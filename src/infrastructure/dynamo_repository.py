import boto3

from domain.entities import Captura
from domain.ports import ICapturaRepository


class DynamoCapturaRepository(ICapturaRepository):
    def __init__(self, table_name: str, region: str):
        dynamodb = boto3.resource("dynamodb", region_name=region)
        self._table = dynamodb.Table(table_name)

    def save(self, captura: Captura) -> None:
        self._table.put_item(Item=captura.to_dynamo_item())
