from domain.exibicao_plantas import plantas_para_exibicao


def _planta(classe, aninhada, conf=0.9):
    return {"classe": classe, "confianca": conf, "aninhada": aninhada,
            "contorno": [[0.1, 0.1], [0.2, 0.2], [0.1, 0.2]], "caixa": [0.1, 0.1, 0.2, 0.2]}


def test_planta_doente_nunca_sai_aninhada():
    saida = plantas_para_exibicao([_planta("nao_saudavel", True, 0.99)])
    assert saida[0]["aninhada"] is False


def test_doente_vai_por_ultimo_e_ordem_das_demais_nao_muda():
    entrada = [
        _planta("saudavel", False, 0.91),
        _planta("nao_saudavel", True, 0.99),
        _planta("saudavel", True, 0.92),
        _planta("nao_saudavel", False, 0.98),
        _planta("saudavel", False, 0.93),
    ]
    saida = plantas_para_exibicao(entrada)
    assert [p["classe"] for p in saida] == ["saudavel"] * 3 + ["nao_saudavel"] * 2
    assert [p["confianca"] for p in saida[:3]] == [0.91, 0.92, 0.93]
    assert [p["confianca"] for p in saida[3:]] == [0.99, 0.98]


def test_saudavel_mantem_aninhada_original():
    saida = plantas_para_exibicao([_planta("saudavel", True), _planta("saudavel", False)])
    assert [p["aninhada"] for p in saida] == [True, False]


def test_nao_mexe_na_lista_original():
    entrada = [_planta("nao_saudavel", True), _planta("saudavel", True)]
    plantas_para_exibicao(entrada)
    assert entrada[0]["aninhada"] is True and entrada[0]["classe"] == "nao_saudavel"


def test_mantem_contorno_e_caixa():
    saida = plantas_para_exibicao([_planta("nao_saudavel", True)])
    assert saida[0]["contorno"] == [[0.1, 0.1], [0.2, 0.2], [0.1, 0.2]]
    assert saida[0]["caixa"] == [0.1, 0.1, 0.2, 0.2]


def test_sem_analise_devolve_lista_vazia():
    assert plantas_para_exibicao([]) == []
