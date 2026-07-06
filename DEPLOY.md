# Deploy — Universo Vulcãozinho

Guia passo a passo para subir em produção (Docker) e publicar no GitHub.

---

## Visão geral da stack

```
Internet → nginx (:80) → Daphne/ASGI (:8000)
                ↓              ↓
           /static/      PostgreSQL + Redis
```

| Serviço    | Função                          |
|-----------|----------------------------------|
| **nginx** | Proxy, arquivos estáticos, WebSocket |
| **web**   | Django + Channels (Daphne)       |
| **db**    | PostgreSQL 16                    |
| **redis** | Channel layer (WebSocket)        |

---

## Passo 1 — Pré-requisitos na sua máquina

### 1.1 Instalar Git

Se `git` não for reconhecido no terminal:

```powershell
winget install Git.Git
```

Feche e reabra o terminal. Teste:

```powershell
git --version
```

### 1.2 Instalar Docker Desktop

- Baixe: https://www.docker.com/products/docker-desktop/
- Inicie o Docker Desktop e aguarde ficar **Running**

Teste:

```powershell
docker --version
docker compose version
```

---

## Passo 2 — Configurar variáveis de ambiente

Na pasta do projeto:

```powershell
cd "c:\Users\plane\OneDrive\Documentos\projetos cursor\Automação confirme\universo_vulcaozinho"
copy .env.example .env
```

Edite o arquivo `.env` e **altere pelo menos**:

| Variável | Exemplo | Observação |
|----------|---------|------------|
| `DJANGO_SECRET_KEY` | string longa aleatória | Gere com: `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `POSTGRES_PASSWORD` | senha forte | Usada pelo Postgres e `DATABASE_URL` |
| `TELAO_API_KEY` | chave única | Telões usam essa chave na API |
| `DJANGO_ALLOWED_HOSTS` | `meudominio.com,localhost` | Domínio ou IP do servidor |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://meudominio.com` | Com `http://` ou `https://` |
| `RUN_SEED` | `1` na 1ª vez, depois `0` | Evita recriar dados a cada restart |

> **Nunca commite o arquivo `.env`** — ele já está no `.gitignore`.

---

## Passo 3 — Subir a aplicação (produção)

```powershell
docker compose up --build -d
```

Aguarde os containers ficarem saudáveis:

```powershell
docker compose ps
```

Acesse no navegador:

- **http://localhost** (porta 80 via nginx)
- Telão: `http://localhost/telao/`
- Admin: `http://localhost/admin/`

### Comandos úteis

```powershell
# Ver logs
docker compose logs -f web

# Parar tudo
docker compose down

# Parar e apagar volumes (CUIDADO: apaga o banco)
docker compose down -v
```

### Stack de desenvolvimento (SQLite, sem nginx)

Para testar Docker sem Postgres:

```powershell
docker compose -f docker-compose.dev.yml up --build
```

Acesse: http://localhost:8000

---

## Passo 4 — Publicar no GitHub

### 4.1 Criar repositório no GitHub

1. Acesse https://github.com/new
2. Nome sugerido: `universo-vulcaozinho`
3. **Não** marque “Add README” (já temos um)
4. Clique em **Create repository**
5. Copie a URL, ex.: `https://github.com/SEU_USUARIO/universo-vulcaozinho.git`

### 4.2 Inicializar Git e primeiro commit

Na pasta do projeto:

```powershell
cd "c:\Users\plane\OneDrive\Documentos\projetos cursor\Automação confirme\universo_vulcaozinho"

git init
git add .
git status
git commit -m "Deploy produção: PostgreSQL, nginx, Redis e módulo financeiro"
```

### 4.3 Conectar ao GitHub e enviar

Substitua pela sua URL:

```powershell
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/universo-vulcaozinho.git
git push -u origin main
```

Se pedir login, use **Personal Access Token** do GitHub (Settings → Developer settings → Tokens).

---

## Passo 5 — Deploy em um servidor (VPS)

No servidor Linux (Ubuntu/Debian):

```bash
# 1. Instalar Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# relogue na sessão

# 2. Clonar o repositório
git clone https://github.com/SEU_USUARIO/universo-vulcaozinho.git
cd universo-vulcaozinho

# 3. Configurar .env (mesmas variáveis do Passo 2)
cp .env.example .env
nano .env

# 4. Subir
docker compose up --build -d
```

### HTTPS (recomendado)

Opções:

- **Cloudflare** na frente do servidor (mais simples)
- **Certbot + nginx** no host (documentação separada)
- Ao usar HTTPS, defina no `.env`:
  - `DJANGO_SECURE_COOKIES=True`
  - `DJANGO_CSRF_TRUSTED_ORIGINS=https://seudominio.com`

---

## Passo 6 — Checklist pós-deploy

- [ ] Login funciona (`seed_usuarios_demo` — senha `vulcaozinho123`)
- [ ] Telão carrega programação e clima
- [ ] WebSocket: badge **Ao vivo** no dashboard
- [ ] PDV registra venda com margem
- [ ] `RUN_SEED=0` no `.env` após primeira subida
- [ ] Backup do volume `postgres_data` agendado

---

## Usuários demo (após seed)

| Usuário | Papel |
|---------|-------|
| `admin` | Administrador |
| `recepcao_nacional` | Recepção |
| `loja_nacional` | Loja |
| `gerente_nacional` | Gerente |

Senha padrão: **`vulcaozinho123`**

---

## Solução de problemas

| Problema | Solução |
|----------|---------|
| `git` não encontrado | Instale com `winget install Git.Git` e reinicie o terminal |
| Porta 80 em uso | Altere `HTTP_PORT=8080` no `.env` |
| Erro de migrate no Postgres | `docker compose logs db` — aguarde healthcheck |
| Estáticos sem CSS | `docker compose exec web python manage.py collectstatic --noinput` |
| WebSocket não conecta | Confirme `REDIS_URL` e proxy `/ws/` no nginx |
