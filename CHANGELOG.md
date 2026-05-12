# Blick API — Registro de Implementação

## Sessão 2026-05-12

### O que foi implementado

Endpoint `POST /capturas` completo, seguindo arquitetura hexagonal (Ports & Adapters), para receber capturas de imagem enviadas pelo Jetson Nano.

---

### Arquivos criados

| Camada | Arquivo | O que faz |
|---|---|---|
| **domain** | `src/domain/entities.py` | Entidade `Captura` com dataclasses (`Coordenadas`, `JetsonNanoInfo`, `StatusEntry`). Gera PK/SK/GSIs como properties e serializa para DynamoDB via `to_dynamo_item()` |
| **domain** | `src/domain/ports.py` | Interfaces abstratas `IStorageService` (upload de imagem) e `ICapturaRepository` (persistência) |
| **application** | `src/application/dtos.py` | `CapturaInputDTO` (entrada do use case) e `CapturaOutputDTO` (resposta) |
| **application** | `src/application/use_cases.py` | `SubmitCapturaUseCase` — decodifica base64, gera `captura_id` (timestamp + uuid curto), monta S3 key, faz upload, persiste no DynamoDB |
| **infrastructure** | `src/infrastructure/s3_storage.py` | `S3StorageService` — implementa `IStorageService` usando `boto3.put_object` |
| **infrastructure** | `src/infrastructure/dynamo_repository.py` | `DynamoCapturaRepository` — implementa `ICapturaRepository` usando `boto3.resource.Table.put_item` |
| **interfaces** | `src/interfaces/schemas.py` | Pydantic schemas `CapturaRequest` (com validação de regex para `dia_mes_ano`) e `CapturaResponse` |
| **interfaces** | `src/interfaces/routes.py` | Rota `POST /capturas` (status 201) com injeção de dependência via `Depends` |
| **interfaces** | `src/interfaces/dependencies.py` | Factory das dependências com `lru_cache` para singletons de S3 e DynamoDB |
| **root** | `src/main.py` | Entrypoint FastAPI (`app`) |
| **root** | `requirements.txt` | `fastapi`, `uvicorn`, `pydantic`, `boto3` |

---

### Schema DynamoDB (single-table design)

```
PK:     PLANT#<plantacao_id>
SK:     CAPTURA#<timestamp>#<captura_id>
GSI1PK: CART#<carrinho_id>
GSI1SK: CAPTURA#<timestamp>
GSI2PK: STATUS#PENDENTE
GSI2SK: <timestamp>
```

Campos: `entity_type`, `captura_id`, `cliente_id`, `timestamp`, `coordenadas`, `s3_bucket`, `s3_key`, `jetson_nano`, `ia_nuvem` (null), `status`, `status_history`, `erro_detalhes` (null), `alerta_emitido` (false), `ttl` (null).

---

### S3 key pattern

```
<cliente_id>/<ano>/<mes>/<dia>/<captura_id>.jpg
```

---

### Variáveis de ambiente

| Variável | Default |
|---|---|
| `AWS_REGION` | `us-east-1` |
| `S3_BUCKET_NAME` | `blick-capturas-tcc` |
| `DYNAMODB_TABLE_NAME` | `blick-table` |

---

### Correções aplicadas

1. **Parsing de `dia_mes_ano`** — trocado `split("/")` manual por `datetime.strptime(dto.dia_mes_ano, "%d/%m/%Y")`. Se o formato vier errado, agora lança `ValueError` em vez de gerar um S3 key silenciosamente incorreto.

2. **Nome default da tabela DynamoDB** — corrigido de `blick-capturas` para `blick-table` em `dependencies.py`.

---

### Pendências / próximos passos

- [ ] Autenticação com Cognito
- [ ] Substituir mocks de `plantacao_id` e `carrinho_id` por dados reais
- [ ] Testes unitários e de integração
- [ ] Pipeline de processamento IA nuvem (campo `ia_nuvem` hoje é null)
- [ ] Sistema de alertas (`alerta_emitido`)
- [ ] Configurar TTL no DynamoDB
