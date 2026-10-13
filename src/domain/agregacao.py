"""
Regra que junta as classificacoes POR PLANTA num status unico pra foto.

Fica aqui na API (e nao so no SageMaker) pra poder ser ajustada sem
reempacotar o modelo: o endpoint devolve o detalhe por planta
(analise_por_planta) e a API decide o status geral da foto.

REGRA PADRAO ("qualquer doente"): se o modelo achou UMA planta nao_saudavel na
foto, a foto e nao_saudavel. Sem limite de confianca, de area ou de quantidade,
e plantas aninhadas tambem contam. E uma regra de triagem: nao deixa passar
nada, e a conferencia de qual planta esta doente e feita olhando as marcacoes
no front. Foto so e saudavel se todas as plantas achadas forem saudaveis.

As regras antigas por limiar continuam no arquivo e voltam com a variavel
  AGREGACAO_MODO=limiar
(ou passando conf_min / n_min / fracao_min explicitamente na chamada).

Regras por limiar (so valem com AGREGACAO_MODO=limiar):
  1. planta nao_saudavel com confianca < conf_min e descartada (nao conta)
  2. a foto e nao_saudavel se
       (doentes validas >= n_min)  E  (fracao >= fracao_min)
     fracao = doentes validas / (saudaveis + doentes validas)
  3. foto sem nenhuma planta saudavel (so doentes validas) e nao_saudavel,
     mesmo com menos de n_min plantas

Regra por AREA (usada quando o endpoint devolve area_pct por planta):
  a foto e nao_saudavel se existir uma planta doente, NAO aninhada em outra
  maior, com confianca >= AGREGACAO_AREA_CONF_MIN e area >= AGREGACAO_AREA_MIN_PCT
  (% da foto). Fragmentos pequenos de folha seca e poligonos duplicados nao
  contam; adesivo vira uma doente grande. Sem area_pct, vale a regra acima.
  AGREGACAO_AREA_MIN_PCT   (padrao 0.8)
  AGREGACAO_AREA_CONF_MIN  (padrao 0.75)
  Planta doente ANINHADA (folha dentro de uma planta maior que o modelo chamou
  de saudavel) normalmente e ruido, mas uma folha com adesivo costuma aparecer
  assim: ela conta se for grande e muito confiante:
  AGREGACAO_ANINHADA_AREA_MIN_PCT   (padrao 1.5)
  AGREGACAO_ANINHADA_CONF_MIN       (padrao 0.90)

Os valores vem de variaveis de ambiente (padrao = confianca minima 0.90 e 2 ou
mais plantas doentes; antes era qualquer confianca):
  AGREGACAO_CONF_MIN     (padrao 0.90)
  AGREGACAO_N_MIN        (padrao 2)
  AGREGACAO_FRACAO_MIN   (padrao 0.0)
"""
import os
from typing import Optional


def _env_float(nome: str, padrao: float) -> float:
    try:
        return float(os.getenv(nome, padrao))
    except ValueError:
        return padrao


def _env_int(nome: str, padrao: int) -> int:
    try:
        return int(os.getenv(nome, padrao))
    except ValueError:
        return padrao


def agregar_qualquer_doente(plantas: list[dict]) -> Optional[tuple[str, float]]:
    """Uma planta nao_saudavel basta pra foto ser nao_saudavel.

    Confianca devolvida: a maior entre as doentes (nao_saudavel) ou a media das
    saudaveis (saudavel). None se nao ha nenhuma planta com classe conhecida.
    """
    saudaveis = [float(p.get("confianca", 0)) for p in plantas if p.get("classe") == "saudavel"]
    doentes = [
        float(p.get("confianca", 0)) for p in plantas if p.get("classe") == "nao_saudavel"
    ]
    if doentes:
        return "nao_saudavel", max(doentes)
    if saudaveis:
        return "saudavel", sum(saudaveis) / len(saudaveis)
    return None


def agregar_por_planta(
    plantas: list[dict],
    conf_min: Optional[float] = None,
    n_min: Optional[int] = None,
    fracao_min: Optional[float] = None,
) -> Optional[tuple[str, float]]:
    """
    plantas: [{"classe": "saudavel"|"nao_saudavel", "confianca": float}, ...]
    Retorna (status_geral, confianca) ou None se nao sobrou nenhuma planta
    valida pra decidir (quem chamou mantem o status que ja tinha).

    Padrao: qualquer planta doente torna a foto nao_saudavel. Usa as regras por
    limiar so com AGREGACAO_MODO=limiar ou quando algum limiar vem explicito.
    """
    explicito = conf_min is not None or n_min is not None or fracao_min is not None
    if not explicito and os.getenv("AGREGACAO_MODO", "qualquer").strip().lower() != "limiar":
        return agregar_qualquer_doente(plantas)
    return agregar_por_limiar(plantas, conf_min, n_min, fracao_min)


def agregar_por_limiar(
    plantas: list[dict],
    conf_min: Optional[float] = None,
    n_min: Optional[int] = None,
    fracao_min: Optional[float] = None,
) -> Optional[tuple[str, float]]:
    """Regras antigas (confianca minima, n minimo, fracao, area)."""
    conf_min = _env_float("AGREGACAO_CONF_MIN", 0.90) if conf_min is None else conf_min
    n_min = _env_int("AGREGACAO_N_MIN", 2) if n_min is None else n_min
    fracao_min = (
        _env_float("AGREGACAO_FRACAO_MIN", 0.0) if fracao_min is None else fracao_min
    )

    if any(p.get("area_pct") is not None for p in plantas):
        return _agregar_por_area(plantas)

    saudaveis: list[float] = []
    doentes: list[float] = []
    for p in plantas:
        confianca = float(p.get("confianca", 0))
        if p.get("classe") == "saudavel":
            saudaveis.append(confianca)
        elif confianca >= conf_min:
            doentes.append(confianca)

    validas = len(saudaveis) + len(doentes)
    if validas == 0:
        return None

    nao_saudavel = len(doentes) >= n_min and (len(doentes) / validas) >= fracao_min
    if not saudaveis and doentes:
        nao_saudavel = True

    if nao_saudavel:
        return "nao_saudavel", max(doentes)
    return "saudavel", sum(saudaveis) / len(saudaveis)


def _doente_conta(p, area_min, conf_min, area_aninhada, conf_aninhada) -> bool:
    confianca = float(p.get("confianca", 0))
    area = float(p.get("area_pct") or 0)
    if p.get("aninhada"):
        return confianca >= conf_aninhada and area >= area_aninhada
    return confianca >= conf_min and area >= area_min


def _agregar_por_area(plantas: list[dict]) -> Optional[tuple[str, float]]:
    area_min = _env_float("AGREGACAO_AREA_MIN_PCT", 0.8)
    conf_min = _env_float("AGREGACAO_AREA_CONF_MIN", 0.75)
    area_aninhada = _env_float("AGREGACAO_ANINHADA_AREA_MIN_PCT", 1.5)
    conf_aninhada = _env_float("AGREGACAO_ANINHADA_CONF_MIN", 0.90)

    saudaveis = [
        float(p.get("confianca", 0)) for p in plantas if p.get("classe") == "saudavel"
    ]
    doentes_uteis = [
        float(p.get("confianca", 0))
        for p in plantas
        if p.get("classe") != "saudavel"
        and _doente_conta(p, area_min, conf_min, area_aninhada, conf_aninhada)
    ]
    if doentes_uteis:
        return "nao_saudavel", max(doentes_uteis)
    if saudaveis:
        return "saudavel", sum(saudaveis) / len(saudaveis)
    return None
