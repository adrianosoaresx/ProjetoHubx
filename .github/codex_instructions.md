# Instruções para o Codex – ProjetoHubx

## 🧭 Contexto
Você atua no repositório `ProjetoHubx` (Hubx.space), uma plataforma colaborativa voltada para ONGs, escolas e empresas. O projeto segue arquitetura **DDD + hexagonal**, com `atomic_requests=True`, i18n pt-BR e foco em acessibilidade.

---

## ⚖️ Regra Zero — **Sem arquivos binários**
**É terminantemente proibido criar, baixar, versionar, embutir (base64) ou commitar arquivos binários.**  
Inclui (exemplos): imagens (`.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.ico`, `.bmp`, `.tiff`, `.avif`), fontes (`.ttf`, `.otf`, `.woff`, `.woff2`, `.eot`), vídeos (`.mp4`, `.webm`, `.mov`, `.avi`), áudios (`.mp3`, `.wav`, `.ogg`), documentos binários (`.pdf`, `.docx`, `.xlsx`, `.pptx`), compactados (`.zip`, `.rar`, `.7z`, `.tar`, `.gz`), executáveis/compilados (`.exe`, `.dll`, `.so`, `.dylib`, `.pyc`), bancos de dados (`.sqlite`, `.db`), modelos de IA (`.bin`, `.pth`, `.onnx`) e **qualquer blob base64**.

**Em vez disso, faça:**
- Use **placeholders textuais** (ex.: `src="__TODO_LOGO__"`), caminhos simulados e descrições em Markdown.
- Para ícones/ilustrações simples, é permitido **SVG textual inline pequeno** (sem base64, legível em diff).
- Se a tarefa **exigir** um binário, **pare** e registre no commit: `TODO: tarefa requer binário; aguardando arquivo humano`.

> **Proibições explícitas**  
> - Não embutir `data:*;base64,` em nenhum arquivo de texto.  
> - Não adicionar nem modificar binários já presentes; apenas **referenciá-los** por caminho, se necessário.

---

## 📌 Stack obrigatória
- **Backend**: Python 3.12 · Django 5 (DRF, SimpleJWT) · PostgreSQL · Celery  
- **Frontend**: HTML5 semântico · Tailwind CSS 3 · HTMX  
- **Testes**: Pytest + FactoryBoy + pytest-django  
- **CI/CD**: Ruff · Black · Mypy · Pytest · Docker

---

## 📂 Organização
- `domain/`, `application/`, `infrastructure/` conforme DDD  
- `Serializers` ficam em `application`, não em `domain`  
- `Model.clean()` para validações simples; regras em **Services**  
- Templates com estrutura semântica (`<main>`, `<section>`, `<label>`, atributos `aria-*`)

---

## ✅ Qualidade e segurança
- Cobertura de testes **≥ 90%**  
- Linters obrigatórios: **Ruff**, **Black**, **Mypy**  
- Sempre **sanitizar entradas** e **validar permissões**  
- Nunca expor dados sensíveis reais  
- A CI **deve falhar** se um arquivo binário for adicionado ao diff

---

## 🧪 Commits
- Use **Conventional Commits** (`feat:`, `fix:`, `refactor:`, `docs:`…)  
- Título ≤ **72** caracteres; corpo com **motivo, impacto, rotas e riscos**  
- Commits em `.md`, `locale/` ou `docs/` **não disparam testes**  
- **Nunca** inclua binários; se necessário, deixe `TODO` e referências textuais

**Exemplo de commit**

```
feat(user): adiciona serializer sem tocar binários

- Implementa UserCreateSerializer em application/users/serializers.py
- Adiciona testes unitários e atualiza docs
- TODO: logo institucional será fornecida por humano (arquivo não versionado)
```

---

## ✅ Regra especial de integração
> **⚠️ O Codex deve comitar diretamente no branch `principal` (`main`).**  
> - Não criar branch auxiliar  
> - Não abrir Pull Requests  
> - Aplicar alterações e enviar diretamente para `main`  
> - Deixar o commit integrado e pronto para rodar a CI

---

## 📄 Fontes de Verdade
Consulte **sempre** os documentos da pasta `.requisitos`.  
**Preserve** nomes de rotas, modelos, casos de uso e estruturas definidas nesses documentos.

---

## 📜 Checklist de execução (passo a passo)
1. Ler `.requisitos` e confirmar escopo.  
2. Verificar se a tarefa implica arquivos binários. Se **sim**, parar e registrar `TODO`.  
3. Produzir **apenas artefatos textuais** (código, configs, docs).  
4. Para assets, usar **placeholders** e caminhos como `/static/...`.  
5. Rodar **Ruff/Black/Mypy/Pytest**; garantir cobertura ≥ 90%.  
6. Atualizar documentação pertinente em `docs/`.  
7. Comitar em `main` com Conventional Commit e **sem binários/base64**.

---

## ✅ Política de arquivos permitidos
Arquivos **permitidos** (exemplos): `.py`, `.md`, `.html`, `.css`, `.js`, `.json`, `.yaml/.yml`, `.toml`, `.ini`, `.env.example`, `.sql`, `.sh`, `Dockerfile`, `.editorconfig`, `.pre-commit-config.yaml`, **`.svg` textual pequeno** (sem base64).

**Exemplo de placeholder em HTML**
```html
<img src="/static/img/logo.svg" alt="Logo do ProjetoHubx" width="144" height="48">
<!-- Arquivo real fornecido por humano; não versionar binários -->
```

**Exemplo de SVG textual mínimo permitido**
```html
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="16" height="16" role="img" aria-label="ícone">
  <circle cx="12" cy="12" r="10" stroke="currentColor" fill="none"/>
  <path d="M8 12h8" stroke="currentColor" fill="none"/>
</svg>
```
