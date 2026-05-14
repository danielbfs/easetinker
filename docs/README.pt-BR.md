# 🧠 EaseTinker

**Orquestrador visual de fine-tuning de LLMs via Tinker SDK (ThinkingMachines)**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](../LICENSE)
[![Docker](https://img.shields.io/badge/docker-ready-blue)](../docker-compose.yml)
[![Next.js](https://img.shields.io/badge/Next.js-16-black)](https://nextjs.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-blue)](https://www.typescriptlang.org)

> **[Read in English 🇺🇸](../README.md)**

EaseTinker é uma aplicação web que simplifica o processo de fine-tuning de modelos de linguagem usando a plataforma [Tinker](https://tinker-docs.thinkingmachines.ai). Sem escrever código Python — configure, lance e monitore jobs de treinamento diretamente pelo navegador.

---

## Índice

- [Visão Geral](#visão-geral)
- [Arquitetura](#arquitetura)
- [Funcionalidades](#funcionalidades)
- [Pré-requisitos](#pré-requisitos)
- [Deploy na Hostinger VPS](#deploy-na-hostinger-vps)
- [Atualizando para uma Nova Versão](#atualizando-para-uma-nova-versão)
- [Desenvolvimento Local](#desenvolvimento-local)
- [Variáveis de Ambiente](#variáveis-de-ambiente)
- [Contribuindo](#contribuindo)
- [Licença](#licença)

---

## Visão Geral

O Tinker SDK é poderoso para fine-tuning de LLMs, mas requer conhecimento de Python, gerenciamento manual de loops de treinamento e monitoramento por terminal.

O **EaseTinker** oferece uma interface web intuitiva para orquestrar tudo isso de forma visual. Basta fornecer a sua API Key do [Tinker Console](https://tinker-console.thinkingmachines.ai) e a aplicação cuida do resto — gerenciando datasets, hiperparâmetros e monitorando o loss de treinamento em tempo real.

---

## Arquitetura

O sistema funciona com dois serviços principais empacotados no Docker Compose:

1. **Next.js (App)** — Frontend, Autenticação, Interface e Gateway REST.
2. **Python Worker** — Comunica-se exclusivamente via rede interna com o Next.js e se conecta externamente ao Tinker Cloud via gRPC.

```text
┌──────────────────────────────────────────────────────┐
│                    VPS Hostinger                     │
│  ┌──────────┐    ┌─────────────────────────────────┐ │
│  │ Traefik  │───▶│     Docker Compose Network      │ │
│  │(Hostinger│    │  ┌───────────┐  ┌────────────┐  │ │
│  │ managed) │    │  │ Next.js   │  │  Python    │  │ │
│  └──────────┘    │  │ App :3000 │──│ Worker:8000│  │ │
│                  │  └─────┬─────┘  └─────┬──────┘  │ │
│                  │        │              │         │ │
│                  │  ┌─────┴─────┐  ┌─────┴──────┐  │ │
│                  │  │PostgreSQL │  │   Redis    │  │ │
│                  │  └───────────┘  └────────────┘  │ │
│                  └─────────────────────────────────┘ │
└──────────────────────────────────────────────────────┘
```

---

## Funcionalidades

- **Autenticação OAuth** — Login com Google ou GitHub
- **Gerenciamento de Projetos** — Crie e gerencie múltiplos projetos de fine-tuning
- **Upload de Datasets** — Envie arquivos ou vincule fontes de dados externas
- **Orquestração de Treinamento** — Configure hiperparâmetros (LoRA rank, learning rate, epochs, batch size) e lance jobs
- **Monitoramento em Tempo Real** — Acompanhe as métricas de loss ao vivo via Redis pub/sub
- **Criptografia de Credenciais** — API keys do Tinker criptografadas em repouso com AES-256-GCM
- **Self-hosted** — Roda inteiramente no seu próprio VPS com Docker Compose

---

## Pré-requisitos

### Para Produção (Hostinger VPS)

- VPS da Hostinger com Ubuntu 22.04+ e Docker instalado
- Domínio apontado para o IP do seu VPS (ex: `easetinker.seudominio.com`)
- Traefik rodando (padrão nas imagens Docker da Hostinger)
- Credenciais de OAuth do Google e/ou GitHub

### Para Desenvolvimento Local

- [Node.js 20+](https://nodejs.org) e [pnpm](https://pnpm.io)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Python 3.12+](https://www.python.org)

---

## Deploy na Hostinger VPS

O EaseTinker foi projetado para ser hospedado em uma **VPS da Hostinger com Docker e Traefik**. O Traefik detecta automaticamente os rótulos (labels) no `docker-compose.yml` e gerencia a emissão dos certificados SSL/HTTPS.

### Passo 1 — Pré-requisitos do Servidor

Conecte-se via SSH ao seu VPS e crie a rede pública do Traefik, caso ainda não exista:

```bash
docker network create traefik-public
```

Certifique-se de que o seu domínio já está apontando para o IP do VPS.

### Passo 2 — Clonar o Repositório

```bash
git clone https://github.com/danielbfs/easetinker.git /docker/easetinker
cd /docker/easetinker
```

### Passo 3 — Configurar Variáveis de Ambiente

```bash
cp .env.example .env
nano .env
```

Preencha os seguintes valores obrigatórios:

| Variável | Descrição | Como gerar |
|----------|-----------|------------|
| `APP_DOMAIN` | Seu domínio exato (sem `https://`) | ex: `easetinker.seudominio.com` |
| `NEXTAUTH_SECRET` | Chave de assinatura JWT | `openssl rand -base64 32` |
| `ENCRYPTION_KEY` | Chave AES-256-GCM para API keys | `openssl rand -hex 32` |
| `GOOGLE_CLIENT_ID` | Client ID do OAuth Google | [Google Cloud Console](https://console.cloud.google.com/) |
| `GOOGLE_CLIENT_SECRET` | Secret do OAuth Google | [Google Cloud Console](https://console.cloud.google.com/) |
| `GITHUB_CLIENT_ID` | Client ID do OAuth GitHub | [GitHub Developer Settings](https://github.com/settings/developers) |
| `GITHUB_CLIENT_SECRET` | Secret do OAuth GitHub | [GitHub Developer Settings](https://github.com/settings/developers) |
| `POSTGRES_PASSWORD` | Senha forte para o banco de dados | `openssl rand -base64 24` |
| `WORKER_SECRET` | Secret compartilhado para auth interna | `openssl rand -hex 32` |

> **URLs de Callback OAuth** — Ao criar os apps OAuth, defina a URL de callback como:
> `https://easetinker.seudominio.com/api/auth/callback/google` (e `/github`)

### Passo 4 — Subir os Containers

```bash
docker compose up -d --build
```

Isso cria 4 containers:
- `easetinker-postgres` — Banco de dados PostgreSQL 16
- `easetinker-redis` — Cache Redis 7 e fila de jobs
- `easetinker-worker` — Worker Python FastAPI (apenas interno)
- `easetinker-app` — App Next.js (exposto via Traefik com HTTPS)

### Passo 5 — Executar as Migrations do Banco

```bash
docker compose exec app pnpm exec prisma migrate deploy
```

> Use `pnpm exec` (e não `npx`), para que a versão do Prisma fixada em `package.json` seja usada. `npx prisma` baixa a última versão do registry silenciosamente, podendo ser incompatível.

### Passo 6 — Verificar e Acessar

```bash
# Verificar se todos os containers estão saudáveis
docker compose ps

# Inspecionar logs se algo não funcionar
docker compose logs -f app
docker compose logs -f worker
```

Acesse `https://easetinker.seudominio.com` no navegador. O Traefik configura o SSL automaticamente.

---

## Atualizando para uma Nova Versão

Escolha a seção que combina com a forma como você configurou o servidor originalmente.

### Opção A — Hostinger Docker Manager (via UI)

Se você instalou pelo Docker Manager da Hostinger (a UI fez o clone do repo pra você), o diretório `/docker/easetinker/` contém apenas `docker-compose.yml` e `.env` — **não** é um checkout git. Para atualizar:

1. Abra o Docker Manager da Hostinger para o projeto.
2. Clique em **Rebuild** (ou **Redeploy**). A Hostinger clona o `main` mais recente para um diretório temporário, rebuilda as imagens e reinicia os containers. Seu `.env` e volumes nomeados são preservados.
3. Após o rebuild terminar, aplique as migrations via SSH:
   ```bash
   docker compose -p easetinker exec app pnpm exec prisma migrate deploy
   ```

### Opção B — Manual via SSH (git clone em `/docker/easetinker/`)

Requer que você tenha originalmente seguido o [Passo 2](#passo-2--clonar-o-repositório) e que `/docker/easetinker/` seja um checkout git:

```bash
cd /docker/easetinker

# 1. Baixar as atualizações
git pull origin main

# 2. Reconstruir as imagens e reiniciar os containers (sem derrubar DB/Redis)
docker compose up -d --build

# 3. Aplicar novas migrations do banco de dados
docker compose exec app pnpm exec prisma migrate deploy

# 4. Confirmar que tudo está saudável
docker compose ps
```

> **Dica:** Assine as [GitHub Releases](https://github.com/danielbfs/easetinker/releases) para ser notificado quando novas versões forem publicadas.

---

## Desenvolvimento Local

Para trabalhar no EaseTinker localmente antes de enviar para produção:

**1. Subir serviços de apoio (DB + Redis):**
```bash
docker compose -f docker-compose.dev.yml up -d
```

**2. Instalar dependências Node:**
```bash
pnpm install
```

**3. Configurar o banco de dados:**
```bash
pnpm prisma generate
pnpm prisma migrate dev
```

**4. Configurar o Python Worker:**
```bash
cd worker
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

**5. Copiar e preencher as variáveis de ambiente:**
```bash
cp .env.example .env
# Edite .env com os valores locais (use URLs localhost)
```

**6. Iniciar os dois serviços em terminais separados:**
```bash
# Terminal 1 — Next.js
pnpm dev

# Terminal 2 — Python Worker
cd worker && uvicorn main:app --reload
```

A aplicação estará disponível em `http://localhost:3000`.

---

## Variáveis de Ambiente

Veja [`.env.example`](../.env.example) para a lista completa com descrições e comandos de geração.

| Variável | Obrigatório | Descrição |
|----------|-------------|-----------|
| `APP_DOMAIN` | Sim | Seu domínio (sem `https://`) |
| `NEXTAUTH_URL` | Sim | URL completa com `https://` |
| `NEXTAUTH_SECRET` | Sim | Chave de assinatura JWT |
| `GOOGLE_CLIENT_ID` | Sim* | OAuth Google (*ao menos um provedor) |
| `GOOGLE_CLIENT_SECRET` | Sim* | OAuth Google |
| `GITHUB_CLIENT_ID` | Sim* | OAuth GitHub |
| `GITHUB_CLIENT_SECRET` | Sim* | OAuth GitHub |
| `ENCRYPTION_KEY` | Sim | Chave hex AES-256-GCM (32 bytes) |
| `DATABASE_URL` | Sim | String de conexão PostgreSQL |
| `REDIS_URL` | Sim | String de conexão Redis |
| `WORKER_URL` | Sim | URL interna do worker |
| `WORKER_SECRET` | Sim | Secret compartilhado para auth do worker |
| `MAX_FILE_SIZE_MB` | Não | Tamanho máximo de upload (padrão: 50) |
| `UPLOAD_DIR` | Não | Diretório de uploads (padrão: /data/uploads) |

---

## Contribuindo

Contribuições são bem-vindas! Leia o [CONTRIBUTING.md](../CONTRIBUTING.md) antes de abrir um pull request.

- Encontrou um bug? [Abra uma issue](https://github.com/danielbfs/easetinker/issues/new?template=bug_report.yml)
- Tem uma ideia? [Solicite uma feature](https://github.com/danielbfs/easetinker/issues/new?template=feature_request.yml)
- Quer contribuir com código? Fork o repositório, crie uma branch e abra um PR.

---

## Licença

Este projeto está licenciado sob a [MIT License](../LICENSE).
