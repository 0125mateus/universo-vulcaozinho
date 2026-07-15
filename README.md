# Universo Vulcãozinho

Sistema de recreação multi-hotel (Nacional Inn, Euro Suite, Dan Inn, Cassino Resort) — Poços de Caldas/MG.

## Stack

- Django 5.2 + SQLite
- Django REST Framework + drf-spectacular (Swagger)
- Templates HTML/CSS/JS (Fredoka, identidade Vulcãozinho)
- Assistente IA opcional (OpenAI)
- Jitsi Meet (salas de reunião)

## Início rápido (local)

```powershell
cd universo_vulcaozinho
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_all
python manage.py runserver
```

Acesse: http://127.0.0.1:8000/

## Docker

```powershell
docker compose up --build
```

Variáveis em `.env` (copie de `.env.example`). Com `RUN_SEED=1` (padrão), popula hotéis, programação e usuários demo na primeira subida.

## Usuários demo

Senha padrão: `vulcaozinho123`

| Usuário | Papel |
|---------|-------|
| `admin_rede` | Administrador |
| `diretor_rede` | Diretor |
| `gerente_nacional` | Gerente (Nacional Inn) |
| `recepcao_nacional` | Recepção |
| `loja_nacional` | Loja |
| `recreador_nacional` | Recreador |

Superuser admin: `python manage.py seed_superuser` → `admin` / `admin`

## Módulos

| Rota | Descrição |
|------|-----------|
| `/recepcao/` | Check-in, hóspedes, agenda, presença |
| `/dashboard/` | Dashboard operacional (polling 30s) |
| `/dashboard/executivo/` | KPIs gerenciais |
| `/telao/` | Tela TV (atividade + aniversariantes) |
| `/loja/gestao/` | CRUD produtos, estoque, QR |
| `/loja/pdv/` | Ponto de venda (carrinho + checkout) |
| `/loja/vendas/` | Histórico de vendas do mês |
| `/loja/financeiro/` | KPIs financeiros, margem, por forma de pagamento |
| `/passaporte/gestao/` | Carimbos e moedas |
| `/noites/gestao/` | Editar noites temáticas |
| `/api/v1/docs/` | Documentação Swagger |
| `/reuniao/` | Reunião diretoria (Jitsi) |
| `/ponto/` | Tablet da sala (nome + PIN) |
| `/ponto/app/` | App do recreador (bater ponto no celular) |
| `/ponto/gestao/` | Gestão de batidas e PIN dos recreadores |
| `/app/` | App do hóspede (PWA) |

## API Telão (pública, read-only)

```
GET /api/v1/telao/{hotel_id}/programacao-atual/?api_key=vulcaozinho-telao-dev
GET /api/v1/telao/{hotel_id}/aniversariantes-hoje/?api_key=...
GET /api/v1/telao/{hotel_id}/passeios-hoje/?api_key=...
```

Header alternativo: `X-API-Key: vulcaozinho-telao-dev`

## Tempo real (WebSocket)

Com `daphne` + Django Channels (`python manage.py runserver` já usa ASGI):

| Canal | URL | Auth |
|-------|-----|------|
| Dashboard | `ws://host/ws/dashboard/{hotel_id}/` | Sessão Django (login) |
| Telão | `ws://host/ws/telao/{hotel_id}/?api_key=...` | API key do telão |

Ao salvar hóspede, presença, inscrição, passaporte ou venda, dashboard e telão recebem `{"event":"refresh"}` e recarregam via API.

Fallback: polling a cada 2 min se o WebSocket cair.

### Channel layer (Redis)

| Ambiente | Backend | Config |
|----------|---------|--------|
| Dev local (`runserver`) | InMemory | padrão — sem `REDIS_URL` |
| Docker / produção | Redis | `REDIS_URL=redis://host:6379/0` |

O `docker-compose.yml` já inclui serviço **redis** e define `REDIS_URL` para o app. Necessário para **múltiplos workers** Daphne/Gunicorn compartilharem broadcasts WebSocket.

```powershell
# Docker (Redis automático)
docker compose up --build

# Escala horizontal (ex.: 3 instâncias web + 1 Redis)
docker compose up --scale web=3 -d
```

## Seeds individuais

```powershell
python manage.py seed_hoteis
python manage.py seed_categorias
python manage.py seed_noites_tematicas
python manage.py seed_programacao
python manage.py seed_loja
python manage.py seed_usuarios_demo
python manage.py seed_ponto
python manage.py seed_all   # todos acima
```

PIN demo dos recreadores (seed_ponto): `1234`

Fotos de recreadores/batidas ficam em `MEDIA_ROOT` (servidas em `/media/`). No Render free o disco é efêmero — após redeploy pode ser preciso reenviar a foto (ou use volume persistente).

## Deploy

Guia completo passo a passo: **[DEPLOY.md](DEPLOY.md)**

```powershell
copy .env.example .env
# edite .env (SECRET_KEY, POSTGRES_PASSWORD, etc.)
docker compose up --build -d
```

Acesso: **http://localhost** (nginx na porta 80)

```powershell
python manage.py test core
```

## Variáveis de ambiente

| Variável | Descrição |
|----------|-----------|
| `DJANGO_SECRET_KEY` | Chave secreta (obrigatória em produção) |
| `DJANGO_DEBUG` | `True` / `False` |
| `DJANGO_ALLOWED_HOSTS` | Hosts separados por vírgula |
| `TELAO_API_KEY` | Chave API do telão |
| `OPENAI_API_KEY` | Assistente IA (opcional) |
| `DEV_SKIP_LOGIN` | Login automático em dev |
| `DATABASE_PATH` | Caminho SQLite (Docker: `/data/db.sqlite3`) |
| `REDIS_URL` | Channel layer Redis (WebSocket multi-worker) |

## Estrutura

```
universo_vulcaozinho/
  config/          settings, urls, api_urls
  core/            models, views, API, seeds
  templates/       HTML
  static/          CSS, JS, imagens
  docker/          entrypoint
```

## Financeiro (loja)

- **PDV** (`/loja/pdv/`): carrinho com produtos do hotel, checkout com forma de pagamento
- **Margem**: cada venda grava `custo_unitario`, `custo_total` e `lucro_bruto` (custo do produto × quantidade)
- **Dashboard executivo**: receita, lucro, margem %, ticket médio via `kpis_financeiros_loja()`
- **API**: `GET/POST /api/v1/vendas/` (DRF)
- **Seed**: `seed_loja` define preço e custo (~50% margem bruta)

## Próximos passos (roadmap)

- HTTPS com certificado (Certbot ou Cloudflare)
- Backup automatizado PostgreSQL
