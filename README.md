# 🌾 BLICK Backend (API & Visão Computacional)

Bem-vindo ao repositório do backend do **BLICK**, um ecossistema inteligente para detecção precoce e monitoramento de pragas agrícolas.

## 🎯 Sobre este Repositório

Este repositório atua como o "cérebro" na nuvem do sistema BLICK. Ele é responsável por:
1. Receber e processar dados/imagens dos nós IoT (Edge) espalhados pela fazenda.
2. Orquestrar a execução do modelo de Inteligência Artificial para identificação de pragas.
3. Servir uma API RESTful para o painel de controle Web (Dashboard).

## 🚀 Quick Start

```bash
# 1. Clone e entre no projeto
git clone <repo-url> && cd blick-backend

# 2. Crie o .env a partir do exemplo
cp .env.example .env

# 3. Suba tudo com Docker
docker compose up --build

# 4. Acesse
#    API:    http://localhost:8000/api/v1
#    Docs:   http://localhost:8000/docs
#    Health: http://localhost:8000/health
```

## ⚙️ Arquitetura de Software

Para garantir escalabilidade e testabilidade, este projeto utiliza a **Arquitetura Hexagonal (Ports and Adapters)** em um **Monólito Modular**.
O núcleo do sistema (Regras de Negócio) é estritamente isolado de frameworks externos, bancos de dados e da própria IA, comunicando-se exclusivamente através de interfaces (Ports).

### Módulos de Negócio

| Módulo | Contexto |
|---|---|
| `users` | Produtores e técnicos agrícolas |
| `auth` | Autenticação e autorização (JWT) |
| `devices` | Nós IoT / Edge na fazenda |
| `detections` | Imagens + modelo de IA + pragas |
| `alerts` | Alertas de pragas detectadas |

### Tech Stack

- **Python 3.14** + **FastAPI**
- **SQLAlchemy 2** (async) + **PostgreSQL 16**
- **Docker** + **Docker Compose**
- **pytest** + **flake8**
