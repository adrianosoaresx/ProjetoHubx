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

> **⚠️ O Codex deve comitar diretamente no branch `principal`.**
> - Não crie branch auxiliar
> - Não abra Pull Requests
> - Aplique as alterações e envie diretamente para o repositório principal (`main`)
> - Deixe o commit já integrado no histórico, pronto para rodar CI

---

## 📄 Fontes de Verdade

Sempre consulte os documentos da pasta `.requisitos`:

Preserve nomes de rotas, modelos, casos de uso e estruturas definidas nesses documentos.

