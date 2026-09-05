import io
import statistics

from PIL import Image

# Limiar de concentracao de verde — voltou ao valor original (baixo,
# conservador), porque sozinho ele nunca resolveria o problema de fundo
# verde generico mesmo subindo (grama/parede pintada podem ter tanto ou
# mais verde que milho real). A defesa real contra isso agora e a
# checagem de VARIACAO (abaixo), nao esse numero.
LIMIAR_VERDE_MINIMO = 0.12

# Como o dataset de treino (Roboflow) so tem saudavel/nao_saudavel — sem
# nenhum exemplo de "isso nao e milho" — o modelo NUNCA vai aprender a
# dizer "nao e milho" sozinho, nao importa quanto ele seja refinado. Essa
# responsabilidade e inteiramente desse filtro, que roda ANTES do
# modelo. Por isso, alem de conferir concentracao de verde, tambem
# confere VARIACAO de tom — uma planta de verdade (folhas, sombra, caule,
# luz variando de ponto a ponto) tem bastante variacao; uma cor quase
# uniforme (parede pintada, tela mostrando verde solido, grama cortada
# rente fotografada de perto) tem pouca. As duas condicoes precisam
# passar juntas — "verde o suficiente" E "variado o suficiente" — senao
# cai direto em nao_milho, sem nem chamar o modelo.
LIMIAR_DESVIO_PADRAO_MINIMO = 12.0

TAMANHO_AMOSTRA = (100, 100)  # reduz a imagem antes de processar, so por velocidade


def possui_verde_suficiente(
    image_bytes: bytes,
    limiar: float = LIMIAR_VERDE_MINIMO,
    limiar_variacao: float = LIMIAR_DESVIO_PADRAO_MINIMO,
) -> bool:
    """
    Confere se a imagem parece minimamente uma planta de verdade, antes
    de sequer valer a pena mandar pro modelo. Duas condicoes, as DUAS
    precisam passar:

    1. Tem concentracao de verde suficiente (pega os casos obvios: mao
       na frente da camera, foto noturna, corredor interno)
    2. Tem variacao de tom suficiente (pega fundo verde uniforme: parede
       pintada, tela de celular, grama cortada rente)

    Retorna True (passa, deixa o modelo decidir) em caso de qualquer erro
    ao abrir a imagem — esse filtro nunca deve ser a causa de um erro de
    classificacao.

    LIMITACAO CONHECIDA: isso ainda e heuristica, nao um modelo treinado
    pra reconhecer milho. Uma foto de outra planta real (nao milho), com
    folhagem variada, pode passar nas duas condicoes e chegar no modelo
    mesmo assim — a correcao definitiva pra esse caso especifico e um
    modelo dedicado de "isso e milho?", que roda antes desse filtro
    (arquitetura de 2 etapas discutida, ainda nao implementada).
    """
    try:
        imagem = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        imagem.thumbnail(TAMANHO_AMOSTRA)
        pixels = list(imagem.getdata())
    except Exception:
        return True

    if not pixels:
        return True

    verdes = sum(1 for (r, g, b) in pixels if g > r * 1.1 and g > b * 1.1 and g > 40)
    concentracao = verdes / len(pixels)
    if concentracao < limiar:
        return False

    # desvio padrao da luminosidade — uma cor solida/uniforme tem
    # variacao baixa, uma cena de verdade (planta, sombra, textura) tem
    # variacao alta
    luminosidades = [0.299 * r + 0.587 * g + 0.114 * b for (r, g, b) in pixels]
    desvio = statistics.pstdev(luminosidades)

    return desvio >= limiar_variacao