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
# recebe o que ja tem e o indice e renovado em segundo plano. Escritas
# feitas por esta task entram no indice na hora (upsert).
TTL_INDICE_SEGUNDOS = 300
_LOCK_INDICE = threading.Lock()
# monotonic() conta desde o boot da maquina: 0.0 pareceria "fresco" num container novo
_OBSOLETO = float("-inf")


class DynamoCapturaRepository(ICapturaRepository):
    def __init__(self, table_name: str, region: str):
        dynamodb = boto3.resource("dynamodb", region_name=region)
        self._dynamodb = dynamodb
        self._table = dynamodb.Table(table_name)

    def save(self, captura: Captura) -> None:
        self._table.put_item(Item=captura.to_dynamo_item())
        self._indice_upsert(captura)

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
        self._indice_remover(plantacao_id, sk)

    def update(self, captura: Captura) -> None:
        # put_item sobrescreve o item inteiro — como Captura.to_dynamo_item()
        # sempre serializa o objeto completo (incluindo o que ja tinha antes,
        # como cliente_id e coordenadas), isso funciona tanto pra criar
        # quanto pra atualizar sem precisar de um UpdateExpression separado.
        self._table.put_item(Item=captura.to_dynamo_item())
        self._indice_upsert(captura)

    def _indices(self) -> dict:
        # setdefault no __dict__: funciona mesmo se o objeto for criado sem __init__ (testes)
        return self.__dict__.setdefault("_indices_dados", {})

    @staticmethod
    def _linha_de(captura: Captura) -> dict:
        ia = captura.ia_nuvem or {}
        return {
            "sk": f"CAPTURA#{captura.timestamp}#{captura.captura_id}",
            "captura_id": captura.captura_id,
            "timestamp": captura.timestamp,
            "status": captura.status,
            "origem": captura.origem,
            "fl_treino": int(captura.fl_treino),
            "latitude": captura.coordenadas.latitude,
            "longitude": captura.coordenadas.longitude,
            "status_geral": ia.get("status_geral"),
        }

    def _indice_upsert(self, captura: Captura) -> None:
        """Escrita feita aqui entra no indice na hora (sem esperar renovacao)."""
        entrada = self._indices().get(captura.plantacao_id)
        if not entrada:
            return
        nova = self._linha_de(captura)
        linhas = [r for r in entrada["linhas"] if r["sk"] != nova["sk"]]
        linhas.append(nova)
        linhas.sort(key=lambda r: r["sk"], reverse=True)
        entrada["linhas"] = linhas  # troca a lista inteira: leitores em andamento nao quebram
        entrada["versao"] += 1

    def _indice_remover(self, plantacao_id: str, sk: str) -> None:
        entrada = self._indices().get(plantacao_id)
        if not entrada:
            return
        entrada["linhas"] = [r for r in entrada["linhas"] if r["sk"] != sk]
        entrada["versao"] += 1

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
            # se uma escrita entrou durante a leitura, esta leitura nao a contem:
            # descarta (o indice atual ja tem a escrita) e tenta de novo depois
            if entrada["versao"] == versao:
                entrada["linhas"] = linhas
                entrada["carregado_em"] = time.monotonic()
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
        """Quem passa no filtro e o total saem do indice leve (memoria); do
        Dynamo vem so a pagina pedida, por chave (BatchGetItem). Antes cada
        filtro virava uma Query que lia item por item ate achar resultados,
        e chegava a varrer metade da tabela pra achar 1 captura rara."""
        linhas = [
            linha for linha in self._indice(plantacao_id)
            if self._passa_filtros(linha, status, status_geral, origem,
                                   data_inicio, data_fim, fl_treino)
        ]
        inicio = (pagina - 1) * tamanho_pagina
        return self._buscar_por_chave(plantacao_id, linhas[inicio: inicio + tamanho_pagina]), \
            len(linhas)

    def _buscar_por_chave(self, plantacao_id: str, linhas: list[dict]) -> list[Captura]:
        if not linhas:
            return []
        pk = f"PLANT#{plantacao_id}"
        nome = self._table.name
        por_sk: dict[str, dict] = {}
        for i in range(0, len(linhas), 100):  # limite do BatchGetItem: 100 chaves
            chaves = [{"PK": pk, "SK": linha["sk"]} for linha in linhas[i:i + 100]]
            pedido = {nome: {"Keys": chaves}}
            while pedido:
                resposta = self._dynamodb.batch_get_item(RequestItems=pedido)
                for item in resposta.get("Responses", {}).get(nome, []):
                    por_sk[item["SK"]] = item
                pedido = resposta.get("UnprocessedKeys") or None
                if pedido:
                    time.sleep(0.05)
        # a ordem do BatchGetItem nao e garantida: mantem a do indice (mais novas primeiro);
        # item que sumiu da tabela e ainda estava no indice e ignorado
        return [Captura.from_dynamo_item(por_sk[linha["sk"]])
                for linha in linhas if linha["sk"] in por_sk]

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
