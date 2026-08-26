import boto3

from domain.ports import IEmailService


class SESEmailService(IEmailService):
    """
    Envio de e-mail via Amazon SES. Precisa de um remetente verificado
    no console do SES (Settings -> Identities) antes de funcionar de
    verdade — sem isso, o SES rejeita o envio.

    Se a conta ainda estiver em "sandbox" (padrao pra contas novas), o
    DESTINATARIO tambem precisa estar verificado — isso bloqueia enviar
    pra qualquer usuario real ate a AWS aprovar a saida do sandbox
    (pedido feito no console, geralmente aprovado em minutos/poucas
    horas pra contas academicas de baixo volume).
    """

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
