# Style Guide Frontend

Este guia resume o padrão visual dos templates do Hubx.

## Tecnologias

- HTML5 semântico
- Tailwind CSS 3
- HTMX para interações dinâmicas
- CSS base em `app/static/css/hubx.css`

Evite JavaScript customizado sempre que possível. Utilize `hx-get` e `hx-post` para enviar e atualizar partes da página.

## Estrutura básica

```html
<!DOCTYPE html>
<html lang="pt-br">
  <head>
    <meta charset="UTF-8" />
    <title>Título</title>
  </head>
  <body>
    <header>...</header>
    <main>
      <!-- conteúdo -->
    </main>
    <footer>...</footer>
  </body>
</html>
```

Aplique utilitários Tailwind diretamente nas tags para garantir consistência entre páginas.


## Convenção de componentes de template por app

Para componentes reutilizáveis específicos de um módulo, adote como padrão:

- `templates/<nome_app>/componentes/`

### Nomenclatura

- Pastas em `snake_case`, organizadas por finalidade (ex.: `cards/`, `filtros/`, `cabecalhos/`).
- Arquivos em `snake_case.html` com nome semântico (ex.: `card_evento_resumo.html`, `filtro_periodo.html`).
- Evite nomes temporários (`tmp`, `novo`, `copia`) em arquivos versionados.

### Exemplos de include

```django
{% include "eventos/componentes/cabecalho_lista.html" with titulo=_("Eventos") %}
{% include "organizacoes/componentes/card_organizacao.html" with organizacao=item %}
```

Quando o componente for compartilhado por vários apps, prefira os diretórios globais já existentes (`templates/_components/` e `templates/_partials/`).

## Ícones

