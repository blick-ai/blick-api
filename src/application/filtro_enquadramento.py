import io

from PIL import Image

LIMIAR_VERDE_MINIMO = 0.12

TAMANHO_AMOSTRA = (100, 100)  # reduz a imagem antes de contar pixel, so por velocidade


def possui_verde_suficiente(image_bytes: bytes, limiar: float = LIMIAR_VERDE_MINIMO) -> bool:
    """
    Confere se a imagem tem verde suficiente pra sequer valer a pena
    classificar. Retorna True (passa) em caso de qualquer erro ao abrir
    a imagem — esse filtro nunca deve ser a causa de um erro de
    classificacao; se algo der errado aqui, deixa o modelo decidir.
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
    return concentracao >= limiar
