# Instruções para o Codex – ProjetoHubx

## 🧭 Contexto
Você atua no repositório `ProjetoHubx` (Hubx.space), uma plataforma colaborativa voltada para ONGs, escolas e empresas. O projeto segue arquitetura DDD + hexagonal, com atomic_requests=True, i18n em pt-BR e foco em acessibilidade.

## 📌 Stack obrigatória

- **Backend**: Python 3.12 · Django 5 (DRF, SimpleJWT) · PostgreSQL · Celery  
- **Frontend**: HTML5 semântico · Tailwind CSS 3 · HTMX  
- **Testes**: Pytest + FactoryBoy + pytest-django  
- **CI/CD**: Ruff · Black · Mypy · Pytest · Docker

## 📂 Organização

- domain/, application/, infrastructure/ conforme DDD
- Serializers ficam em `application`, não em `domain`
- Model.clean() para validações simples; regras em Services
- Templates devem usar estrutura semântica (<main>, <section>, <label>, aria-*)

## ✅ Qualidade e segurança

- Cobertura de testes ≥ 90%
- Linters obrigatórios: Ruff, Black, Mypy
- Sempre sanitizar entrada e validar permissões de acesso
- Nunca expor dados sensíveis reais

## 🧪 Commits

- Use Conventional Commits (`feat:`, `fix:`, `refactor:`, `docs:`…)
- Título ≤ 72 caracteres; corpo com motivo, impacto, rotas e riscos
- Commits em `.md`, `locale/` ou `docs/` **não disparam testes**

---

## ✅ Regra especial

## ✅ Regra especial

> **⚠️ O Codex deve sempre criar uma branch auxiliar e abrir uma Pull Request (PR) para o branch `principal`.**
> - Não deve comitar diretamente no `principal`.
> - Nomeie a branch de forma clara: `fix/nome`, `feat/modulo`, etc.
> - A PR deve conter:
>   - Título no padrão Conventional Commit (ex: `fix: corrigir acessibilidade nos templates`)
>   - Descrição com objetivo, impacto, requisitos e rota envolvida.
> - O merge será feito **manualmente no GitHub** após revisão e sucesso no CI.

---

## 📄 Fontes de Verdade

Sempre consulte os documentos da pasta `.requisitos`:

Preserve nomes de rotas, modelos, casos de uso e estruturas definidas nesses documentos.

