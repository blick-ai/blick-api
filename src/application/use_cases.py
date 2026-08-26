import base64
import uuid
from datetime import datetime

from application.filtro_enquadramento import possui_verde_suficiente
from application.preprocessamento_imagem import (
    extrair_timestamp_exif,
    gerar_thumbnail,
    redimensionar_para_classificacao,
)
from application.dtos import (
    CapturaDetalheDTO,
    CapturaInputDTO,
    CapturaOutputDTO,
    CapturaResumoDTO,
    CapturaSimplesInputDTO,
    ListCapturasOutputDTO,
    ListClientesOutputDTO,
)
from domain.entities import (
    Captura,
    ClassificacaoResultado,
    Coordenadas,
    JetsonNanoInfo,
    StatusEntry,
)
from domain.ports import ICapturaRepository, IClassificationService, IStorageService

MOCK_PLANTACAO_ID = "plantacao-mock-001"
MOCK_CARRINHO_ID = "carrinho-mock-001"


class SubmitCapturaUseCase:
    def __init__(
        self,
        storage: IStorageService,
        repository: ICapturaRepository,
        s3_bucket: str,
    ):
        self._storage = storage
        self._repository = repository
        self._s3_bucket = s3_bucket

    def execute(self, dto: CapturaInputDTO) -> CapturaOutputDTO:
        image_bytes = base64.b64decode(dto.imagem_base64)

        now = datetime.utcnow()
        timestamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        short_uuid = uuid.uuid4().hex[:8]
        captura_id = f"{now.strftime('%Y%m%d%H%M%S')}-{short_uuid}"

        date = datetime.strptime(dto.dia_mes_ano, "%d/%m/%Y")
        dia, mes, ano = date.strftime("%d"), date.strftime("%m"), date.strftime("%Y")
        s3_key = f"{dto.cliente_id}/{ano}/{mes}/{dia}/{captura_id}.jpg"

        self._storage.upload_image(s3_key, image_bytes)

        # miniatura pequena pra listagem geral — se der erro ao gerar,
        # simplesmente nao sobe nenhuma (thumbnail_key fica None); o
        # detalhe/classificacao usam a imagem original de qualquer forma,
        # entao isso nunca deve travar o upload
        thumbnail_key = None
        thumbnail_bytes = gerar_thumbnail(image_bytes)
        if thumbnail_bytes is not None:
            thumbnail_key = f"{dto.cliente_id}/{ano}/{mes}/{dia}/{captura_id}_thumb.jpg"
            try:
                self._storage.upload_image(thumbnail_key, thumbnail_bytes)
            except Exception:
                thumbnail_key = None

        captura = Captura(
            captura_id=captura_id,
            cliente_id=dto.cliente_id,
            plantacao_id=MOCK_PLANTACAO_ID,
            carrinho_id=MOCK_CARRINHO_ID,
            timestamp=timestamp,
            coordenadas=Coordenadas(
                latitude=dto.latitude,
                longitude=dto.longitude,
            ),
            s3_bucket=self._s3_bucket,
            s3_key=s3_key,
            thumbnail_key=thumbnail_key,
            jetson_nano=JetsonNanoInfo(
                planta_detectada=True,
                confianca=dto.confianca_borda if dto.confianca_borda is not None else 0.0,
                # antes fixo em "ia-blick-v2" mesmo quando o worker de envio
                # do Klar ja manda a versao real do modelo de borda (ver
                # capturar_zed.py — plants_v1.tflite, nao ia-blick-v2).
                # Agora usa o que vier do cliente, com fallback pra nao quebrar
                # chamadas antigas que ainda nao mandam esse campo.
                modelo_versao=dto.modelo_versao_borda or "desconhecida",
            ),
            status="PENDENTE",
            status_history=[StatusEntry(status="PENDENTE", timestamp=timestamp)],
            origem="rover",  # explicito de proposito — nao depende do valor padrao da classe
        )

        self._repository.save(captura)

        return CapturaOutputDTO(
            sucesso=True,
            captura_id=captura_id,
            s3_key=s3_key,
            timestamp=timestamp,
            plantacao_id=MOCK_PLANTACAO_ID,
        )


