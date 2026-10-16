import email
import io
from unittest.mock import MagicMock

from PIL import Image

from application.use_cases import ClassifyCapturaUseCase
from domain.entities import (
    Captura,
    ClassificacaoResultado,
    Coordenadas,
    JetsonNanoInfo,
)
from infrastructure.ses_email_service import SESEmailService


def _jpeg() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), (10, 120, 30)).save(buf, "JPEG")
    return buf.getvalue()


def _captura(origem="manual") -> Captura:
    return Captura(
        captura_id="20261015-abc",
        cliente_id="user-1",
        plantacao_id="p1",
        carrinho_id="c1",
        timestamp="2026-10-15T20:00:00Z",
        coordenadas=Coordenadas(latitude=0.0, longitude=0.0),
        s3_bucket="b",
        s3_key="user-1/2026/10/15/x.jpg",
        jetson_nano=JetsonNanoInfo(planta_detectada=True, confianca=0.9, modelo_versao="v"),
        origem=origem,
    )


def _caso(status, origem="manual", email_ok="a@b.com"):
    repo, storage, classifier = MagicMock(), MagicMock(), MagicMock()
    repo.get.return_value = _captura(origem)
    storage.download_image.return_value = _jpeg()
    classifier.classify.return_value = ClassificacaoResultado(
        status_geral=status, confianca_status_geral=0.9, probabilidades={}
    )
    mail, lookup = MagicMock(), MagicMock()
    lookup.obter_email.return_value = email_ok
    uc = ClassifyCapturaUseCase(repo, storage, classifier, mail, lookup)
    uc.execute("p1", "2026-10-15T20:00:00Z", "20261015-abc")
    return mail


def test_nao_milho_manual_envia_email_com_imagem():
    mail = _caso("nao_milho")
    mail.enviar_email.assert_called_once()
    args, kwargs = mail.enviar_email.call_args
    assert args[0] == "a@b.com"
    assert kwargs["imagem_jpeg"].startswith(b"\xff\xd8")
    assert "cid:foto" in args[3]


def test_nao_milho_do_rover_nao_envia():
    assert not _caso("nao_milho", origem="rover").enviar_email.called


def test_saudavel_nao_envia():
    assert not _caso("saudavel").enviar_email.called


def test_sem_email_do_usuario_nao_envia():
    assert not _caso("nao_milho", email_ok=None).enviar_email.called


def test_falha_no_envio_nao_derruba_classificacao():
    repo, storage, classifier = MagicMock(), MagicMock(), MagicMock()
    repo.get.return_value = _captura()
    storage.download_image.return_value = _jpeg()
    classifier.classify.return_value = ClassificacaoResultado(
        status_geral="nao_milho", confianca_status_geral=0.9, probabilidades={}
    )
    mail, lookup = MagicMock(), MagicMock()
    mail.enviar_email.side_effect = RuntimeError("AccessDenied")
    lookup.obter_email.return_value = "a@b.com"
    captura = ClassifyCapturaUseCase(repo, storage, classifier, mail, lookup).execute(
        "p1", "t", "id"
    )
    assert captura.status == "CLASSIFICADO"


def _ses():
    svc = SESEmailService.__new__(SESEmailService)
    svc._client = MagicMock()
    svc._remetente = "noreply@blick-ai.com.br"
    return svc


def test_ses_com_imagem_usa_send_raw_email_com_cid_e_anexo():
    svc = _ses()
    svc.enviar_email("a@b.com", "Assunto ç", "texto", "<img src='cid:foto'>", imagem_jpeg=_jpeg())
    svc._client.send_email.assert_not_called()
    kw = svc._client.send_raw_email.call_args.kwargs
    assert kw["Source"] == "noreply@blick-ai.com.br"
    assert kw["Destinations"] == ["a@b.com"]
    msg = email.message_from_string(kw["RawMessage"]["Data"])
    tipos = [p.get_content_type() for p in msg.walk()]
    assert "text/plain" in tipos and "text/html" in tipos and "image/jpeg" in tipos
    foto = next(p for p in msg.walk() if p.get_content_type() == "image/jpeg")
    assert foto["Content-ID"] == "<foto>"
    assert foto.get_payload(decode=True).startswith(b"\xff\xd8")


def test_ses_sem_imagem_continua_usando_send_email():
    svc = _ses()
    svc.enviar_email("a@b.com", "x", "texto")
    svc._client.send_email.assert_called_once()
    svc._client.send_raw_email.assert_not_called()
