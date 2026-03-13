# 🏗️ Arquitetura Hexagonal — BLICK Backend

Este projeto utiliza **Arquitetura Hexagonal (Ports & Adapters)** para manter as regras de negócio do sistema de detecção de pragas isoladas de frameworks e infraestrutura.

```
src/
├── domain/           ← Núcleo do sistema (regras puras)
├── application/      ← Orquestração dos casos de uso
├── infrastructure/   ← Implementações concretas
└── interfaces/       ← Entrada: API REST (FastAPI)
```

---

## `domain/`

> O coração do sistema. **Não depende de nenhuma outra camada.**

| Arquivo futuro | Descrição |
|---|---|
| `entities.py` | Entidades de domínio (`User`, `Device`, `Detection`, `Alert`) |
| `value_objects.py` | Objetos de valor (`Email`, `GeoLocation`, `Confidence`) |
| `exceptions.py` | Exceções de negócio (`PestNotFound`, `DeviceOffline`) |
| `ports.py` | Interfaces (ABC) dos repositórios e serviços externos |
| `events.py` | Eventos de domínio (`PestDetectedEvent`, `AlertCreatedEvent`) |

---

## `application/`

> Orquestra a lógica de domínio. Contém os **casos de uso** da aplicação.

| Arquivo futuro | Descrição |
|---|---|
| `use_cases.py` | Casos de uso (`SubmitImage`, `CreateAlert`, `RegisterDevice`) |
| `services.py` | Serviços de aplicação que coordenam múltiplas operações |
| `dtos.py` | Data Transfer Objects para entrada/saída dos casos de uso |

---

## `infrastructure/`

> Implementações concretas que conversam com o mundo externo.

| Arquivo futuro | Descrição |
|---|---|
| `database.py` | Configuração do SQLAlchemy / conexão com PostgreSQL |
| `models.py` | Modelos ORM (tabelas `users`, `devices`, `detections`, `alerts`) |
| `repositories.py` | Implementações concretas dos ports definidos no `domain/` |
| `ai_client.py` | Client para invocar o modelo de IA de detecção de pragas |
| `storage.py` | Upload/download de imagens (S3, local, etc.) |

---

## `interfaces/`

> Camada de entrada — expõe o sistema via API REST.

| Arquivo futuro | Descrição |
|---|---|
| `routes.py` | Rotas FastAPI (`/devices`, `/detections`, `/alerts`) |
| `schemas.py` | Schemas Pydantic de request/response |
| `dependencies.py` | Injeção de dependência via `Depends()` |

---

## Fluxo de uma Detecção de Praga

```
[IoT Device] → POST /detections (interfaces/)
                    → SubmitImage (application/)
                        → DetectionPort (domain/)
                            → AiClient + Repository (infrastructure/)
                                → PestDetectedEvent (domain/)
                                    → CreateAlert (application/)
```
