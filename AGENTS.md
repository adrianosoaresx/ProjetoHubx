# AGENTS.md — Projeto Hubx (Django 5 + Tailwind 3 + HTMX)

| Agente           | Descrição breve | Entradas esperadas | Saídas esperadas |
|------------------|-----------------|--------------------|------------------|
| **refactor_bot** | Refatoração, migração para Tailwind/HTMX, split settings, pytest, CI. | Nome do app ou lista de apps; escopo (“front”, “backend”, “tests”); constraints. | Commits, patches ou instruções passo‑a‑passo. |
| **seed_bot**     | Geração de massa de dados (factory‑boy + django‑seed). | Tamanhos (users, events, posts…) e flags (`--flush`, `--images`). | Factories atualizadas, comando `seed_data` e/ou fixtures geradas. |
| **test_guru**    | Cria e corrige testes pytest‑django + hypothesis. | Caminho dos arquivos ou descrição do caso de uso. | Arquivos de teste prontos, dicas de mocks, cobertura alvo. |
| **ux_polish**    | Converte ou ajusta templates para Tailwind 3 + HTMX + Font Awesome 6. | Caminho template(s) ou tag fragment. | Código HTML ajustado + explicação das classes utilitárias aplicadas. |
| **docsmith**     | Mantém documentação (README, ADRs, CHANGELOG). | Arquivo alvo ou seção a atualizar; resumo das mudanças. | Markdown pronto e verificado por linter. |

---

## Convenções

1. **Idioma‑padrão: Português‑BR** (código pode estar em inglês).  
2. Sempre grave *snippets* em blocos fenced \``` (linguagem).  
3. Respeite formatação Black + Ruff.  
4. Para alterações múltiplas gere **patch Git** format‑patch style, exceto quando “explanation‑only” for solicitado.  
5. Para qualquer comando CLI, prefixe com `$` (shell).  
6. Nunca altere arquivos de migração manualmente — use `python manage.py makemigrations`.  

---

## Contexto de alto nível

* **Back‑end**: Django 5.2.2 + Django Channels  
* **Front‑end**: Tailwind CSS 3 (JIT), HTMX 1.9.x, Font Awesome 6  
* **Testes**: pytest‑django, factory‑boy, hypothesis, coverage ≥ 90 %  
* **CI**: GitHub Actions (`lint`, `test`, `build‑static`)  
* **Banco local**: SQLite; produção: Postgres + S3 (django‑storages)  

---

### Exemplo de invocação rápida

```text
<!-- Dentro do VS Code com a extensão Copilot Chat -->
User:
refactor_bot, por favor:
  app: forum
  escopo: "backend, tests"
  constraints: "manter API pública; cobertura mínima 95 %"
