# Magister, backend

Backend do **Magister**, plataforma B2B onde administradores criam tutores de IA
(persona, instrucoes, fontes) e integradores os embutem em sites via `<iframe>`.

> Codigo produzido **via agentes de codificacao** (agentes backend, frontend e
> seguranca), conforme exigido pelo PRD do desafio. Este repositorio e o do backend.

## Arquitetura

```mermaid
flowchart TB
  subgraph Integrador["Site do integrador"]
    IF["iframe: /embed?token=…"]
  end
  subgraph FE["Frontend — React + Vite (repo separado)"]
    Admin["Painel Admin<br/>login JWT + CRUD tutores + snippet embed"]
    Widget["Widget de chat<br/>rota /embed"]
  end
  subgraph BE["Backend — FastAPI (este repo)"]
    AuthAPI["Auth<br/>POST /api/auth/login (JWT)"]
    AdminAPI["REST Admin<br/>protegida: JWT"]
    ChatAPI["Chat API<br/>SSE stream (embed token)"]
    subgraph AG["Orquestração multi-agente — LangGraph"]
      SUP["Supervisor / Router"]
      KN["Knowledge Agent"]
      PE["Persona Agent"]
      GD["Guardrail Agent"]
      CP["Compactação<br/>resumo rolante"]
    end
    Tools["Tools: fetch_source / list_sources / summarize<br/>(SSRF guard)"]
  end
  DB[("SQLite<br/>tutores + sessões + mensagens")]
  LLM["LLM Router (custo)<br/>Groq → OpenRouter + failover"]
  SRC["Fontes externas<br/>URLs HTTP do tutor"]
  IF --> Widget
  Admin --> AuthAPI
  Admin --> AdminAPI
  Widget --> ChatAPI
  ChatAPI --> SUP
  SUP --> GD
  SUP --> KN
  KN --> Tools
  Tools --> SRC
  SUP --> PE
  SUP --> CP
  KN --> LLM
  PE --> LLM
  GD --> LLM
  AdminAPI --> DB
  ChatAPI --> DB
```

## Stack

- **FastAPI** + **SQLModel/SQLAlchemy** sobre **SQLite**.
- Orquestracao **LangChain + LangGraph** (`StateGraph`), multi-agente.
- Conhecimento **agentico por tools** (`list_sources`, `fetch_source`, `summarize`).
  Sem vector DB / embeddings (restricao do PRD).
- Auth admin por **JWT**; widget por **embed token** publico escopado ao tutor.
- Chat por **SSE**; roteamento de LLM por custo (Groq -> OpenRouter) com failover.

## Decisoes de arquitetura

| Tema | Decisao | Porque |
|---|---|---|
| Orquestracao | LangGraph `StateGraph` multi-agente | Roteamento dinamico + especialistas (Supervisor/Knowledge/Persona/Guardrail), extensivel |
| Conhecimento | Tools que buscam/resumem URLs | PRD proibe vector DB/embeddings |
| Banco | SQLite | Zero-config para o MVP; migrar para Postgres e trivial |
| Auth | JWT (admin) + embed token (widget) | Expiracao + role no admin; embed token e publico e escopado, sem segredo no front |
| Transporte | HTTP + SSE | Simples e funciona bem em iframe |
| Memoria | Janela de 40 msgs + resumo rolante | Continuidade sem estourar contexto |
| LLM | Router por custo com failover | Free/barato primeiro (Groq), fallback (OpenRouter) |

### Topologia do grafo

```
guardrail_input -> supervisor -> [knowledge?] -> compaction -> persona -> [reitor?] -> guardrail_output
```

- **guardrail_input**: barra prompt-injection (regex) antes de gastar LLM.
- **supervisor**: decide se precisa buscar conhecimento (heuristica barata).
- **knowledge**: usa as tools (whitelist) sobre `tutor.sources`, com SSRF guard.
- **compaction**: resumo rolante quando a janela de 40 mensagens enche.
- **persona**: gera a resposta com `system_instructions` + contexto + historico.
- **reitor**: no de fallback. Responde a mesma pergunta com as instrucoes do tutor
  `is_fallback`, sem fontes. Terminal (nao escala de novo).
- **guardrail_output**: evita vazamento do bloco de seguranca e do marcador de escalada.

