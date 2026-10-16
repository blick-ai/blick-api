"""Como as plantas de uma captura saem na tela de detalhe."""


def plantas_para_exibicao(analise: list[dict]) -> list[dict]:
    """Planta doente sempre aparece na foto: nao sai como 'aninhada' (o front
    esconde as aninhadas) e vem por ultimo, pra ser desenhada por cima das
    saudaveis que cobrem a mesma area. Devolve copias; os dados guardados
    (e a regra de agregacao, que usa o 'aninhada' original) nao mudam."""
    ordenadas = sorted(analise, key=lambda p: p.get("classe") == "nao_saudavel")
    return [
        {**p, "aninhada": False} if p.get("classe") == "nao_saudavel" else dict(p)
        for p in ordenadas
    ]
