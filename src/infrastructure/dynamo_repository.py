import concurrent.futures
import threading
import time

import boto3

from domain.entities import Captura
from domain.ports import ICapturaRepository


# Varredura paralela: a particao da plantacao tem milhares de itens pesados
# (contornos por planta). Ler tudo em sequencia levava ~15 s; em segmentos
# paralelos o tempo cai quase na proporcao do numero de segmentos.
SEGMENTOS_VARREDURA = 8
# Indice leve (uma linha pequena por captura) compartilhado por TODAS as
# chamadas: totais da paginacao e pontos do mapa saem dele, em vez de cada
# requisicao varrer a tabela inteira de novo. Passou do TTL, a chamada
# recebe o que ja tem e o indice e renovado em segundo plano.
TTL_INDICE_SEGUNDOS = 120
_LOCK_INDICE = threading.Lock()
# monotonic() conta desde o boot da maquina: 0.0 pareceria "fresco" num container novo
_OBSOLETO = float("-inf")


class DynamoCapturaRepository(ICapturaRepository):
    def __init__(self, table_name: str, region: str):
        dynamodb = boto3.resource("dynamodb", region_name=region)
        self._table = dynamodb.Table(table_name)

    def save(self, captura: Captura) -> None:
        self._table.put_item(Item=captura.to_dynamo_item())
        self._marcar_obsoleto()

    def get(self, plantacao_id: str, timestamp: str, captura_id: str) -> Captura | None:
        pk = f"PLANT#{plantacao_id}"
        sk = f"CAPTURA#{timestamp}#{captura_id}"
        response = self._table.get_item(Key={"PK": pk, "SK": sk})
        item = response.get("Item")
        return Captura.from_dynamo_item(item) if item else None

    def delete(self, plantacao_id: str, timestamp: str, captura_id: str) -> None:
        pk = f"PLANT#{plantacao_id}"
        sk = f"CAPTURA#{timestamp}#{captura_id}"
        self._table.delete_item(Key={"PK": pk, "SK": sk})
        self._marcar_obsoleto()

    def update(self, captura: Captura) -> None:
        # put_item sobrescreve o item inteiro — como Captura.to_dynamo_item()
        # sempre serializa o objeto completo (incluindo o que ja tinha antes,
        # como cliente_id e coordenadas), isso funciona tanto pra criar
        # quanto pra atualizar sem precisar de um UpdateExpression separado.
        self._table.put_item(Item=captura.to_dynamo_item())
        self._marcar_obsoleto()

    def _indices(self) -> dict:
        # setdefault no __dict__: funciona mesmo se o objeto for criado sem __init__ (testes)
        return self.__dict__.setdefault("_indices_dados", {})

    def _marcar_obsoleto(self) -> None:
        """Chamado em toda escrita: o indice atual passa a ser renovado na
        proxima leitura (sem apagar, pra ninguem esperar a varredura)."""
        for entrada in self._indices().values():
            entrada["versao"] += 1
            entrada["carregado_em"] = _OBSOLETO

    def _carregar_indice(self, plantacao_id: str) -> list[dict]:
        segmentos = self._varrer_paralelo(
            FilterExpression="PK = :pk AND begins_with(SK, :pref)",
            ExpressionAttributeValues={":pk": f"PLANT#{plantacao_id}", ":pref": "CAPTURA#"},
            ExpressionAttributeNames={"#ts": "timestamp", "#st": "status"},
            ProjectionExpression=(
                "SK, captura_id, #ts, #st, origem, fl_treino, coordenadas, ia_nuvem.status_geral"
            ),
        )
        linhas = []
        for itens, _ in segmentos:
            for it in itens:
                coord = it.get("coordenadas") or {}
                linhas.append({
                    "sk": it["SK"],
                    "captura_id": it.get("captura_id"),
                    "timestamp": it.get("timestamp"),
                    "status": it.get("status"),
                    "origem": it.get("origem"),
                    "fl_treino": int(it.get("fl_treino", 0)),
                    "latitude": coord.get("latitude"),
                    "longitude": coord.get("longitude"),
                    "status_geral": (it.get("ia_nuvem") or {}).get("status_geral"),
                })
        linhas.sort(key=lambda r: r["sk"], reverse=True)  # mais recentes primeiro
        return linhas

    def _renovar_indice(self, plantacao_id: str) -> None:
        entrada = self._indices()[plantacao_id]
        versao = entrada["versao"]
        try:
            linhas = self._carregar_indice(plantacao_id)
            entrada["linhas"] = linhas
            # se entrou escrita durante a leitura, continua "velho" e renova de novo
            entrada["carregado_em"] = (
                time.monotonic() if entrada["versao"] == versao else _OBSOLETO
            )
        except Exception:
            pass  # mantem o indice antigo; a proxima chamada tenta de novo
        finally:
            entrada["renovando"] = False

    def _indice(self, plantacao_id: str) -> list[dict]:
        entradas = self._indices()
        entrada = entradas.get(plantacao_id)
        if entrada:
            fresco = time.monotonic() - entrada["carregado_em"] < TTL_INDICE_SEGUNDOS
            if not fresco and not entrada["renovando"]:
                entrada["renovando"] = True
                threading.Thread(
                    target=self._renovar_indice, args=(plantacao_id,), daemon=True
                ).start()
            return entrada["linhas"]
        with _LOCK_INDICE:  # 1a carga: quem chega junto espera a mesma leitura
            entrada = entradas.get(plantacao_id)
            if entrada:
                return entrada["linhas"]
            linhas = self._carregar_indice(plantacao_id)
            entradas[plantacao_id] = {
                "linhas": linhas, "carregado_em": time.monotonic(),
                "renovando": False, "versao": 0,
            }
            return linhas

    @staticmethod
    def _passa_filtros(linha, status, status_geral, origem, data_inicio, data_fim, fl_treino):
        """Mesma regra dos filtros da consulta, aplicada ao indice em memoria."""
        if status and linha["status"] != status:
            return False
        if status_geral and linha["status_geral"] != status_geral:
            return False
        if origem and linha["origem"] != origem:
            return False
        if fl_treino is not None and linha["fl_treino"] != fl_treino:
            return False
        if data_inicio or data_fim:
            inicio = f"CAPTURA#{data_inicio}" if data_inicio else "CAPTURA#0000-00-00"
            fim = f"CAPTURA#{data_fim}~" if data_fim else "CAPTURA#9999-99-99~"
            if not inicio <= linha["sk"] <= fim:
                return False
        return True

    def _varrer_paralelo(self, **kwargs_base) -> list[tuple[list[dict], int]]:
        """Scan em SEGMENTOS_VARREDURA segmentos ao mesmo tempo.
        Devolve [(itens, contagem)] por segmento."""

        def _segmento(indice: int) -> tuple[list[dict], int]:
            kw = dict(kwargs_base, Segment=indice, TotalSegments=SEGMENTOS_VARREDURA)
            itens, contagem = [], 0
            while True:
                resposta = self._table.scan(**kw)
                itens.extend(resposta.get("Items", []))
                contagem += resposta.get("Count", 0)
                if "LastEvaluatedKey" not in resposta:
                    break
                kw["ExclusiveStartKey"] = resposta["LastEvaluatedKey"]
            return itens, contagem

        with concurrent.futures.ThreadPoolExecutor(max_workers=SEGMENTOS_VARREDURA) as ex:
            return list(ex.map(_segmento, range(SEGMENTOS_VARREDURA)))

    def list_by_status(
        self, status: str, plantacao_id: str = "plantacao-mock-001", limit: int = 50
    ) -> list[Captura]:
        # PENSADO PRA USAR GSI2 originalmente, mas a tabela real nao tem
        # esse indice criado na infra (so existe no calculo do item, nunca
        # foi provisionado na tabela em si — ver conversa de 04/08). Em vez
        # de depender de uma mudanca de infraestrutura pra criar o indice,
        # consulta so pela chave primaria (PK), que sabemos que funciona,
        # e filtra por status em memoria — o volume de uma plantacao de
        # TCC e pequeno o suficiente pra isso ser tranquilo.
        pk = f"PLANT#{plantacao_id}"
        kwargs = {
            "KeyConditionExpression": "PK = :pk",
            "ExpressionAttributeValues": {":pk": pk, ":status": status},
            "FilterExpression": "#s = :status",
            "ExpressionAttributeNames": {"#s": "status"},
        }
        encontrados = []
        while True:
            response = self._table.query(**kwargs)
            encontrados.extend(Captura.from_dynamo_item(item) for item in response.get("Items", []))
            if len(encontrados) >= limit or "LastEvaluatedKey" not in response:
                break
            kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
        return encontrados[:limit]

    def list_by_plantacao(
        self,
        plantacao_id: str,
        status: str | None = None,
        status_geral: str | None = None,
        origem: str | None = None,
        data_inicio: str | None = None,
        data_fim: str | None = None,
        pagina: int = 1,
        tamanho_pagina: int = 8,
        fl_treino: int | None = None,
    ) -> tuple[list[Captura], int]:
        pk = f"PLANT#{plantacao_id}"
        key_condition = "PK = :pk"
        expr_values = {":pk": pk}

        # data_inicio/data_fim no formato "YYYY-MM-DD" — SK comeca com
        # "CAPTURA#<timestamp ISO>#...", e como ISO8601 ordena
        # corretamente como string, da pra usar um BETWEEN direto na SK
        # (parte da key condition, muito mais barato que Scan+filtro)
        if data_inicio or data_fim:
            inicio = f"CAPTURA#{data_inicio}" if data_inicio else "CAPTURA#0000-00-00"
            fim = f"CAPTURA#{data_fim}~" if data_fim else "CAPTURA#9999-99-99~"
            key_condition += " AND SK BETWEEN :inicio AND :fim"
            expr_values[":inicio"] = inicio
            expr_values[":fim"] = fim

        kwargs = {
            "KeyConditionExpression": key_condition,
            "ExpressionAttributeValues": expr_values,
            "ScanIndexForward": False,  # mais recentes primeiro (SK = timestamp)
        }

        filtros = []
        if status:
            # "status" e palavra reservada no DynamoDB, precisa de alias
            filtros.append("#s = :status")
            expr_values[":status"] = status
        if status_geral:
            # ia_nuvem e um Map (M) no DynamoDB — da pra filtrar direto
            # no campo aninhado sem precisar de indice novo
            filtros.append("ia_nuvem.status_geral = :sg")
            expr_values[":sg"] = status_geral
        if origem:
            # "origem" nao e palavra reservada, filtra direto sem alias
            filtros.append("origem = :origem")
            expr_values[":origem"] = origem
        if fl_treino is not None:
            # fl_treino=0 tambem pega itens que ainda nao tem a coluna
            # (capturas anteriores a flag), senao sumiriam da listagem
            if fl_treino == 0:
                filtros.append("(attribute_not_exists(fl_treino) OR fl_treino = :flt)")
            else:
                filtros.append("fl_treino = :flt")
            expr_values[":flt"] = fl_treino

        if filtros:
            kwargs["FilterExpression"] = " AND ".join(filtros)
            if status:
                kwargs["ExpressionAttributeNames"] = {"#s": "status"}

        # ANTES: buscava TODAS as capturas da plantacao (mesmo pra
        # mostrar so 8), sempre, em toda chamada — ficava mais lento a
        # cada captura nova, ate em paginas iniciais. Corrigido ontem
        # (para assim que tem itens suficientes pra pagina pedida).
        #
        # MAS: a contagem do total (pro "1096 resultados" da paginacao)
        # continuava rodando numa consulta SEPARADA, DEPOIS da coleta —
        # sequencial, dobrando o tempo total mesmo com as duas consultas
        # sendo independentes uma da outra. Agora rodam em PARALELO
        # (thread separada pra cada), cortando o tempo pela metade.
        itens_necessarios = pagina * tamanho_pagina

        def _coletar_pagina():
            coletadas = []
            kwargs_local = dict(kwargs)
            while len(coletadas) < itens_necessarios:
                response = self._table.query(**kwargs_local)
                coletadas.extend(
                    Captura.from_dynamo_item(item) for item in response.get("Items", [])
                )
                if "LastEvaluatedKey" not in response:
                    break
                kwargs_local["ExclusiveStartKey"] = response["LastEvaluatedKey"]
            return coletadas

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            futuro_dados = executor.submit(_coletar_pagina)
            futuro_total = executor.submit(
                self._contar_total, plantacao_id, status, status_geral, origem,
                data_inicio, data_fim, fl_treino,
            )
            coletadas = futuro_dados.result()
            total = futuro_total.result()

        inicio_idx = (pagina - 1) * tamanho_pagina
        capturas_da_pagina = coletadas[inicio_idx: inicio_idx + tamanho_pagina]

        return capturas_da_pagina, total

    def _contar_total(self, plantacao_id, status, status_geral, origem,
                      data_inicio, data_fim, fl_treino) -> int:
        return sum(
            1 for linha in self._indice(plantacao_id)
            if self._passa_filtros(linha, status, status_geral, origem,
                                   data_inicio, data_fim, fl_treino)
        )

    def list_pontos_mapa(
        self,
        plantacao_id: str,
        status_geral: str | None = None,
        fl_treino: int | None = None,
    ) -> list[dict]:
        """Pontos enxutos pro mapa (captura_id, timestamp, latitude, longitude,
        status_geral), mais recentes primeiro, vindos do indice leve."""
        return [
            {k: linha[k] for k in
             ("captura_id", "timestamp", "latitude", "longitude", "status_geral")}
            for linha in self._indice(plantacao_id)
            if self._passa_filtros(linha, None, status_geral, None, None, None, fl_treino)
        ]

    def list_cliente_ids(self) -> list[str]:
        cliente_ids: set[str] = set()
        scan_kwargs = {
            "FilterExpression": "entity_type = :et",
            "ExpressionAttributeValues": {":et": "CAPTURA"},
            "ProjectionExpression": "cliente_id",
        }
        while True:
            response = self._table.scan(**scan_kwargs)
            for item in response.get("Items", []):
                if "cliente_id" in item:
                    cliente_ids.add(item["cliente_id"])
            if "LastEvaluatedKey" not in response:
                break
            scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
        return sorted(cliente_ids)