class SubmitCapturaSimplesUseCase:
    """
    Upload manual simplificado — recebe SO a foto, sem data nem
    coordenadas. O timestamp vem do EXIF da propria imagem (quando a
    foto foi tirada de verdade); se a foto nao tiver esse metadado
    (screenshot, imagem que passou por app que remove EXIF, etc.), usa
    a hora atual do servidor como substituto.

    Coordenadas ficam vazias de proposito — quem faz upload manual ja
    sabe onde tirou a foto, nao faz sentido pedir isso no formulario
    (e providenciar via Google Maps foi removido justamente por causa
    disso).
    """

    def __init__(
        self,
        storage: IStorageService,
        repository: ICapturaRepository,
        s3_bucket: str,
    ):
        self._storage = storage
        self._repository = repository
        self._s3_bucket = s3_bucket

    def execute(self, dto: CapturaSimplesInputDTO) -> CapturaOutputDTO:
        image_bytes = base64.b64decode(dto.imagem_base64)

        timestamp_exif = extrair_timestamp_exif(image_bytes)
        if timestamp_exif is not None:
            momento = datetime.strptime(timestamp_exif, "%Y-%m-%dT%H:%M:%SZ")
        else:
            momento = datetime.utcnow()
        timestamp = momento.strftime("%Y-%m-%dT%H:%M:%SZ")

        short_uuid = uuid.uuid4().hex[:8]
        captura_id = f"{momento.strftime('%Y%m%d%H%M%S')}-{short_uuid}"
        dia, mes, ano = momento.strftime("%d"), momento.strftime("%m"), momento.strftime("%Y")
        s3_key = f"{dto.cliente_id}/{ano}/{mes}/{dia}/{captura_id}.jpg"

        self._storage.upload_image(s3_key, image_bytes)

        thumbnail_key = None
        thumbnail_bytes = gerar_thumbnail(image_bytes)
        if thumbnail_bytes is not None:
            thumbnail_key = f"{dto.cliente_id}/{ano}/{mes}/{dia}/{captura_id}_thumb.jpg"
            try:
                self._storage.upload_image(thumbnail_key, thumbnail_bytes)
            except Exception:
                thumbnail_key = None

        captura = Captura(
            captura_id=captura_id,
            cliente_id=dto.cliente_id,
            plantacao_id=MOCK_PLANTACAO_ID,
            carrinho_id=MOCK_CARRINHO_ID,
            timestamp=timestamp,
            coordenadas=Coordenadas(latitude=None, longitude=None),
            s3_bucket=self._s3_bucket,
            s3_key=s3_key,
            thumbnail_key=thumbnail_key,
            jetson_nano=JetsonNanoInfo(
                planta_detectada=True,
                confianca=0.0,
                modelo_versao="upload-manual",
            ),
            status="PENDENTE",
            status_history=[StatusEntry(status="PENDENTE", timestamp=timestamp)],
            origem="manual",
        )

        self._repository.save(captura)

        return CapturaOutputDTO(
            sucesso=True,
            captura_id=captura_id,
            s3_key=s3_key,
            timestamp=timestamp,
            plantacao_id=MOCK_PLANTACAO_ID,
        )


class ClassifyCapturaUseCase:
    """
    Baixa a imagem da captura, manda pro modelo de nuvem (via
    IClassificationService) e atualiza a captura com o resultado.

    Pensado pra ser chamado de forma assincrona (worker separado, nao no
    mesmo request de SubmitCapturaUseCase) — ver conversa sobre rajada de
    capturas quando o Klar volta a ter Wi-Fi, que motivou esse desenho.
    """

    def __init__(
        self,
        repository: ICapturaRepository,
        storage: IStorageService,
        classifier: IClassificationService,
    ):
        self._repository = repository
        self._storage = storage
        self._classifier = classifier

    def execute(self, plantacao_id: str, timestamp: str, captura_id: str) -> Captura:
        captura = self._repository.get(plantacao_id, timestamp, captura_id)
        if captura is None:
            raise ValueError(f"Captura não encontrada: {captura_id}")

        agora = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

        try:
            image_bytes = self._storage.download_image(captura.s3_key)
            image_bytes = redimensionar_para_classificacao(image_bytes)

            if possui_verde_suficiente(image_bytes):
                resultado = self._classifier.classify(image_bytes)
            else:
                # nao vale a pena gastar uma chamada no SageMaker numa
                # imagem sem verde suficiente pra ter chance de ser milho
                # (pulso bloqueando a camera, foto noturna, corredor
                # interno...) — ja cai direto como nao_milho
                resultado = ClassificacaoResultado(
                    status_geral="nao_milho",
                    confianca_status_geral=1.0,
                    probabilidades={"saudavel": 0.0, "praga": 0.0, "doenca": 0.0, "nao_milho": 1.0},
                    origem="filtro_enquadramento",
                )
        except Exception as e:
            captura.status = "ERRO"
            captura.erro_detalhes = str(e)
            captura.status_history.append(StatusEntry(status="ERRO", timestamp=agora))
            self._repository.update(captura)
            raise

        captura.ia_nuvem = resultado.to_dict()
        captura.status = "CLASSIFICADO"
        # limpa erro de uma tentativa anterior mal sucedida, se houver —
        # sem isso, reclassificar uma captura que falhou antes deixava a
        # mensagem de erro velha "grudada" mesmo com sucesso agora
        captura.erro_detalhes = None
        captura.status_history.append(StatusEntry(status="CLASSIFICADO", timestamp=agora))

        # alerta so faz sentido se nao for planta saudavel nem "nao_milho"
        # (nao_milho e ruido de captura, nao problema na lavoura)
        if resultado.status_geral in ("praga", "doenca"):
            captura.alerta_emitido = True
            captura.alerta_emitido_em = agora

        self._repository.update(captura)
        return captura


