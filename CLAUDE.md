# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

---

# Projeto: Magister (Desafio Técnico DOT)

Regras obrigatórias derivadas do PRD `Cópia de PRD - Plataforma de tutores personalizados.docx`. Este arquivo é o **manual** da implementação; valem inclusive para o estilo dos comentários no código.

## Produto
Plataforma B2B onde administradores criam/configuram **tutores de IA** (persona, instruções, fontes) e integradores os embutem em sites via **iframe**. Nome do produto: **Magister**.

## Processo (do PRD)
- Código produzido **via agentes de codificação** (backend / frontend / segurança). Declarar isso explicitamente nos READMEs.
- Entrega em **dois repositórios Git distintos**: `backend/` e `frontend/`, com histórico de commits coerente com uso de agentes.

## Arquitetura (decisões travadas)
- Backend: **Python + FastAPI**. Frontend: **React + Vite + TypeScript**.
- Orquestração: **LangChain + LangGraph**, multi-agente **Supervisor + Knowledge + Persona + Guardrail** (escolha justificada pela orquestração multi-agente; registrar em "Decisões de arquitetura" do README).
- Conhecimento **agêntico por ferramentas** (`fetch_source`/`list_sources`/`summarize`). **Proibido** vector DB / embeddings / índice vetorial como núcleo de RAG.
- Persistência: **SQLite** (SQLModel/SQLAlchemy). Histórico por sessão: **janela de 40 mensagens + resumo rolante** (summary buffer).
- Transporte do chat: **HTTP + SSE (streaming)**.

## Segurança (ver `SECURITY.md`)
- Chaves/endpoints só por **variável de ambiente**; `.env.example` sem segredos reais.
- API admin **protegida por JWT**; widget autenticado por **embed token** público escopado ao tutor; embed **somente via iframe**; **nenhum segredo no front**.
- `fetch_source` com **SSRF guard**; system prompt do agente com **bloco anti prompt-injection**; **whitelist** de tools.
- Sem vazar stack trace nas respostas; **rate limit** na rota de chat; CORS/CSP coerentes com iframe.

## Custo e limites
- **Roteamento de LLM por custo**: Groq (free/barato) → OpenRouter (fallback), com **failover** e rotação de chaves; modelo por tarefa.
- **Limites de token**: `MAX_OUTPUT_TOKENS` por resposta e **orçamento por sessão** (`MAX_TOKENS_PER_SESSION`).

## Qualidade (NFRs do PRD)
- **Testes** em ponto crítico (tutor service e rota de chat) + auth, SSRF e llm router.
- **Linter/formatador** nos dois repos (ruff no backend; eslint+prettier no frontend).
- **Logs estruturados** para depurar falhas de ferramentas do agente e auditar custo.
- **README** em cada repo: como subir local, variáveis de ambiente, fluxo de embed ponta a ponta, diagrama, limitações e próximos passos.

## Fora de escopo (não implementar)
LTI/LMS; RAG vetorial; pagamentos/faturamento/multi-tenant forte; app mobile nativo.

## Idioma
Comentários e docs em **pt-BR**; identificadores de código em inglês (convenção). Comentar com parcimônia ("por quê", não "o quê").
