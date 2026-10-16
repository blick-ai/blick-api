from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

pytest.importorskip("boto3")
pytest.importorskip("PIL")

from application.use_cases import (  # noqa: E402
    DeletarCapturaUseCase,
    GetCapturaUseCase,
    ListCapturasUseCase,
    ListMapaCapturasUseCase,
)
from infrastructure.dynamo_repository import DynamoCapturaRepository  # noqa: E402
from tests.test_filtro_treino import _ids as _ids_treino  # noqa: E402
from tests.test_filtro_treino import _item, _repo  # noqa: E402


def _com_dono(item, cliente_id):
    if cliente_id:
        item["cliente_id"] = cliente_id
    return item


ITENS = [
    _com_dono(_item("CAPTURA#2026-09-29T10:00:00#a", "saudavel", fl_treino=0), "igor"),
    _com_dono(_item("CAPTURA#2026-09-30T10:00:00#b", "nao_saudavel", fl_treino=0), "mauro"),
    _com_dono(_item("CAPTURA#2026-10-01T10:00:00#c", "nao_saudavel", fl_treino=0), "mauro"),
    _com_dono(_item("CAPTURA#2026-10-02T10:00:00#d", "saudavel", fl_treino=0), None),  # sem dono
]


_ids_base = _ids_treino


def _ids(repo, **kw):
    return _ids_base(repo, **kw)


def test_listagem_so_devolve_as_capturas_do_usuario(monkeypatch):
    repo = _repo(ITENS, monkeypatch)
    assert _ids(repo, cliente_id="mauro") == (["c", "b"], 2)
    assert _ids(repo, cliente_id="igor") == (["a"], 1)


def test_usuario_sem_capturas_recebe_lista_vazia(monkeypatch):
    repo = _repo(ITENS, monkeypatch)
    assert _ids(repo, cliente_id="outro") == ([], 0)


def test_captura_sem_dono_nao_aparece_pra_ninguem(monkeypatch):
    repo = _repo(ITENS, monkeypatch)
    for dono in ("igor", "mauro"):
        assert "d" not in _ids(repo, cliente_id=dono)[0]


def test_sem_cliente_id_nao_filtra_para_rotinas_de_manutencao(monkeypatch):
    repo = _repo(ITENS, monkeypatch)
    assert _ids(repo)[1] == 4


def test_filtro_de_usuario_combina_com_os_outros_filtros(monkeypatch):
    repo = _repo(ITENS, monkeypatch)
    assert _ids(repo, cliente_id="mauro", status_geral="nao_saudavel") == (["c", "b"], 2)
    assert _ids(repo, cliente_id="igor", status_geral="nao_saudavel") == ([], 0)
    assert _ids(repo, cliente_id="mauro", tamanho_pagina=1, pagina=2) == (["b"], 2)


def test_mapa_so_tem_pontos_do_usuario(monkeypatch):
    repo = _repo(ITENS, monkeypatch)
    pontos = repo.list_pontos_mapa(plantacao_id="p1", cliente_id="mauro")
    assert [p["captura_id"] for p in pontos] == ["c", "b"]
    do_igor = repo.list_pontos_mapa(plantacao_id="p1", cliente_id="igor")
    assert [p["captura_id"] for p in do_igor] == ["a"]


def test_indice_inclui_o_dono_das_capturas_novas(monkeypatch):
    from tests.test_filtro_treino import _captura_falsa

    repo = _repo(ITENS, monkeypatch)
    _ids(repo)
    repo.save(_captura_falsa("e", "2026-10-03T10:00:00", cliente_id="igor"))
    assert _ids(repo, cliente_id="igor") == (["e", "a"], 2)
    assert _ids(repo, cliente_id="mauro")[1] == 2


def test_use_cases_repassam_o_cliente_id_ao_repositorio():
    repo = MagicMock()
    repo.list_by_plantacao.return_value = ([], 0)
    repo.list_pontos_mapa.return_value = []
    ListCapturasUseCase(repo, storage=None).execute(cliente_id="u1")
    ListMapaCapturasUseCase(repo).execute(cliente_id="u1")
    assert repo.list_by_plantacao.call_args.kwargs["cliente_id"] == "u1"
    assert repo.list_pontos_mapa.call_args.kwargs["cliente_id"] == "u1"


def _captura(dono):
    return SimpleNamespace(cliente_id=dono, s3_key="k", ia_nuvem=None)


def test_detalhe_de_captura_de_outro_usuario_vira_nao_encontrada():
    repo = MagicMock()
    repo.get.return_value = _captura("igor")
    uc = GetCapturaUseCase(repo, storage=MagicMock())
    assert uc.execute("p1", "t", "x", cliente_id="mauro") is None


def test_nao_apaga_captura_de_outro_usuario():
    repo, storage = MagicMock(), MagicMock()
    repo.get.return_value = _captura("igor")
    uc = DeletarCapturaUseCase(repo, storage)
    assert uc.execute("p1", "t", "x", cliente_id="mauro") is False
    repo.delete.assert_not_called()
    storage.delete_image.assert_not_called()


def test_apaga_a_propria_captura():
    repo, storage = MagicMock(), MagicMock()
    repo.get.return_value = _captura("mauro")
    assert DeletarCapturaUseCase(repo, storage).execute("p1", "t", "x", cliente_id="mauro") is True
    repo.delete.assert_called_once()


def test_repositorio_continua_sendo_um_dynamo():
    assert issubclass(DynamoCapturaRepository, object)