class ClassifyPendentesUseCase:
    """Processa em lote as capturas que ainda estao com status PENDENTE."""

    def __init__(self, repository: ICapturaRepository, classify_use_case: ClassifyCapturaUseCase):
        self._repository = repository
        self._classify_use_case = classify_use_case

    def execute(self, limite: int = 50) -> dict:
        pendentes = self._repository.list_by_status(
            "PENDENTE", plantacao_id=MOCK_PLANTACAO_ID, limit=limite
        )
        processadas, erros = 0, 0

        for captura in pendentes:
            try:
                self._classify_use_case.execute(
                    captura.plantacao_id, captura.timestamp, captura.captura_id
                )
                processadas += 1
            except Exception:
                erros += 1

        return {"total": len(pendentes), "processadas": processadas, "erros": erros}


class ReclassificarTodasUseCase:
    """
    Reclassifica capturas em lote, INDEPENDENTE do status atual (inclusive
    as ja CLASSIFICADAS antes) — usado quando uma mudanca no pipeline
    (por exemplo, o filtro de enquadramento) precisa ser aplicada
    retroativamente a capturas que ja tinham sido processadas.

    Diferente de ClassifyPendentesUseCase (onde o conjunto "pendente"
    encolhe sozinho a cada chamada), aqui o conjunto NAO encolhe — a
    captura continua CLASSIFICADO depois de reclassificada. Por isso usa
    paginacao explicita (pagina 1, 2, 3...) em vez de repetir ate total
    zerar.
    """

    def __init__(self, repository: ICapturaRepository, classify_use_case: ClassifyCapturaUseCase):
        self._repository = repository
        self._classify_use_case = classify_use_case

    def execute(
        self,
        plantacao_id: str = MOCK_PLANTACAO_ID,
        pagina: int = 1,
        tamanho_pagina: int = 20,
    ) -> dict:
        capturas, total = self._repository.list_by_plantacao(
            plantacao_id=plantacao_id, pagina=pagina, tamanho_pagina=tamanho_pagina
        )
        processadas, erros = 0, 0

        for captura in capturas:
            try:
                self._classify_use_case.execute(
                    captura.plantacao_id, captura.timestamp, captura.captura_id
                )
                processadas += 1
            except Exception:
                erros += 1

        total_paginas = (total + tamanho_pagina - 1) // tamanho_pagina if total > 0 else 0
        return {
            "pagina": pagina,
            "tamanho_pagina": tamanho_pagina,
            "total": total,
            "total_paginas": total_paginas,
            "processadas": processadas,
            "erros": erros,
        }


class ListClientesUseCase:
    def __init__(self, repository: ICapturaRepository):
        self._repository = repository

    def execute(self) -> ListClientesOutputDTO:
        cliente_ids = self._repository.list_cliente_ids()
        return ListClientesOutputDTO(cliente_ids=cliente_ids)


