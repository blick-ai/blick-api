import boto3

from domain.ports import IEmailService


class SESEmailService(IEmailService):
    def __init__(self, remetente: str, region: str):
        self._client = boto3.client("ses", region_name=region)
        self._remetente = remetente

    def enviar_email(
        self,
        destinatario: str,
        assunto: str,
        corpo_texto: str,
        corpo_html: str | None = None,
    ) -> None:
        body = {"Text": {"Data": corpo_texto, "Charset": "UTF-8"}}
        if corpo_html:
            body["Html"] = {"Data": corpo_html, "Charset": "UTF-8"}

        self._client.send_email(
            Source=self._remetente,
            Destination={"ToAddresses": [destinatario]},
            Message={
                "Subject": {"Data": assunto, "Charset": "UTF-8"},
                "Body": body,
            },
        )
