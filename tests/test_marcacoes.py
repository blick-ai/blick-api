from decimal import Decimal

from domain.entities import ClassificacaoResultado


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


def test_caixa_incompleta_e_ignorada():
    r = _resultado([{"classe": "saudavel", "confianca": 0.9, "caixa": [0.1, 0.2]}])
    assert "caixa" not in r.to_dict()["analise_por_planta"][0]
