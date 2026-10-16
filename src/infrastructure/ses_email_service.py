from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

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
        imagem_jpeg: bytes | None = None,
    ) -> None:
        if imagem_jpeg:
            self._enviar_com_imagem(destinatario, assunto, corpo_texto, corpo_html, imagem_jpeg)
            return

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

    def _enviar_com_imagem(
        self,
        destinatario: str,
        assunto: str,
        corpo_texto: str,
        corpo_html: str | None,
        imagem_jpeg: bytes,
    ) -> None:
        # send_email do SES nao aceita anexo; com imagem precisa ser MIME cru.
        # Estrutura: mixed > related > alternative (texto + html) + imagem.
        # O HTML referencia a foto por cid:foto, entao aparece dentro do
        # proprio email, e o cliente de email ainda oferece baixar o arquivo.
        raiz = MIMEMultipart("mixed")
        raiz["Subject"] = assunto
        raiz["From"] = self._remetente
        raiz["To"] = destinatario

        relacionado = MIMEMultipart("related")
        alternativo = MIMEMultipart("alternative")
        alternativo.attach(MIMEText(corpo_texto, "plain", "utf-8"))
        if corpo_html:
            alternativo.attach(MIMEText(corpo_html, "html", "utf-8"))
        relacionado.attach(alternativo)

        foto = MIMEImage(imagem_jpeg, _subtype="jpeg")
        foto.add_header("Content-ID", "<foto>")
        foto.add_header("Content-Disposition", "inline", filename="captura.jpg")
        relacionado.attach(foto)
        raiz.attach(relacionado)

        self._client.send_raw_email(
            Source=self._remetente,
            Destinations=[destinatario],
            RawMessage={"Data": raiz.as_string()},
        )
