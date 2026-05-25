# CLAUDE.md — Blick API

> Lido automaticamente pelo Claude CLI a cada sessão.
> Instituto Mauá de Tecnologia · TCC 2026 · Grupo CMD04

---

## O Projeto

**Blick** é um sistema de monitoramento fitossanitário agrícola composto por:
- **Blick Klar** — robô agrícola (carrinho) com câmera e Jetson Nano para captura georreferenciada
- **Blick Cloud** — API + IA na nuvem para análise de saúde das plantas

O carrinho percorre a plantação, detecta plantas via modelo local no Jetson Nano, captura imagens e envia em lote para a API na nuvem. A IA na nuvem classifica a saúde da planta (saudável / doença / praga) e gera recomendações de ação para o produtor rural.

---

## Stack

| Tecnologia | Uso |
|---|---|
| Python 3.12 | Linguagem |
| FastAPI | Framework web |
| Pydantic v2 | Validação |
| boto3 | SDK AWS |
| python-jose[cryptography] | Validação JWT Cognito |
| httpx | HTTP client |
| uvicorn | Servidor ASGI |
| Docker | Container local |

---

## Arquitetura Hexagonal

```
src/
├── domain/                   ← Núcleo — sem dependências externas
│   ├── entities.py           ← Captura, Coordenadas, JetsonNanoInfo, StatusEntry
│   ├── ports.py              ← ICapturaRepository, IStorageService, IAuthService
│   └── exceptions.py        ← BlickAuthError
├── application/
│   ├── use_cases.py          ← SubmitCapturaUseCase
│   └── dtos.py               ← CapturaInputDTO, CapturaOutputDTO
├── infrastructure/           ← Implementações concretas AWS
│   ├── dynamo_repository.py  ← DynamoCapturaRepository (boto3)
│   ├── s3_storage.py         ← S3StorageService (boto3)
│   └── cognito_auth.py       ← CognitoAuthService — valida JWT via JWKS offline
└── interfaces/
    ├── routes.py             ← POST /capturas (protegido por JWT)
    ├── schemas.py            ← CapturaRequest (sem cliente_id), CapturaResponse
    └── dependencies.py       ← Injeção de dependência + get_current_cliente_id
```

---

## Infraestrutura AWS

| Recurso | Nome | Região |
|---|---|---|
| DynamoDB | `blick-table` | `us-east-1` |
| S3 | `blick-capturas-tcc-640168426886-us-east-1` | `us-east-1` |
| Cognito User Pool | `blick-user-pool` | `us-east-1` |
| Cognito Pool ID | `us-east-1_Xqao8BA2H` | — |
| Cognito Client ID (dashboard) | `24bc2a4d4ok7sp2hrsir5a09pt` | — |
| JWKS URL | `https://cognito-idp.us-east-1.amazonaws.com/us-east-1_Xqao8BA2H/.well-known/jwks.json` | — |

### Tags padrão (todos os recursos)
```
environment = GRADUACAO
project     = TCC
group       = CMD04
creator     = LUCASCRAPINO_22006672
owner       = BOSSINI
```

---

## DynamoDB — Single Table Design

**Tabela:** `blick-table`

### Entidade CAPTURA
- **PK:** `PLANT#<plantacao_id>`
- **SK:** `CAPTURA#<timestamp>#<captura_id>`
- **GSI1PK/SK:** `CART#<carrinho_id>` / `CAPTURA#<timestamp>` → busca por carrinho
- **GSI2PK/SK:** `STATUS#<status>` / `<timestamp>` → busca por status
- **Atributos:** `captura_id`, `cliente_id`, `plantacao_id`, `carrinho_id`, `timestamp`, `sequencia_no_percurso`, `coordenadas`, `s3_bucket`, `s3_key`, `jetson_nano`, `ia_nuvem`, `status`, `status_history[]`, `erro_detalhes`, `alerta_emitido`, `alerta_emitido_em`, `ttl`

### Entidade PLANTACAO
- **PK:** `PLANT#<plantacao_id>`
- **SK:** `METADATA`
- **Atributos:** `cliente_id` (GUID do Cognito/sub), `nome`, `cultura`, `area_hectares`, `localizacao`, `criado_em`

### GSIs
| Índice | PK | SK | Uso |
|---|---|---|---|
| `GSI1-carrinho` | `GSI1PK` | `GSI1SK` | Buscar por carrinho |
| `GSI2-status` | `GSI2PK` | `GSI2SK` | Buscar por status |

### Ciclo de vida do status
```
PENDENTE → ENVIADO → PROCESSADO → REVISADO
                  ↘ ERRO
```

---

## S3 — Estrutura de Pastas

```
blick-capturas-tcc-640168426886-us-east-1/
  └── <cliente_id>/
        └── <ano>/
              └── <mes>/
                    └── <dia>/
                              └── <captura_id>.jpg
```

---

## Endpoint Atual

### `POST /capturas` (protegido por JWT)

**Request:**
```json
{
  "dia_mes_ano": "12/05/2026",
  "latitude": -23.6470,
  "longitude": -46.5151,
  "imagem_base64": "<base64 JPEG>"
}
```
> `cliente_id` vem do token JWT (campo `sub`) — não enviado no body

**Response 201:**
```json
{
  "sucesso": true,
  "captura_id": "20260512143000-a1b2c3d4",
  "s3_key": "<cliente_id>/2026/05/12/20260512143000-a1b2c3d4.jpg"
}
```

---

## Autenticação Cognito

### Validação JWT (offline)
- JWKS buscado na inicialização e cacheado com `lru_cache`
- Validação local com `python-jose` — sem chamada AWS a cada request
- `cliente_id` = campo `sub` do token JWT
- Lança `BlickAuthError` se token inválido ou expirado