def _resumo_de(captura: Captura, storage: IStorageService) -> CapturaResumoDTO:
    ia = captura.ia_nuvem or {}
    confianca_str = ia.get("confianca_status_geral")

    try:
        # usa a miniatura pequena, quando existe — bem mais rapida pra
        # carregar numa lista. Capturas antigas (de antes dessa feature)
        # nao tem thumbnail_key, entao caem no fallback da imagem
        # original mesmo (mais lenta, mas ainda funciona)
        chave_imagem = captura.thumbnail_key or captura.s3_key
        imagem_url = storage.generate_presigned_url(chave_imagem)
    except Exception:
        # gerar a URL assinada e um calculo local (nao faz chamada de rede
        # pro S3), mas se por algum motivo falhar, o resto do resumo ainda
        # e util — nao derruba a listagem inteira por causa de uma imagem
        imagem_url = None

    return CapturaResumoDTO(
        captura_id=captura.captura_id,
        timestamp=captura.timestamp,
        status=captura.status,
        status_geral=ia.get("status_geral"),
        confianca_status_geral=float(confianca_str) if confianca_str is not None else None,
        latitude=captura.coordenadas.latitude,
        longitude=captura.coordenadas.longitude,
        alerta_emitido=captura.alerta_emitido,
        imagem_url=imagem_url,
        origem=captura.origem,
    )


class ListCapturasUseCase:
    """
    GET geral — lista enxuta de capturas de uma plantacao, mais recentes
    primeiro por padrao. Suporta filtro por status_geral (saudavel/praga/
    doenca/nao_milho), por periodo de data, e paginacao numerada (8 por
    pagina por padrao). Pensado pra alimentar dashboard/mapa/tabela, nao
    pra trazer o detalhe completo de cada item (isso e o GetCapturaUseCase).
    """

    def __init__(self, repository: ICapturaRepository, storage: IStorageService):
        self._repository = repository
        self._storage = storage

    def execute(
        self,
        plantacao_id: str = MOCK_PLANTACAO_ID,
        status: str | None = None,
        status_geral: str | None = None,
        origem: str | None = None,
        data_inicio: str | None = None,
        data_fim: str | None = None,
        pagina: int = 1,
        tamanho_pagina: int = 8,
    ) -> ListCapturasOutputDTO:
        capturas, total = self._repository.list_by_plantacao(
            plantacao_id=plantacao_id,
            status=status,
            status_geral=status_geral,
            origem=origem,
            data_inicio=data_inicio,
            data_fim=data_fim,
            pagina=pagina,
            tamanho_pagina=tamanho_pagina,
        )
        total_paginas = (total + tamanho_pagina - 1) // tamanho_pagina if total > 0 else 0
        return ListCapturasOutputDTO(
            capturas=[_resumo_de(c, self._storage) for c in capturas],
            pagina=pagina,
            tamanho_pagina=tamanho_pagina,
            total=total,
            total_paginas=total_paginas,
        )


class GetCapturaUseCase:
    """GET especifico — detalhe completo de uma captura, incluindo URL
    assinada da imagem (o front nao precisa de credencial AWS pra exibir
    a foto — a URL ja vem pronta pra usar direto num <img src=...>)."""

    def __init__(self, repository: ICapturaRepository, storage: IStorageService):
        self._repository = repository
        self._storage = storage

    def execute(
        self, plantacao_id: str, timestamp: str, captura_id: str
    ) -> CapturaDetalheDTO | None:
        captura = self._repository.get(plantacao_id, timestamp, captura_id)
        if captura is None:
            return None

        ia = captura.ia_nuvem or {}
        probabilidades = ia.get("probabilidades")
        if probabilidades is not None:
            probabilidades = {k: float(v) for k, v in probabilidades.items()}

        confianca_status_str = ia.get("confianca_status_geral")
        confianca_subtipo_str = ia.get("confianca_subtipo")

        try:
            imagem_url = self._storage.generate_presigned_url(captura.s3_key)
        except Exception:
            # se a URL nao puder ser gerada por algum motivo, o resto do
            # detalhe ainda e util — nao derruba a resposta inteira por isso
            imagem_url = None

        return CapturaDetalheDTO(
            captura_id=captura.captura_id,
            plantacao_id=captura.plantacao_id,
            carrinho_id=captura.carrinho_id,
            cliente_id=captura.cliente_id,
            timestamp=captura.timestamp,
            status=captura.status,
            latitude=captura.coordenadas.latitude,
            longitude=captura.coordenadas.longitude,
            status_geral=ia.get("status_geral"),
            confianca_status_geral=(
                float(confianca_status_str) if confianca_status_str is not None else None
            ),
            subtipo=ia.get("subtipo"),
            confianca_subtipo=(
                float(confianca_subtipo_str) if confianca_subtipo_str is not None else None
            ),
            probabilidades=probabilidades,
            modelo_versao_borda=captura.jetson_nano.modelo_versao,
            confianca_borda=captura.jetson_nano.confianca,
            imagem_url=imagem_url,
            status_history=[
                {"status": e.status, "timestamp": e.timestamp} for e in captura.status_history
            ],
            erro_detalhes=captura.erro_detalhes,
            alerta_emitido=captura.alerta_emitido,
            origem=captura.origem,
            alerta_emitido_em=captura.alerta_emitido_em,
        )


