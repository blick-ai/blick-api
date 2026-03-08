# 🌾 BLICK Backend (API & Visão Computacional)

Bem-vindo ao repositório do backend do **BLICK**, um ecossistema inteligente para detecção precoce e monitoramento de pragas agrícolas.

## 🎯 Sobre este Repositório

Este repositório atua como o "cérebro" na nuvem do sistema BLICK. Ele é responsável por:
1. Receber e processar dados/imagens dos nós IoT (Edge) espalhados pela fazenda.
2. Orquestrar a execução do modelo de Inteligência Artificial para identificação de pragas.
3. Servir uma API RESTful para o painel de controle Web (Dashboard).

## ⚙️ Arquitetura de Software

Para garantir escalabilidade e testabilidade, este projeto utiliza a **Arquitetura Hexagonal (Ports and Adapters)**. 
O núcleo do sistema (Regras de Negócio) é estritamente isolado de frameworks externos, bancos de dados e da própria IA, comunicando-se exclusivamente através de interfaces (Ports).
