import boto3

from domain.entities import Captura
from domain.ports import ICapturaRepository


class DynamoCapturaRepository(ICapturaRepository):
    def __init__(self, table_name: str, region: str):
        dynamodb = boto3.resource("dynamodb", region_name=region)
        self._table = dynamodb.Table(table_name)

    def save(self, captura: Captura) -> None:
        self._table.put_item(Item=captura.to_dynamo_item())

    def get(self, plantacao_id: str, timestamp: str, captura_id: str) -> Captura | None:
        pk = f"PLANT#{plantacao_id}"
        sk = f"CAPTURA#{timestamp}#{captura_id}"
        response = self._table.get_item(Key={"PK": pk, "SK": sk})
        item = response.get("Item")
        return Captura.from_dynamo_item(item) if item else None

    def update(self, captura: Captura) -> None:
        # put_item sobrescreve o item inteiro — como Captura.to_dynamo_item()
        # sempre serializa o objeto completo (incluindo o que ja tinha antes,
        # como cliente_id e coordenadas), isso funciona tanto pra criar
        # quanto pra atualizar sem precisar de um UpdateExpression separado.
        self._table.put_item(Item=captura.to_dynamo_item())

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
        data_inicio: str | None = None,
        data_fim: str | None = None,
        pagina: int = 1,
        tamanho_pagina: int = 8,
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

        if filtros:
            kwargs["FilterExpression"] = " AND ".join(filtros)
            if status:
                kwargs["ExpressionAttributeNames"] = {"#s": "status"}

        # dataset de uma plantacao de TCC e pequeno (centenas/poucos
        # milhares de capturas) — busca tudo que bate no filtro e pagina
        # em memoria. Simples e correto. Se um dia isso escalar pra volume
        # bem maior, vale trocar por paginacao nativa via cursor em vez
        # de pagina numerada (que exige varrer do inicio a cada consulta).
        todas = []
        while True:
            response = self._table.query(**kwargs)
            todas.extend(Captura.from_dynamo_item(item) for item in response.get("Items", []))
            if "LastEvaluatedKey" not in response:
                break
            kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]

        total = len(todas)
        inicio_idx = (pagina - 1) * tamanho_pagina
        capturas_da_pagina = todas[inicio_idx: inicio_idx + tamanho_pagina]
        return capturas_da_pagina, total

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
