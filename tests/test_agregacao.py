from domain.agregacao import agregar_por_planta


def _plantas(saudaveis, doentes):
    return (
        [{"classe": "saudavel", "confianca": c} for c in saudaveis]
        + [{"classe": "nao_saudavel", "confianca": c} for c in doentes]
    )


def test_padrao_uma_planta_doente_e_saudavel():
    status, _ = agregar_por_planta(_plantas([0.99] * 19, [0.99]))
    assert status == "saudavel"


def test_padrao_duas_plantas_doentes_e_nao_saudavel():
    status, confianca = agregar_por_planta(_plantas([0.99] * 14, [0.95, 0.99]))
    assert status == "nao_saudavel"
    assert confianca == 0.99


def test_filtro_de_confianca_descarta_doente_incerta():
    plantas = _plantas([0.99] * 13, [0.9998, 0.7167, 1.0, 0.9999])
    status, _ = agregar_por_planta(plantas, conf_min=0.90, n_min=4, fracao_min=0.20)
    assert status == "saudavel"


def test_adesivo_continua_nao_saudavel_com_regra_estrita():
    plantas = _plantas([0.99] * 18, [0.99] * 6 + [0.5, 0.6])
    status, _ = agregar_por_planta(plantas, conf_min=0.90, n_min=4, fracao_min=0.20)
    assert status == "nao_saudavel"


def test_fracao_minima_protege_foto_com_muitas_plantas():
    plantas = _plantas([0.99] * 40, [0.99] * 4)
    status, _ = agregar_por_planta(plantas, conf_min=0.0, n_min=2, fracao_min=0.20)
    assert status == "saudavel"


def test_so_doentes_validas_nunca_vira_saudavel():
    status, _ = agregar_por_planta(_plantas([], [0.99]))
    assert status == "nao_saudavel"


def test_sem_planta_valida_devolve_none():
    assert agregar_por_planta([]) is None
    assert agregar_por_planta(_plantas([], [0.5]), conf_min=0.9) is None


def test_variavel_de_ambiente_muda_a_regra(monkeypatch):
    plantas = _plantas([0.99] * 19, [0.99])
    assert agregar_por_planta(plantas)[0] == "saudavel"
    monkeypatch.setenv("AGREGACAO_N_MIN", "1")
    assert agregar_por_planta(plantas)[0] == "nao_saudavel"


def _planta(classe, conf, area, aninhada=False):
    return {"classe": classe, "confianca": conf, "area_pct": area, "aninhada": aninhada}


def test_area_fragmentos_pequenos_nao_contam():
    plantas = [_planta("saudavel", 0.99, 5.0)] * 10 + [
        _planta("nao_saudavel", 1.0, 0.14),
        _planta("nao_saudavel", 1.0, 0.13),
        _planta("nao_saudavel", 0.94, 0.51),
    ]
    assert agregar_por_planta(plantas)[0] == "saudavel"


def test_area_uma_doente_grande_basta():
    plantas = [_planta("saudavel", 0.99, 5.0)] * 10 + [_planta("nao_saudavel", 0.81, 0.97)]
    status, confianca = agregar_por_planta(plantas)
    assert status == "nao_saudavel"
    assert confianca == 0.81


def test_area_doente_aninhada_pequena_nao_conta():
    plantas = [_planta("saudavel", 0.99, 5.0), _planta("nao_saudavel", 1.0, 1.0, aninhada=True)]
    assert agregar_por_planta(plantas)[0] == "saudavel"


def test_area_doente_aninhada_grande_e_confiante_conta():
    plantas = [
        _planta("saudavel", 0.99, 9.0),
        _planta("nao_saudavel", 0.9995, 2.433, aninhada=True),
    ]
    assert agregar_por_planta(plantas)[0] == "nao_saudavel"


def test_area_doente_aninhada_grande_pouco_confiante_nao_conta():
    plantas = [_planta("saudavel", 0.99, 9.0), _planta("nao_saudavel", 0.8, 3.0, aninhada=True)]
    assert agregar_por_planta(plantas)[0] == "saudavel"


def test_area_confianca_baixa_nao_conta():
    plantas = [_planta("saudavel", 0.99, 5.0), _planta("nao_saudavel", 0.6, 3.0)]
    assert agregar_por_planta(plantas)[0] == "saudavel"


def test_area_limiar_por_variavel_de_ambiente(monkeypatch):
    plantas = [_planta("saudavel", 0.99, 5.0), _planta("nao_saudavel", 1.0, 0.5)]
    assert agregar_por_planta(plantas)[0] == "saudavel"
    monkeypatch.setenv("AGREGACAO_AREA_MIN_PCT", "0.3")
    assert agregar_por_planta(plantas)[0] == "nao_saudavel"
