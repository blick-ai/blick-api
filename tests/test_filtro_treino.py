import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


class _TabelaFalsa:
    """Tabela falsa: scan alimenta o indice, put/delete registram escritas."""

    name = "blick-table"

    def __init__(self, itens_scan=None):
        self.scans = []
        self.puts = []
        self.deletes = []
        self._itens_scan = list(itens_scan or [])  # copia: put_item acrescenta

    def query(self, **kwargs):
        raise AssertionError("a listagem nao deve mais usar Query com filtro")

    def scan(self, **kwargs):
        self.scans.append(kwargs)
        # so o segmento 0 devolve os itens, pra nao duplicar entre segmentos
        itens = self._itens_scan if kwargs.get("Segment") == 0 else []
        return {"Items": itens, "Count": len(itens)}

    def put_item(self, **kwargs):
        self.puts.append(kwargs)
        self._itens_scan = [i for i in self._itens_scan if i["SK"] != kwargs["Item"]["SK"]]
        self._itens_scan.append(kwargs["Item"])

    def delete_item(self, **kwargs):
        self.deletes.append(kwargs)


class _DynamoFalso:
    def __init__(self, tabela):
        self._tabela = tabela
        self.pedidos = []

    def batch_get_item(self, RequestItems):
        self.pedidos.append(RequestItems)
        nome = self._tabela.name
        por_sk = {i["SK"]: i for i in self._tabela._itens_scan}
        chaves = RequestItems[nome]["Keys"]
        # devolve fora de ordem de proposito: o repositorio tem que reordenar
        itens = [por_sk[c["SK"]] for c in reversed(chaves) if c["SK"] in por_sk]
        return {"Responses": {nome: itens}}


def _repo(itens_scan=None, monkeypatch=None):
    pytest.importorskip("boto3")
    from infrastructure import dynamo_repository
    from infrastructure.dynamo_repository import DynamoCapturaRepository

    if monkeypatch is not None:  # as paginas voltam como o proprio item, sem montar Captura
        monkeypatch.setattr(dynamo_repository.Captura, "from_dynamo_item",
                            staticmethod(lambda item: item))
    repo = object.__new__(DynamoCapturaRepository)
    repo._table = _TabelaFalsa(itens_scan)
    repo._dynamodb = _DynamoFalso(repo._table)
    return repo


def _item(sk, status_geral=None, fl_treino=None, status="CONCLUIDO", origem="rover",
          lat=1, lon=2):
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


def _ids(repo, **filtros):
    capturas, total = repo.list_by_plantacao(plantacao_id="p1", **filtros)
    return [c["captura_id"] for c in capturas], total


def test_filtros_valem_igual_a_consulta_antiga(monkeypatch):
    repo = _repo(ITENS, monkeypatch)

    assert _ids(repo) == (["d", "c", "b", "a"], 4)
    assert _ids(repo, fl_treino=0) == (["d", "b", "a"], 3)  # inclui quem nao tem a coluna
    assert _ids(repo, fl_treino=1) == (["c"], 1)
    assert _ids(repo, fl_treino=0, status_geral="nao_saudavel") == (["b"], 1)
    assert _ids(repo, status="ERRO") == (["d"], 1)
    assert _ids(repo, origem="manual") == (["d"], 1)
    assert _ids(repo, data_inicio="2026-09-30", data_fim="2026-10-01") == (["c", "b"], 2)


def test_status_geral_aceita_varios_valores_separados_por_virgula(monkeypatch):
    repo = _repo(ITENS, monkeypatch)

    # o front pede "saudavel,nao_saudavel" numa chamada so, em vez de duas de 100 itens
    assert _ids(repo, status_geral="saudavel,nao_saudavel", fl_treino=0) == (["b", "a"], 2)
    assert _ids(repo, status_geral="nao_saudavel") == (["c", "b"], 2)
    assert _ids(repo, status_geral="saudavel") == (["a"], 1)


def test_listagem_leve_nao_busca_o_detalhe_por_planta(monkeypatch):
    repo = _repo(ITENS, monkeypatch)

    repo.list_by_plantacao(plantacao_id="p1", tamanho_pagina=2, completo=False)
    leve = repo._dynamodb.pedidos[-1]["blick-table"]
    assert "analise_por_planta" not in leve["ProjectionExpression"]
    assert "ia_nuvem.status_geral" in leve["ProjectionExpression"]
    # palavras reservadas do DynamoDB entram por apelido, senao a consulta falha
    assert leve["ExpressionAttributeNames"] == {
        "#ts": "timestamp", "#st": "status", "#ttl": "ttl"}
    for campo in ("#ts", "#st", "#ttl", "s3_key", "jetson_nano", "cliente_id", "GSI1PK"):
        assert campo in leve["ProjectionExpression"]

    repo.list_by_plantacao(plantacao_id="p1", tamanho_pagina=2)  # padrao: completo
    completo = repo._dynamodb.pedidos[-1]["blick-table"]
    # reclassificar/backfill gravam a captura de volta: tem que vir inteira
    assert "ProjectionExpression" not in completo


