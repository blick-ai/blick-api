import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


class _TabelaFalsa:
    """Registra os parametros de cada query, sem tocar na AWS."""

    def __init__(self):
        self.chamadas = []

    def query(self, **kwargs):
        self.chamadas.append(kwargs)
        return {"Items": [], "Count": 0}


def _repo():
    pytest.importorskip("boto3")
    from infrastructure.dynamo_repository import DynamoCapturaRepository

    repo = object.__new__(DynamoCapturaRepository)
    repo._table = _TabelaFalsa()
    return repo


def test_fl_treino_zero_inclui_itens_sem_a_coluna():
    repo = _repo()
    repo.list_by_plantacao(plantacao_id="p1", fl_treino=0)
    for kw in repo._table.chamadas:
        assert "attribute_not_exists(fl_treino)" in kw["FilterExpression"]
        assert kw["ExpressionAttributeValues"][":flt"] == 0


def test_fl_treino_um_filtra_so_as_de_treino():
    repo = _repo()
    repo.list_by_plantacao(plantacao_id="p1", fl_treino=1)
    for kw in repo._table.chamadas:
        assert kw["FilterExpression"] == "fl_treino = :flt"
        assert kw["ExpressionAttributeValues"][":flt"] == 1


def test_sem_fl_treino_nao_filtra_nada():
    repo = _repo()
    repo.list_by_plantacao(plantacao_id="p1")
    for kw in repo._table.chamadas:
        assert "FilterExpression" not in kw
        assert ":flt" not in kw["ExpressionAttributeValues"]


class _RepoFalso:
    def __init__(self):
        self.chamadas = []

    def list_by_plantacao(self, **kwargs):
        self.chamadas.append(kwargs)
        return [], 0


def test_listagem_e_mapa_escondem_treino_e_manutencao_nao():
    pytest.importorskip("PIL")
    from application.use_cases import (
        ListCapturasUseCase,
        ListMapaCapturasUseCase,
        ReclassificarTodasUseCase,
    )

    repo = _RepoFalso()
    ListCapturasUseCase(repo, storage=None).execute()
    ListMapaCapturasUseCase(repo).execute()
    ReclassificarTodasUseCase(repo, classify_use_case=None).execute()

    listagem, mapa, manutencao = repo.chamadas
    assert listagem["fl_treino"] == 0
    assert mapa["fl_treino"] == 0
    assert "fl_treino" not in manutencao  # a reclassificacao precisa ver tudo
