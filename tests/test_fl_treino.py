import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from domain.entities import (  # noqa: E402
    Captura, Coordenadas, JetsonNanoInfo,
)


def _captura(**extra):
    return Captura(
        captura_id="20260701120000-abcd1234",
        cliente_id="c1",
        plantacao_id="p1",
        carrinho_id="k1",
        timestamp="2026-07-01T12:00:00Z",
        coordenadas=Coordenadas(),
        s3_bucket="b",
        s3_key="k.jpg",
        jetson_nano=JetsonNanoInfo(True, 0.9, "v1"),
        **extra,
    )


def test_captura_nova_nasce_fora_do_treino():
    assert _captura().fl_treino == 0


def test_flag_e_gravada_no_item():
    assert _captura(fl_treino=1).to_dynamo_item()["fl_treino"] == 1
    assert _captura().to_dynamo_item()["fl_treino"] == 0


def test_flag_sobrevive_ao_ciclo_ler_e_regravar():
    # simula reclassificar: le do Dynamo (Decimal) e regrava o item inteiro
    item = _captura(fl_treino=1).to_dynamo_item()
    item["fl_treino"] = Decimal("1")
    lida = Captura.from_dynamo_item(item)
    assert lida.fl_treino == 1
    assert lida.to_dynamo_item()["fl_treino"] == 1


def test_item_antigo_sem_a_coluna_vira_zero():
    item = _captura().to_dynamo_item()
    del item["fl_treino"]
    assert Captura.from_dynamo_item(item).fl_treino == 0
