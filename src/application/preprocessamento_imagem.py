import io
from datetime import datetime

from PIL import ExifTags, Image

# limite REAL e rigido do SageMaker Serverless Inference: 4 MB de payload,
# sem excecao, nao da pra configurar (fonte: docs.aws.amazon.com/sagemaker/
# latest/dg/serverless-endpoints-invoke.html, confirmado em ago/2026).
#
# Estrategia: comeca com qualidade BEM alta (pouca perda visual) e so
# reduz progressivamente se a imagem especifica realmente precisar —
# a maioria das fotos reais de folha deve passar de primeira, sem perda
# de qualidade perceptivel. So fotos incomuns (muito grandes/detalhadas)
# passam pelas tentativas seguintes.
TAMANHO_INICIAL = 1600
QUALIDADE_INICIAL = 92
LIMITE_SEGURO_BYTES = 3 * 1024 * 1024  # 3 MB — 1 MB de folga sob o limite de 4 MB do SageMaker
MAX_TENTATIVAS = 6


def redimensionar_para_classificacao(image_bytes: bytes) -> bytes:
    """
    Reduz o tamanho da imagem SO O NECESSARIO pra caber com folga no
    limite de payload do SageMaker Serverless (4 MB, rigido). Comeca em
    qualidade alta (1600px, JPEG 92) e so degrada mais se a imagem
    especifica nao couber nesse primeiro nivel. Se der qualquer erro ao
    processar, devolve os bytes originais — melhor tentar classificar do
    jeito que veio do que travar a captura inteira por causa disso.
    """
    try:
        imagem_original = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception:
        return image_bytes

    tamanho = TAMANHO_INICIAL
    qualidade = QUALIDADE_INICIAL
    resultado = image_bytes

    for _ in range(MAX_TENTATIVAS):
        imagem = imagem_original.copy()
        imagem.thumbnail((tamanho, tamanho))
        buffer = io.BytesIO()
        imagem.save(buffer, format="JPEG", quality=qualidade)
        resultado = buffer.getvalue()

        if len(resultado) <= LIMITE_SEGURO_BYTES:
            return resultado

        # essa tentativa ainda ficou grande demais — reduz mais e tenta de novo
        tamanho = int(tamanho * 0.8)
        qualidade = max(60, qualidade - 10)

    # esgotou as tentativas — devolve a ultima (menor) mesmo assim, e essa
    # sim tem uma chance real de ainda estourar o limite em casos extremos,
    # mas e um cenario raro o suficiente pra nao valer mais complexidade aqui
    return resultado


TAMANHO_THUMBNAIL = 300  # pixels no maior lado — suficiente pra um quadradinho de lista
QUALIDADE_THUMBNAIL = 80


def gerar_thumbnail(image_bytes: bytes) -> bytes:
    """
    Gera uma miniatura pequena pra usar na LISTAGEM geral — sem isso, o
    front baixa a foto em resolucao original (varios MB, comum em fotos
    de celular) so pra mostrar um quadradinho de 64px, desperdicando
    banda e deixando a lista lenta pra carregar. A foto original continua
    intacta no S3, usada normalmente no detalhe/classificacao — isso aqui
    e so uma copia extra, menor, pensada exclusivamente pra exibicao.

    Se der qualquer erro ao processar, devolve None — nesse caso o
    chamador deve usar a imagem original mesmo (fallback), em vez de
    travar o upload por causa de uma miniatura que nao e essencial.
    """
    try:
        imagem = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        imagem.thumbnail((TAMANHO_THUMBNAIL, TAMANHO_THUMBNAIL))
        buffer = io.BytesIO()
        imagem.save(buffer, format="JPEG", quality=QUALIDADE_THUMBNAIL)
        return buffer.getvalue()
    except Exception:
        return None


def extrair_timestamp_exif(image_bytes: bytes) -> str | None:
    """
    Le a data/hora em que a foto foi tirada de verdade, a partir dos
    metadados EXIF — usado no upload manual (sem data digitada pelo
    usuario, a foto ja carrega isso sozinha).

    Tenta primeiro a tag "DateTimeOriginal" (0x9003, na Exif SubIFD —
    e o campo correto/padrao pra "momento do disparo"), e cai pra
    "DateTime" (0x0132, no IFD principal) como alternativa mais simples
    se a primeira nao existir.

    Retorna None se a foto nao tiver EXIF nenhum (comum em screenshots,
    ou fotos que passaram por apps de mensagem que removem metadados) —
    nesse caso, quem chama deve usar a hora atual do servidor como
    substituto, em vez de travar o upload.
    """
    try:
        imagem = Image.open(io.BytesIO(image_bytes))
        exif = imagem.getexif()
        if not exif:
            return None

        bruto = None
        try:
            sub_ifd = exif.get_ifd(ExifTags.IFD.Exif)
            bruto = sub_ifd.get(0x9003)  # DateTimeOriginal
        except Exception:
            pass

        if not bruto:
            bruto = exif.get(0x0132)  # DateTime (fallback mais simples)

        if not bruto:
            return None

        momento = datetime.strptime(bruto, "%Y:%m:%d %H:%M:%S")
        return momento.strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return None