class DeletarCapturaUseCase:
    """
    Exclusao definitiva de uma captura — usado quando o usuario revisa o
    detalhe e conclui que a classificacao esta errada/nao serve pra nada
    (foto invalida, engano de captura, etc). Apaga o registro do
    DynamoDB E a imagem do S3.

    Ordem importa: apaga o banco PRIMEIRO, o S3 DEPOIS. Se a exclusao do
    S3 falhar por algum motivo, o pior cenario e uma imagem orfa sobrando
    no bucket (inofensivo, limpavel depois) — nunca um registro no banco
    apontando pra uma imagem que nao existe mais (isso sim quebraria a
    classificacao depois, com erro NoSuchKey).
    """

    def __init__(self, repository: ICapturaRepository, storage: IStorageService):
        self._repository = repository
        self._storage = storage

    def execute(self, plantacao_id: str, timestamp: str, captura_id: str) -> bool:
        captura = self._repository.get(plantacao_id, timestamp, captura_id)
        if captura is None:
            return False

        self._repository.delete(plantacao_id, timestamp, captura_id)

        try:
            self._storage.delete_image(captura.s3_key)
        except Exception:
            # o registro ja foi removido do banco (o que importa pra
            # listagem/classificacao) — uma falha aqui so deixa uma
            # imagem orfa no S3, nao vale reverter nem falhar a
            # exclusao inteira por causa disso
            pass

        return True


class GerarThumbnailsUseCase:
    """
    Backfill: gera a miniatura pequena (ver preprocessamento_imagem.
    gerar_thumbnail) pras capturas ANTIGAS que nao tem thumbnail_key —
    ou seja, tudo que foi enviado antes dessa feature existir. Sem isso,
    essas capturas continuam usando a imagem original (varios MB) na
    listagem geral pra sempre, mesmo com a otimizacao ja no ar.

    Mesma logica de paginacao explicita do ReclassificarTodasUseCase —
    o conjunto "sem thumbnail" encolhe conforme processa, mas ainda assim
    usa paginas numeradas por simplicidade e consistencia com o resto da
    API.
    """

    def __init__(self, repository: ICapturaRepository, storage: IStorageService):
        self._repository = repository
        self._storage = storage

    def execute(
        self,
        plantacao_id: str = MOCK_PLANTACAO_ID,
        pagina: int = 1,
        tamanho_pagina: int = 20,
    ) -> dict:
        capturas, total = self._repository.list_by_plantacao(
            plantacao_id=plantacao_id, pagina=pagina, tamanho_pagina=tamanho_pagina
        )
        processadas, ja_tinham, erros = 0, 0, 0

        for captura in capturas:
            if captura.thumbnail_key:
                ja_tinham += 1
                continue

            try:
                image_bytes = self._storage.download_image(captura.s3_key)
                thumbnail_bytes = gerar_thumbnail(image_bytes)
                if thumbnail_bytes is None:
                    erros += 1
                    continue

                thumbnail_key = captura.s3_key.rsplit(".", 1)[0] + "_thumb.jpg"
                self._storage.upload_image(thumbnail_key, thumbnail_bytes)

                captura.thumbnail_key = thumbnail_key
                self._repository.update(captura)
                processadas += 1
            except Exception:
                erros += 1

        total_paginas = (total + tamanho_pagina - 1) // tamanho_pagina if total > 0 else 0
        return {
            "pagina": pagina,
            "tamanho_pagina": tamanho_pagina,
            "total": total,
            "total_paginas": total_paginas,
            "processadas": processadas,
            "ja_tinham": ja_tinham,
            "erros": erros,
        }
