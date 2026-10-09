"""Marcacoes (contorno/caixa) de cada planta: gravacao no Dynamo, resposta da
API e giro da foto pelo EXIF. Sem AWS: tudo em memoria."""
import io
from decimal import Decimal

from PIL import Image

from application.preprocessamento_imagem import redimensionar_para_classificacao
from domain.entities import ClassificacaoResultado
from interfaces.schemas import PlantaResponse


def _resultado(plantas):
    return ClassificacaoResultado(
        status_geral="saudavel",
        confianca_status_geral=0.99,
        probabilidades={"saudavel": 0.99},
        analise_por_planta=plantas,
    )


def test_contorno_e_caixa_viram_decimal_no_dynamo():
    r = _resultado([{
        "classe": "saudavel", "confianca": 0.97, "area_pct": 3.2, "aninhada": False,
        "contorno": [[0.1, 0.2], [0.3, 0.2], [0.2, 0.5]], "caixa": [0.1, 0.2, 0.3, 0.5],
    }])
    planta = r.to_dict()["analise_por_planta"][0]
    assert planta["contorno"][0] == [Decimal("0.1"), Decimal("0.2")]
    assert planta["caixa"] == [Decimal("0.1"), Decimal("0.2"), Decimal("0.3"), Decimal("0.5")]


def test_planta_sem_marcacao_continua_valida():
    # resposta de endpoint antigo ou captura antiga
    r = _resultado([{"classe": "nao_saudavel", "confianca": 0.8}])
    planta = r.to_dict()["analise_por_planta"][0]
    assert "contorno" not in planta and "caixa" not in planta
    assert planta["classe"] == "nao_saudavel"


def test_schema_aceita_decimal_do_dynamo_e_ausencia():
    p = PlantaResponse(classe="saudavel", confianca=Decimal("0.9"),
                       contorno=[[Decimal("0.1"), Decimal("0.2")]] * 3,
                       caixa=[Decimal("0.1")] * 4, aninhada=True)
    d = p.model_dump()
    assert d["caixa"] == [0.1] * 4 and d["aninhada"] is True
    assert PlantaResponse(classe="saudavel").contorno is None


def test_foto_de_celular_e_girada_antes_de_ir_pro_modelo():
    # EXIF orientation 6 = foto "deitada" que o navegador exibe em pe
    im = Image.new("RGB", (400, 200), (10, 200, 10))
    exif = Image.Exif()
    exif[0x0112] = 6
    buf = io.BytesIO()
    im.save(buf, "JPEG", exif=exif)
    saida = Image.open(io.BytesIO(redimensionar_para_classificacao(buf.getvalue())))
    assert saida.size == (200, 400)


def test_foto_sem_exif_nao_muda_de_orientacao():
    im = Image.new("RGB", (400, 200), (10, 200, 10))
    buf = io.BytesIO()
    im.save(buf, "JPEG")
    saida = Image.open(io.BytesIO(redimensionar_para_classificacao(buf.getvalue())))
    assert saida.size == (400, 200)