Estado compartilhado: `{tutor, user_message, history, rolling_summary,
compiled_context, needs_knowledge, response, tokens_used, safety, escalation_enabled,
fallback, session_id}`.

### Escalada ao Reitor

Quando um tutor tematico nao sabe responder (foge das fontes/escopo), a conversa
escala para o **Reitor** (tutor de fallback) dentro da mesma sessao, sem o visitante
trocar de iframe.

- Gatilho: a persona do tutor tematico e instruida a responder **apenas** com o
  marcador `[[ESCALAR]]` quando nao souber (ver `app/agents/prompts.py`).
- Apos a persona, uma aresta condicional (`route_after_persona`) verifica: resposta
  tem o marcador **e** `fallback_enabled=true` **e** existe um tutor `is_fallback`.
  Se sim, roteia para o no `reitor`; senao, segue para `guardrail_output`.
- O `guardrail_output` e o unico chokepoint: o marcador `[[ESCALAR]]` **nunca** vaza
  ao usuario. Sem Reitor disponivel, vira um "nao sei" honesto.
- Cada escalada emite log estruturado (`event="escalation"`, tutor de origem, tutor
  de destino, session id).
- `ponytail`: a escalada depende do LLM emitir exatamente `[[ESCALAR]]`. Aceitavel no
  MVP; upgrade path = saida estruturada `{answer, can_answer}`.

Controle por tutor: `is_fallback` marca o Reitor (definido no seed, nao editavel pela
API); `fallback_enabled` liga/desliga a escalada de um tutor tematico (editavel via
`PUT /api/tutors/{id}`).

## Como subir localmente

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate | Unix: source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env            # preencha os valores (veja abaixo)
# gere o hash da senha do admin:
python -c "import bcrypt;print(bcrypt.hashpw(b'suasenha',bcrypt.gensalt()).decode())"

uvicorn app.main:app --reload
```

API em `http://localhost:8000` (docs em `/docs`, health em `/health`).

### Variaveis de ambiente (`.env.example`)