def test_paginacao_pega_so_a_fatia_e_busca_so_ela_por_chave(monkeypatch):
    repo = _repo(ITENS, monkeypatch)

    ids, total = _ids(repo, pagina=2, tamanho_pagina=2)
    assert (ids, total) == (["b", "a"], 4)  # ordem mantida mesmo com o Dynamo fora de ordem

    chaves = repo._dynamodb.pedidos[-1]["blick-table"]["Keys"]
    assert [c["SK"].split("#")[-1] for c in chaves] == ["b", "a"]
    assert all(c["PK"] == "PLANT#p1" for c in chaves)


def test_varias_listagens_dividem_uma_unica_leitura_da_tabela(monkeypatch):
    pytest.importorskip("boto3")
    from infrastructure.dynamo_repository import SEGMENTOS_VARREDURA

    repo = _repo(ITENS, monkeypatch)
    for filtro in ({}, {"fl_treino": 0}, {"status_geral": "saudavel"}, {"status": "ERRO"}):
        repo.list_by_plantacao(plantacao_id="p1", **filtro)
    repo.list_pontos_mapa(plantacao_id="p1", fl_treino=0)

    assert len(repo._table.scans) == SEGMENTOS_VARREDURA  # 1 varredura paralela no total
    kw = repo._table.scans[0]
    assert "contorno" not in kw["ProjectionExpression"]
    assert "analise_por_planta" not in kw["ProjectionExpression"]


def _captura_falsa(captura_id, timestamp, status_geral="saudavel", fl_treino=0):
    from types import SimpleNamespace

    return SimpleNamespace(
        captura_id=captura_id, timestamp=timestamp, plantacao_id="p1", status="CONCLUIDO",
        origem="rover", fl_treino=fl_treino,
        coordenadas=SimpleNamespace(latitude=5, longitude=6),
        ia_nuvem={"status_geral": status_geral},
        to_dynamo_item=lambda: {"SK": f"CAPTURA#{timestamp}#{captura_id}",
                                "captura_id": captura_id},
    )


def test_captura_nova_aparece_no_indice_na_hora_sem_nova_varredura(monkeypatch):
    pytest.importorskip("boto3")
    from infrastructure.dynamo_repository import SEGMENTOS_VARREDURA

    repo = _repo(ITENS, monkeypatch)
    assert _ids(repo)[1] == 4

    repo.save(_captura_falsa("e", "2026-10-03T10:00:00"))
    ids, total = _ids(repo, tamanho_pagina=2)
    assert total == 5
    assert ids[0] == "e"  # a mais nova ja vem na frente
    assert len(repo._table.scans) == SEGMENTOS_VARREDURA

    repo.update(_captura_falsa("e", "2026-10-03T10:00:00", fl_treino=1))
    assert _ids(repo, fl_treino=1)[1] == 2  # c e e

    repo.delete("p1", "2026-10-03T10:00:00", "e")
    assert _ids(repo)[1] == 4
    assert repo._table.deletes[0]["Key"]["SK"] == "CAPTURA#2026-10-03T10:00:00#e"


def test_indice_velho_responde_na_hora_e_renova_em_segundo_plano(monkeypatch):
    pytest.importorskip("boto3")
    import time

    from infrastructure.dynamo_repository import _OBSOLETO, SEGMENTOS_VARREDURA

    repo = _repo(ITENS, monkeypatch)
    _ids(repo)
    repo._indices()["p1"]["carregado_em"] = _OBSOLETO  # passou do TTL

    assert _ids(repo)[1] == 4  # respondeu na hora, com o indice antigo

    for _ in range(40):  # espera a renovacao (thread) terminar
        if len(repo._table.scans) >= 2 * SEGMENTOS_VARREDURA:
            break
        time.sleep(0.05)
    assert len(repo._table.scans) == 2 * SEGMENTOS_VARREDURA


def test_renovacao_descarta_leitura_que_perdeu_uma_escrita(monkeypatch):
    repo = _repo(ITENS, monkeypatch)
    _ids(repo)
    carregar = repo._carregar_indice

    def carregar_e_escrever(plantacao_id):
        linhas = carregar(plantacao_id)  # leitura sem a captura nova...
        repo.save(_captura_falsa("e", "2026-10-03T10:00:00"))  # ...e a escrita entra no meio
        return linhas

    repo._carregar_indice = carregar_e_escrever
    repo._indices()["p1"]["renovando"] = True
    repo._renovar_indice("p1")

    assert _ids(repo)[1] == 5  # a captura nova nao some


def test_pontos_do_mapa_vem_enxutos_filtrados_e_ordenados(monkeypatch):
    repo = _repo(ITENS, monkeypatch)
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
    assert listagem["completo"] is False  # a tela nao precisa dos contornos
    assert mapa["fl_treino"] == 0
    assert "fl_treino" not in manutencao  # a reclassificacao precisa ver tudo
    assert "completo" not in manutencao  # e precisa da captura inteira, pra gravar de volta


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