- Utilize ícones [Lucide](https://lucide.dev) embutidos como SVG diretamente nos templates ou componentes.
- Ícones meramente decorativos devem incluir `aria-hidden="true"`.
- Quando o ícone transmitir significado, forneça um `aria-label` no elemento ou um texto auxiliar escondido com `sr-only`.

### Badges e labels traduzidos

- Contadores dinâmicos (ex.: sino de notificações) devem expor `aria-live="polite"` para avisar leitores de tela sem interromper o foco. Use `sr-only` para repetir o rótulo traduzido ao lado do valor visual.
- Gere todos os textos de contagem com `{% blocktrans %}` para manter pluralização correta. Ao atualizar o número via JavaScript, recicle os templates de label armazenados em `data-*` (como `data-notification-label-one/other`) para que o `aria-label` e o texto invisível permaneçam localizados.
- Mesmo quando houver WebSocket, mantenha atributos HTMX (`hx-get`, `hx-trigger`) como *fallback* de atualização do badge. Isso garante sincronização de contadores em ambientes sem WebSocket ou com JS bloqueado.

## Paleta de cores oficial

A identidade do Hubx usa um gradiente de marca e tokens de cores para garantir
consistência entre componentes.

- **Gradiente:** utilize `bg-gradient-to-r from-primary-600 to-primary-800` para
  barras ou destaques de marca.
- **Primárias:** `text-[var(--primary)]`, `bg-[var(--primary)]` e
  `border-[var(--primary)]`.
- **Neutras:** `bg-background`, `text-foreground`, `border-border` e
  `text-[var(--text-secondary)]`.
- **Sucesso/Erro:** `text-success-600`, `bg-success-100`, `bg-destructive` e
  `text-destructive-foreground`.

```html
<div class="h-8 bg-gradient-to-r from-primary-600 to-primary-800"></div>
```

## Estrutura de layout

### Header com seletor de tema

O cabeçalho abriga o logotipo, links primários e um botão para alternância de
tema. Ele deve ser fixo no topo e responder ao modo claro/escuro.

```html
<header class="flex items-center justify-between border-b p-4">
  <h1 class="text-lg font-bold">Hubx</h1>
  <button
    id="theme-toggle"
    class="btn"
    hx-post="/tema/alternar"
    aria-label="Alternar tema"
    aria-pressed="false"
  >
    <span class="sr-only">Alternar tema</span>
    🌗
  </button>
</header>
```

Quando o usuário alterna o tema, adicione a classe `dark` no elemento `html`
ou `body` para ativar as variantes `dark:` do Tailwind.

### Sidebar

Use a partial `_partials/sidebar.html` para menus de navegação fixos e
responsivos. Ela traz links contextualizados pelo tipo de usuário e alterna
entre visual mobile e desktop automaticamente.

```django
{% include "_partials/sidebar.html" with active="feed" %}
```

### Hero

Seções de destaque devem ocupar a área inicial da página com uma mensagem
principal e call to action opcional. Utilize `_components/hero.html` para manter
consistência de espaçamento e tipografia. Páginas de listagem devem iniciar com
este componente, destacando o título e ações relevantes.

```django
{% include "_components/hero.html" with title="Bem-vindo" subtitle="Resumo do app" %}
```

### Cartões e botões

Agrupe informações em elementos com a classe utilitária `.card`. Ela define
bordas suaves, espaçamento e adapta automaticamente para o modo escuro.

```html
<div class="card bg-[var(--bg-secondary)] dark:bg-gray-900">
  <h3 class="font-semibold">Título</h3>
  <p class="text-sm text-[var(--text-secondary)]">Descrição ou conteúdo.</p>
  <button class="btn btn-primary mt-2">Ação</button>
</div>
```

### Formulários com labels flutuantes

Formulários devem ser compostos por `label` e `input` ou componentes do
Tailwind. Utilize rótulos flutuantes para economizar espaço e garantir
acessibilidade.

```html
<form hx-post="/salvar" class="space-y-6">
  <div class="relative">
    <input
      id="nome"
      type="text"
      name="nome"
      placeholder=" "
      class="floating peer"
      required
    />
    <label for="nome" class="label-float">Nome</label>
  </div>
  <button type="submit" class="btn btn-primary">Enviar</button>
</form>
```

### Modo claro/escuro e acessibilidade

As variantes `dark:` do Tailwind aplicam estilos quando o elemento `html` ou
`body` possui a classe `dark`. Combine classes para definir versões dos dois
temas:

```html
<main class="p-4 bg-gray-50 text-gray-900 dark:bg-gray-900 dark:text-gray-100">
  <p>
    Este parágrafo mantém contraste suficiente e é anunciado por leitores de
    tela.
  </p>
  <a href="#conteudo" class="sr-only focus:not-sr-only">Pular para conteúdo</a>
</main>
```

Botões com o atributo `data-theme-option` alternam o tema global (`claro` ou
`escuro`) atualizando o `aria-pressed` automaticamente. Utilize ícones para
representar cada opção:

```html
<div class="flex gap-2" role="group" aria-label="Tema">
  <button type="button" data-theme-option="claro" class="btn btn-secondary">
    <svg aria-hidden="true" xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2m0 16v2m10-10h-2M4 12H2m15.364-7.364l-1.414 1.414M6.05 17.95l-1.414 1.414m12.728 0l-1.414-1.414M6.05 6.05 4.636 4.636" />
    </svg>
    <span class="sr-only">Claro</span>
  </button>
  <button type="button" data-theme-option="escuro" class="btn btn-secondary">
    <svg aria-hidden="true" xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
      <path d="M17.293 13.293A8 8 0 1 1 6.707 2.707a8.003 8.003 0 0 0 10.586 10.586z" />
    </svg>
    <span class="sr-only">Escuro</span>
  </button>
</div>
```

Evite usar apenas cores para transmitir significado e garanta que botões
interativos tenham `aria-label` quando não houver texto visível.

### Componentes em modo claro e escuro

Os componentes devem apresentar boa aparência em ambos os temas:

```html
<div class="p-4 rounded bg-[var(--bg-secondary)] text-gray-900 dark:bg-gray-800 dark:text-gray-100">
  <p class="mb-2">Conteúdo do cartão</p>
  <button class="btn btn-primary">Ação</button>
</div>
```
