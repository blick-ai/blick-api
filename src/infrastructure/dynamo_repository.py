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

    def list_by_status(self, status: str, limit: int = 50) -> list[Captura]:
        response = self._table.query(
            IndexName="GSI2",
            KeyConditionExpression="GSI2PK = :status",
            ExpressionAttributeValues={":status": f"STATUS#{status}"},
            Limit=limit,
        )
        return [Captura.from_dynamo_item(item) for item in response.get("Items", [])]

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
    