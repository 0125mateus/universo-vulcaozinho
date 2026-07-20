# Roadmap por etapas — Universo Vulcãozinho

Plano para consolidar o sistema na rede e, depois, preparar venda/licença.

---

## Visão geral

| Etapa | Foco | Prazo sugerido |
|-------|------|----------------|
| **1** | Produção confiável | 1–2 semanas |
| **2** | Piloto no Nacional Inn | 2–3 semanas |
| **3** | LGPD + termos (ponto/foto) | 1 semana |
| **4** | Expandir para os 4 hotéis | 2 semanas |
| **5** | White-label + 1º cliente externo | 1–2 meses |

---

## Etapa 1 — Produção confiável (em andamento)

Objetivo: sistema estável, seguro e recuperável.

### Checklist técnico

- [x] Hotéis da rede recriados a cada deploy (`seed_hoteis`)
- [x] Usuários demo desligados em produção (`SEED_DEMO_USERS=0`)
- [x] Seeds não resetam senha de usuários existentes
- [x] SMTP configurável por variáveis de ambiente
- [x] Script de backup PostgreSQL (`scripts/backup_postgres.sh`)
- [ ] **Domínio próprio** (ex.: `app.seudominio.com.br`)
- [ ] **HTTPS** (Cloudflare ou Certbot)
- [ ] **SMTP real** no Render/VPS (Gmail Workspace, SendGrid, etc.)
- [ ] **Backup agendado** (cron diário no VPS ou serviço do provedor)
- [ ] **Trocar senhas** dos usuários reais (não usar demo)
- [ ] **Redis** se escalar para mais de 1 worker (Docker já inclui)

### Variáveis novas (`.env` / Render)

```env
# Produção: não recriar logins demo
SEED_DEMO_USERS=0

# E-mail (recuperação de senha)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=seu@email.com
EMAIL_HOST_PASSWORD=senha-de-app
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=noreply@seudominio.com.br
```

### Backup manual

```bash
chmod +x scripts/backup_postgres.sh
./scripts/backup_postgres.sh
# Arquivos em backups/vulcaozinho_YYYYMMDD_HHMMSS.sql.gz
```

### Quando considerar Etapa 1 concluída

- Login com usuários reais (não demo)
- “Esqueci minha senha” envia e-mail
- Backup testado (restore em ambiente de teste)
- Domínio + HTTPS ativos

---

## Etapa 2 — Piloto Nacional Inn

Objetivo: um hotel usando tudo no dia a dia por 2–3 semanas.

### Módulos por ordem de adoção

1. **Semana 1:** Programação + telão + recepção (check-in básico)
2. **Semana 2:** Ponto (tablet + gestão RH) + dashboard
3. **Semana 3:** App hóspede + loja/PDV (se aplicável)

### Papéis envolvidos

| Papel | O que testa |
|-------|-------------|
| Gerente | Programação, publicar telão, dashboard |
| Recepção | Check-in, presença, hóspedes |
| Recreador | Ponto (PIN/facial) |
| RH / supervisor | Export Excel/PDF do ponto |

### Registro de feedback

Anote bugs, telas confusas e o que a equipe não usa — isso vira prioridade antes de expandir.

---

## Etapa 3 — LGPD e termos

Objetivo: base legal antes de escalar dados pessoais e biometria.

- [ ] Política de privacidade (hóspedes + recreadores)
- [ ] Termo de consentimento para foto no ponto
- [ ] Retenção de dados (quanto tempo guardar batidas/comprovantes)
- [ ] Procedimento de exclusão sob solicitação

---

## Etapa 4 — Rede completa (4 hotéis)

Replicar o que funcionou no piloto:

- Treinamento por hotel (meio dia cada)
- Usuários reais por perfil
- Telão configurado com API key própria
- WhatsApp setor pagamentos por hotel

---

## Etapa 5 — Venda / licença (opcional)

Só após Etapas 1–4 estáveis:

- White-label (logo/cores sem hardcode)
- Ambiente demo para prospects
- Contrato de licença + SLA de suporte
- Precificação (implantação + mensalidade)

---

## Próximo passo agora

**Concluir Etapa 1:** configurar domínio, SMTP e primeiro backup.

Quando estiver pronto, avise para iniciarmos a **Etapa 2** (roteiro detalhado do piloto Nacional Inn).
