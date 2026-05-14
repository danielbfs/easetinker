# 🧠 EaseTinker

**Visual orchestrator for fine-tuning LLMs via the Tinker SDK (ThinkingMachines)**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-ready-blue)](docker-compose.yml)
[![Next.js](https://img.shields.io/badge/Next.js-16-black)](https://nextjs.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-blue)](https://www.typescriptlang.org)

> **[Leia em Português 🇧🇷](docs/README.pt-BR.md)**

EaseTinker is a web application that simplifies the LLM fine-tuning process using the [Tinker](https://tinker-docs.thinkingmachines.ai) platform. No Python knowledge required — configure, launch, and monitor training jobs directly from your browser.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Deploy on Hostinger VPS](#deploy-on-hostinger-vps)
- [Updating to a New Version](#updating-to-a-new-version)
- [Local Development](#local-development)
- [Environment Variables](#environment-variables)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

The Tinker SDK is powerful for fine-tuning LLMs, but it requires Python knowledge, manual training loop management, and terminal-based monitoring.

**EaseTinker** provides an intuitive web interface to orchestrate everything visually. Simply provide your [Tinker Console](https://tinker-console.thinkingmachines.ai) API key, and the application handles the rest — managing datasets, hyperparameters, and monitoring training loss in real time.

---

## Architecture

The system runs two main services packaged with Docker Compose:

1. **Next.js (App)** — Frontend, Authentication, UI, and REST Gateway.
2. **Python Worker** — Communicates exclusively via internal network with Next.js and connects externally to Tinker Cloud via gRPC.

```text
┌──────────────────────────────────────────────────────┐
│                    Hostinger VPS                     │
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

## Features

- **OAuth Authentication** — Sign in with Google or GitHub
- **Project Management** — Create and manage multiple fine-tuning projects
- **Dataset Upload** — Upload files or link external data sources
- **Training Orchestration** — Configure hyperparameters (LoRA rank, learning rate, epochs, batch size) and launch jobs
- **Real-time Monitoring** — Watch training loss metrics live via Redis pub/sub
- **Credential Encryption** — Tinker API keys encrypted at rest with AES-256-GCM
- **Self-hosted** — Runs entirely on your own VPS with Docker Compose

---

## Prerequisites

### For Production (Hostinger VPS)

- Hostinger VPS with Ubuntu 22.04+ and Docker pre-installed
- A domain pointing to your VPS IP (e.g. `easetinker.yourdomain.com`)
- Traefik reverse proxy running (default on Hostinger Docker images)
- Google and/or GitHub OAuth app credentials

### For Local Development

- [Node.js 20+](https://nodejs.org) and [pnpm](https://pnpm.io)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Python 3.12+](https://www.python.org)

---

## Deploy on Hostinger VPS

EaseTinker is designed to be hosted on a **Hostinger VPS with Docker and Traefik**. Traefik automatically detects the labels in `docker-compose.yml` and manages SSL/HTTPS certificate issuance.

### Step 1 — Server Prerequisites

Connect to your VPS via SSH and create the Traefik public network if it does not exist yet:

```bash
docker network create traefik-public
```

Make sure your domain is already pointing to your VPS IP address.

### Step 2 — Clone the Repository

```bash
git clone https://github.com/danielbfs/easetinker.git /docker/easetinker
cd /docker/easetinker
```

### Step 3 — Configure Environment Variables

```bash
cp .env.example .env
nano .env
```

Fill in the following required values:

| Variable | Description | How to generate |
|----------|-------------|-----------------|
| `APP_DOMAIN` | Your exact domain (no `https://`) | e.g. `easetinker.yourdomain.com` |
| `NEXTAUTH_SECRET` | JWT signing secret | `openssl rand -base64 32` |
| `ENCRYPTION_KEY` | AES-256-GCM key for API keys | `openssl rand -hex 32` |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID | [Google Cloud Console](https://console.cloud.google.com/) |
| `GOOGLE_CLIENT_SECRET` | Google OAuth secret | [Google Cloud Console](https://console.cloud.google.com/) |
| `GITHUB_CLIENT_ID` | GitHub OAuth client ID | [GitHub Developer Settings](https://github.com/settings/developers) |
| `GITHUB_CLIENT_SECRET` | GitHub OAuth secret | [GitHub Developer Settings](https://github.com/settings/developers) |
| `POSTGRES_PASSWORD` | Strong database password | `openssl rand -base64 24` |
| `WORKER_SECRET` | Shared secret for internal auth | `openssl rand -hex 32` |

> **OAuth Callback URLs** — When creating OAuth apps, set the callback URL to:
> `https://easetinker.yourdomain.com/api/auth/callback/google` (and `/github`)

### Step 4 — Start the Containers

```bash
docker compose up -d --build
```

This creates 4 containers:
- `easetinker-postgres` — PostgreSQL 16 database
- `easetinker-redis` — Redis 7 cache and job queue
- `easetinker-worker` — Python FastAPI worker (internal only)
- `easetinker-app` — Next.js app (exposed via Traefik with HTTPS)

### Step 5 — Run Database Migrations

```bash
docker compose exec app pnpm exec prisma migrate deploy
```

> Use `pnpm exec` (not `npx`), so the Prisma version pinned in `package.json` is used. `npx prisma` will silently fetch the latest version from the registry, which can be incompatible.

### Step 6 — Verify and Access

```bash
# Check all containers are healthy
docker compose ps

# Inspect logs if something is wrong
docker compose logs -f app
docker compose logs -f worker
```

Open `https://easetinker.yourdomain.com` in your browser. Traefik configures SSL automatically.

---

## Updating to a New Version

Pick the section that matches how you set up the server in the first place.

### Option A — Hostinger Docker Manager (UI-driven)

If you installed via Hostinger's Docker Manager (the UI cloned the repo for you), the project directory `/docker/easetinker/` only contains `docker-compose.yml` and `.env` — **not** a git checkout. To update:

1. Open the Hostinger Docker Manager UI for the project.
2. Click **Rebuild** (or **Redeploy**). Hostinger clones the latest `main` into a temporary directory, rebuilds the images, and restarts the containers. Your `.env` and named volumes are preserved.
3. After the rebuild finishes, apply migrations via SSH:
   ```bash
   docker compose -p easetinker exec app pnpm exec prisma migrate deploy
   ```

### Option B — Manual via SSH (git clone in `/docker/easetinker/`)

This requires that you originally followed [Step 2](#step-2--clone-the-repository) and `/docker/easetinker/` is a git checkout:

```bash
cd /docker/easetinker

# 1. Pull the latest code
git pull origin main

# 2. Rebuild images and restart containers (zero-downtime for DB/Redis)
docker compose up -d --build

# 3. Apply any new database migrations
docker compose exec app pnpm exec prisma migrate deploy

# 4. Confirm everything is healthy
docker compose ps
```

> **Tip:** Subscribe to [GitHub Releases](https://github.com/danielbfs/easetinker/releases) to get notified when new versions are published.

---

## Local Development

To work on EaseTinker locally before pushing to production:

**1. Start support services (DB + Redis only):**
```bash
docker compose -f docker-compose.dev.yml up -d
```

**2. Install Node dependencies:**
```bash
pnpm install
```

**3. Set up the database:**
```bash
pnpm prisma generate
pnpm prisma migrate dev
```

**4. Set up the Python Worker:**
```bash
cd worker
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

**5. Copy and fill in environment variables:**
```bash
cp .env.example .env
# Edit .env with your local values (use localhost URLs)
```

**6. Start both services in separate terminals:**
```bash
# Terminal 1 — Next.js
pnpm dev

# Terminal 2 — Python Worker
cd worker && uvicorn main:app --reload
```

The app will be available at `http://localhost:3000`.

---

## Environment Variables

See [`.env.example`](.env.example) for the full list with descriptions and generation commands.

| Variable | Required | Description |
|----------|----------|-------------|
| `APP_DOMAIN` | Yes | Your domain (no `https://`) |
| `NEXTAUTH_URL` | Yes | Full URL including `https://` |
| `NEXTAUTH_SECRET` | Yes | JWT signing secret |
| `GOOGLE_CLIENT_ID` | Yes* | Google OAuth (*at least one provider required) |
| `GOOGLE_CLIENT_SECRET` | Yes* | Google OAuth |
| `GITHUB_CLIENT_ID` | Yes* | GitHub OAuth |
| `GITHUB_CLIENT_SECRET` | Yes* | GitHub OAuth |
| `ENCRYPTION_KEY` | Yes | AES-256-GCM hex key (32 bytes) |
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `REDIS_URL` | Yes | Redis connection string |
| `WORKER_URL` | Yes | Internal worker URL |
| `WORKER_SECRET` | Yes | Shared secret for worker auth |
| `MAX_FILE_SIZE_MB` | No | Max upload size (default: 50) |
| `UPLOAD_DIR` | No | Upload directory (default: /data/uploads) |

---

## Contributing

We welcome contributions! Please read [CONTRIBUTING.md](CONTRIBUTING.md) before submitting a pull request.

- Found a bug? [Open an issue](https://github.com/danielbfs/easetinker/issues/new?template=bug_report.yml)
- Have an idea? [Request a feature](https://github.com/danielbfs/easetinker/issues/new?template=feature_request.yml)
- Want to contribute code? Fork the repo, create a branch, and open a PR.

---

## License

This project is licensed under the [MIT License](LICENSE).
