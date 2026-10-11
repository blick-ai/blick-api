import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


class _TabelaFalsa:
    """Registra os parametros de cada consulta, sem tocar na AWS."""

    def __init__(self, itens_scan=None):
        self.queries = []
        self.scans = []
        self._itens_scan = itens_scan or []

    def query(self, **kwargs):
        self.queries.append(kwargs)
        return {"Items": [], "Count": 0}

    def scan(self, **kwargs):
        self.scans.append(kwargs)
        # so o segmento 0 devolve os itens, pra nao duplicar entre segmentos
        itens = self._itens_scan if kwargs.get("Segment") == 0 else []
        return {"Items": itens, "Count": len(itens)}


def _repo(itens_scan=None):
    pytest.importorskip("boto3")
    from infrastructure.dynamo_repository import DynamoCapturaRepository

    repo = object.__new__(DynamoCapturaRepository)
    repo._table = _TabelaFalsa(itens_scan)
    return repo


def _item(sk, status_geral=None, fl_treino=None, status="CONCLUIDO", origem="rover", lat=1, lon=2):
    item = {
        "SK": sk, "captura_id": sk.split("#")[-1], "timestamp": sk.split("#")[1],
        "status": status, "origem": origem, "coordenadas": {"latitude": lat, "longitude": lon},
    }
    if status_geral:
        item["ia_nuvem"] = {"status_geral": status_geral}
    if fl_treino is not None:
        item["fl_treino"] = fl_treino
    return item


ITENS = [
    _item("CAPTURA#2026-09-29T10:00:00#a", "saudavel"),                 # sem a coluna
    _item("CAPTURA#2026-09-30T10:00:00#b", "nao_saudavel", fl_treino=0),
    _item("CAPTURA#2026-10-01T10:00:00#c", "nao_saudavel", fl_treino=1),
    _item("CAPTURA#2026-10-02T10:00:00#d", None, status="ERRO", origem="manual",
          lat=None, lon=None),
]


def test_fl_treino_zero_inclui_itens_sem_a_coluna():
    repo = _repo()
    repo.list_by_plantacao(plantacao_id="p1", fl_treino=0)
    for kw in repo._table.queries:
        assert "attribute_not_exists(fl_treino)" in kw["FilterExpression"]
        assert kw["ExpressionAttributeValues"][":flt"] == 0


def test_fl_treino_um_filtra_so_as_de_treino():
    repo = _repo()
    repo.list_by_plantacao(plantacao_id="p1", fl_treino=1)
    for kw in repo._table.queries:
        assert "fl_treino = :flt" in kw["FilterExpression"]
        assert kw["ExpressionAttributeValues"][":flt"] == 1


def test_sem_fl_treino_nao_filtra_nada():
    repo = _repo()
    repo.list_by_plantacao(plantacao_id="p1")
    for kw in repo._table.queries:
        assert "FilterExpression" not in kw
        assert ":flt" not in kw["ExpressionAttributeValues"]


def test_totais_saem_do_indice_e_respeitam_os_mesmos_filtros():
    repo = _repo(itens_scan=ITENS)
    total = lambda **f: repo.list_by_plantacao(plantacao_id="p1", **f)[1]  # noqa: E731

    assert total() == 4
    assert total(fl_treino=0) == 3          # a, b (sem coluna e 0) e d
    assert total(fl_treino=1) == 1
    assert total(fl_treino=0, status_geral="nao_saudavel") == 1
    assert total(status="ERRO") == 1
    assert total(origem="manual") == 1
    assert total(data_inicio="2026-09-30", data_fim="2026-10-01") == 2


def test_varios_filtros_dividem_uma_unica_leitura_da_tabela():
    pytest.importorskip("boto3")
    from infrastructure.dynamo_repository import SEGMENTOS_VARREDURA

    repo = _repo(itens_scan=ITENS)
    for filtro in ({}, {"fl_treino": 0}, {"status_geral": "saudavel"}, {"status": "ERRO"}):
        repo.list_by_plantacao(plantacao_id="p1", **filtro)
    repo.list_pontos_mapa(plantacao_id="p1", fl_treino=0)

    assert len(repo._table.scans) == SEGMENTOS_VARREDURA  # 1 varredura paralela no total
    kw = repo._table.scans[0]
    assert "contorno" not in kw["ProjectionExpression"]
    assert "analise_por_planta" not in kw["ProjectionExpression"]


def test_escrita_serve_o_indice_antigo_e_renova_em_segundo_plano():
    pytest.importorskip("boto3")
    import time

    from infrastructure.dynamo_repository import SEGMENTOS_VARREDURA

    repo = _repo(itens_scan=ITENS)
    repo.list_by_plantacao(plantacao_id="p1")
    repo._marcar_obsoleto()

    _, total = repo.list_by_plantacao(plantacao_id="p1")
    assert total == 4  # respondeu na hora, com o indice antigo

    for _ in range(40):  # espera a renovacao (thread) terminar
        if len(repo._table.scans) >= 2 * SEGMENTOS_VARREDURA:
            break
        time.sleep(0.05)
    assert len(repo._table.scans) == 2 * SEGMENTOS_VARREDURA


def test_pontos_do_mapa_vem_enxutos_filtrados_e_ordenados():
    repo = _repo(itens_scan=ITENS)
    pontos = repo.list_pontos_mapa(plantacao_id="p1", fl_treino=0)

    assert [p["captura_id"] for p in pontos] == ["d", "b", "a"]  # mais recente primeiro
    assert pontos[2]["status_geral"] == "saudavel"
    assert pontos[1]["status_geral"] == "nao_saudavel"
    assert set(pontos[0]) == {"captura_id", "timestamp", "latitude", "longitude", "status_geral"}
    assert repo.list_pontos_mapa(plantacao_id="p1", status_geral="nao_saudavel")[0][
        "captura_id"] == "c"
    assert repo._table.scans[0]["ExpressionAttributeValues"][":pk"] == "PLANT#p1"


class _RepoFalso:
    def __init__(self):
        self.chamadas = []

    def list_by_plantacao(self, **kwargs):
        self.chamadas.append(kwargs)
        return [], 0

    def list_pontos_mapa(self, **kwargs):
        self.chamadas.append(kwargs)
        return []


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


def test_mapa_monta_pontos_e_pula_sem_coordenada():
    pytest.importorskip("PIL")
    from application.use_cases import ListMapaCapturasUseCase

    class Repo:
        def list_pontos_mapa(self, **kwargs):
            return [
                {"captura_id": "a", "timestamp": "t1", "latitude": 1.23456789,
                 "longitude": 2, "status_geral": "saudavel"},
                {"captura_id": "b", "timestamp": "t2", "latitude": None,
                 "longitude": None, "status_geral": None},
            ]

    r = ListMapaCapturasUseCase(Repo()).execute()
    assert r["total"] == 1
    assert r["pontos"][0]["latitude"] == 1.234568
