import pytest

# o CI instala so pytest e flake8: sem Pillow/boto3 estes testes sao pulados
Image = pytest.importorskip("PIL.Image")
pytest.importorskip("boto3")

import io  # noqa: E402
from unittest.mock import MagicMock  # noqa: E402

from application.use_cases import ClassifyCapturaUseCase, ReclassificarTodasUseCase  # noqa: E402
from domain.entities import (  # noqa: E402
    Captura,
    ClassificacaoResultado,
    Coordenadas,
    JetsonNanoInfo,
)


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


def _caso(status, origem="manual", email_ok="a@b.com", notificar=True):
    repo, storage, classifier = MagicMock(), MagicMock(), MagicMock()
    repo.get.return_value = _captura(origem)
    storage.download_image.return_value = _jpeg()
    classifier.classify.return_value = ClassificacaoResultado(
        status_geral=status, confianca_status_geral=0.9, probabilidades={}
    )
    mail, lookup = MagicMock(), MagicMock()
    lookup.obter_email.return_value = email_ok
    uc = ClassifyCapturaUseCase(repo, storage, classifier, mail, lookup)
    uc.execute("p1", "2026-10-15T20:00:00Z", "20261015-abc", notificar=notificar)
    return mail


def test_nao_milho_manual_envia_email():
    mail = _caso("nao_milho")
    mail.enviar_email.assert_called_once()
    args, _ = mail.enviar_email.call_args
    assert args[0] == "a@b.com"
    assert "não foi reconhecida como milho" in args[1] or "milho" in args[1]


def test_nao_milho_do_rover_nao_envia():
    assert not _caso("nao_milho", origem="rover").enviar_email.called


def test_saudavel_e_nao_saudavel_nao_enviam_email():
    assert not _caso("saudavel").enviar_email.called
    assert not _caso("nao_saudavel").enviar_email.called


def test_sem_email_do_usuario_nao_envia():
    assert not _caso("nao_milho", email_ok=None).enviar_email.called


def test_reprocessamento_em_lote_nao_envia_email():
    assert not _caso("nao_milho", notificar=False).enviar_email.called


def test_reclassificar_todas_nao_manda_email():
    repo, classificar = MagicMock(), MagicMock()
    repo.list_by_plantacao.return_value = ([_captura()], 1)
    ReclassificarTodasUseCase(repo, classificar).execute()
    assert classificar.execute.call_args.kwargs["notificar"] is False


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