### Fluxo Jetson Nano
1. Boot → `initiate_auth(USER_PASSWORD_AUTH)` → recebe `AccessToken` + `RefreshToken`
2. Cada `POST /capturas` → `Authorization: Bearer <AccessToken>`
3. Token expirou → `initiate_auth(REFRESH_TOKEN_AUTH)` → novo `AccessToken`

### Fluxo Dashboard (React)
1. AWS Amplify Auth → telas de login/signup
2. `fetchAuthSession()` → `AccessToken`
3. Cada chamada API → `Authorization: Bearer <AccessToken>`

---

## Variáveis de Ambiente

```env
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_SESSION_TOKEN=...
S3_BUCKET_NAME=blick-capturas-tcc-640168426886-us-east-1
DYNAMODB_TABLE_NAME=blick-table
COGNITO_USER_POOL_ID=us-east-1_Xqao8BA2H
COGNITO_CLIENT_ID=24bc2a4d4ok7sp2hrsir5a09pt
COGNITO_REGION=us-east-1
```

> ⚠️ Credenciais AWS da Mauá são temporárias — renovar em https://myapps.microsoft.com/

---

## Rodando Localmente

```bash
docker compose up --build   # subir
docker compose down         # parar
```

- **API:** http://localhost:8000
- **Swagger:** http://localhost:8000/docs

---

## Próximos Passos

- [ ] Implementar autenticação JWT com Cognito (6 arquivos — ver seção abaixo)
- [ ] Criar App Client do Jetson Nano no Cognito
- [ ] Criar usuário de teste no Cognito
- [ ] Deploy na AWS Lambda + API Gateway
- [ ] Configurar IAM Role para a Lambda
- [ ] IA na nuvem para análise de saúde da planta
- [ ] Dashboard frontend (React + AWS Amplify)
- [ ] CI/CD com GitHub Actions

---

## Implementação Pendente — Autenticação JWT (Cognito)

### Arquivos a modificar/criar

| Arquivo | Ação |
|---|---|
| `domain/ports.py` | Adicionar `IAuthService.verify_token()` |
| `domain/exceptions.py` | Criar — `BlickAuthError` |
| `infrastructure/cognito_auth.py` | Criar — valida JWT via JWKS offline |
| `interfaces/dependencies.py` | Adicionar `get_current_cliente_id` via `Depends` |
| `interfaces/routes.py` | Proteger rotas, `cliente_id` vem do token |
| `interfaces/schemas.py` | Remover `cliente_id` do `CapturaRequest` |
| `requirements.txt` | Adicionar `python-jose[cryptography]`, `httpx` |

### Prompt para o Claude CLI implementar

```
Leia o CLAUDE.md para entender o projeto. Implemente a autenticação JWT com AWS Cognito nos seguintes arquivos:

1. domain/ports.py — adicionar interface IAuthService com método verify_token(token: str) -> str que retorna o cliente_id (sub)

2. domain/exceptions.py — criar arquivo com BlickAuthError(Exception)

3. infrastructure/cognito_auth.py — criar CognitoAuthService que implementa IAuthService:
   - Busca JWKS em https://cognito-idp.us-east-1.amazonaws.com/us-east-1_Xqao8BA2H/.well-known/jwks.json
   - Cacheia as chaves públicas com lru_cache na inicialização
   - Valida JWT offline com python-jose sem chamar AWS a cada request
   - Extrai e retorna o campo sub do token como cliente_id
   - Lança BlickAuthError se token inválido ou expirado

4. interfaces/dependencies.py — adicionar:
   - get_auth_service() com lru_cache retornando CognitoAuthService
   - oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
   - get_current_cliente_id(token = Depends(oauth2_scheme)) que chama verify_token e retorna cliente_id

5. interfaces/routes.py — atualizar POST /capturas:
   - Adicionar cliente_id: str = Depends(get_current_cliente_id)
   - Remover cliente_id do body (CapturaInputDTO recebe do Depends)

6. interfaces/schemas.py — remover cliente_id do CapturaRequest

7. requirements.txt — adicionar:
   python-jose[cryptography]==3.3.0
   httpx==0.27.0

Manter padrão hexagonal. Gerar todos os arquivos completos.
```

### Teste rápido após implementação

```bash
# Obter token
TOKEN=$(aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id 24bc2a4d4ok7sp2hrsir5a09pt \
  --auth-parameters USERNAME=teste@blick.com,PASSWORD=BlickTest2026! \
  --region us-east-1 \
  --query 'AuthenticationResult.AccessToken' --output text)

# Testar rota protegida
curl -X POST http://localhost:8000/capturas \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"dia_mes_ano":"12/05/2026","latitude":-23.6470,"longitude":-46.5151,"imagem_base64":"..."}'
```

---

## Decisões de Arquitetura

| Decisão | Motivo |
|---|---|
| Single Table Design | Access patterns definidos, mais barato e eficiente |
| S3 para imagens | Mais barato e escalável que guardar no banco |
| On-demand no DynamoDB | Sem necessidade de estimar capacidade para TCC |
| Arquitetura Hexagonal | Isolamento do domínio, facilita troca de infra futura |
| GUID como `cliente_id` | Evita expor CPF/CNPJ na tabela operacional |
| `lru_cache` nas dependências | Evita criar conexão boto3 nova a cada request |
| JWKS cacheado | Validação JWT offline — sem chamada AWS a cada request |
| Credenciais temporárias | Limitação SSO Mauá — em produção usar IAM Role na Lambda |