| Variavel | Descricao |
|---|---|
| `JWT_SECRET` | Segredo HS256 do JWT admin (use 32+ bytes) |
| `JWT_EXPIRE_MINUTES` | Expiracao do token (padrao 60) |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD_HASH` | Credencial do admin unico (hash bcrypt) |
| `DATABASE_URL` | Conexao SQLite |
| `CORS_ALLOW_ORIGINS` | Origens do painel admin (separadas por virgula) |
| `HISTORY_WINDOW` | Tamanho da janela de mensagens (padrao 40) |
| `MAX_OUTPUT_TOKENS` | Teto de tokens por resposta |
| `MAX_TOKENS_PER_SESSION` | Orcamento de tokens por sessao |
| `CHAT_RATE_LIMIT_PER_MIN` | Rate limit da rota de chat por token/IP |
| `FETCH_TIMEOUT_SECONDS` / `FETCH_MAX_BYTES` | Limites do `fetch_source` (SSRF) |
| `LLM_PROVIDERS` | Lista JSON ordenada por custo (Groq -> OpenRouter) |
| `LLM_TASK_MODELS` | Mapa opcional tarefa->modelo (guardrail/summarize baratos) |

Chaves de LLM e `JWT_SECRET` vivem **so** no backend. O `.env.example` nao tem
valores reais; `.env` e ignorado pelo git.

## Rotas

| Metodo | Rota | Auth | Descricao |
|---|---|---|---|
| POST | `/api/auth/login` | - | Login admin -> JWT |
| POST | `/api/tutors` | JWT | Cria tutor |
| GET | `/api/tutors` | JWT | Lista tutores |
| GET | `/api/tutors/{id}` | JWT | Detalhe |
| PUT | `/api/tutors/{id}` | JWT | Atualiza |
| PATCH | `/api/tutors/{id}/status` | JWT | Ativa/desativa |
| GET | `/api/tutors/{id}/embed` | JWT | Snippet `<iframe>` + embed token |
| GET | `/api/embed/{embed_token}` | publica | Config publica do widget (titulo + saudacao) |
| POST | `/api/embed/{embed_token}/session` | publica | Clona a conversa-modelo numa sessao nova (resume) |
| POST | `/api/chat` | embed token | Chat do widget (SSE) |

O payload de tutor (create/update/list/detail) inclui `is_fallback` (bool, so leitura)
e `fallback_enabled` (bool, editavel por create/update). `is_fallback` e definido no
seed e nao e editavel pela API.

### Fluxo de embed ponta a ponta

1. Admin faz `POST /api/auth/login` e recebe o JWT.
2. Cria um tutor (`POST /api/tutors`); o servidor gera o `embed_token`.
3. `GET /api/tutors/{id}/embed` retorna o snippet
   `<iframe src=".../embed?token=<embed_token>">`.
4. O integrador cola o snippet no site. O widget (frontend) chama
   `POST /api/chat {embed_token, message}`; o backend valida tutor ativo +
   origem, aplica rate limit e orcamento de tokens, roda o grafo e faz stream SSE.

### Conversa-modelo continuavel (resume)

Para o visitante abrir o widget e continuar de onde a demo parou, o backend semeia
uma sessao-modelo (template) no startup (via `seed_demo_session`) vinculada ao embed
token do tutor "Suporte de Matriculas". Ela ja contem uma pergunta fora de escopo
respondida pelo Reitor (escalada).

- **Resume:** `POST /api/embed/{embed_token}/session` (cria estado, por isso POST).
  O cliente **nunca** envia `session_id` (evita IDOR). Retorna
  `{"session_id": str | null, "messages": [{"role", "content"}, ...]}`.
- **Clone por visitante:** o template `demo-<embed_token>` e **somente leitura**. A cada
  resume, o servidor **minta um uuid novo**, clona as mensagens do template para essa
  sessao e a devolve. Assim cada visitante tem historico e orcamento de tokens proprios,
  sem vazamento entre visitantes. O widget usa o `session_id` retornado no `POST /api/chat`
  para continuar **com contexto**.
- **Prefixo reservado `demo-`:** o `POST /api/chat` rejeita (HTTP 400) qualquer
  `session_id` que comece com `demo-`; ninguem consegue escrever/inflar o template mesmo
  adivinhando o id.
- **Rate limit:** o resume usa o mesmo limitador do chat (por IP), pois tambem cria estado.
- Sem sessao-modelo para o token, `session_id` vem `null` e `messages` vazio.

### Regenerar o banco/seed

O banco SQLite e apenas dado de demonstracao. Os campos `is_fallback`/`fallback_enabled`
e a sessao-modelo sao criados pelo seed no startup (idempotente). Para regenerar do zero
apos mudar o schema ou o seed:

```bash
rm magister.db           # remova o banco local
uvicorn app.main:app --reload   # o startup recria o schema e roda o seed
```

O `create_all` nao altera tabelas existentes; por isso, ao adicionar colunas ao modelo,
apague `magister.db` para que o schema seja recriado.

## Seguranca

Ver `SECURITY.md`. Resumo do que este backend implementa:

- Segredos so por env; `.gitignore` + `.gitleaks.toml` + hook `pre-commit`.
- CRUD admin exige JWT (assinatura + expiracao + role); widget usa so o embed token.
- Rate limit em `/api/chat` (token/IP) + orcamento de tokens por sessao.
- Handler global de erro sem vazar stack trace; logs estruturados (JSON).
- Bloco anti prompt-injection no system prompt; whitelist de tools.
- SSRF guard no `fetch_source` (so http/https; bloqueia IPs privados/loopback/
  link-local, incluindo `169.254.169.254`; timeout e limite de tamanho).

## Testes e lint

```bash
ruff check .
pytest
```

## Limitacoes do MVP

- Rate limit em memoria (1 instancia). Producao: Redis/WAF (ver `SECURITY.md`).
- SSE entrega a resposta ja gerada em blocos; streaming token a token direto do
  modelo fica como proximo passo (o transporte SSE ja esta pronto).
- Admin unico via env (sem tabela de usuarios / refresh token).
- CSP `frame-ancestors` da pagina do widget e responsabilidade do frontend.

## Proximos passos

PostgreSQL; refresh token / OAuth / multiplos admins; multi-tenant; observabilidade
(LangSmith/OpenTelemetry); cache de fontes e de respostas; WebSocket como alternativa
ao SSE; persistencia de estado/checkpoints no LangGraph; streaming token a token;
escalada por saida estruturada (`{answer, can_answer}`) em vez do marcador textual;
TTL/limpeza das sessoes de demo clonadas (cada resume cria uma sessao nova, as linhas
acumulam sem expurgo).
