# Style Guide Frontend

Este guia resume o padrão visual dos templates do Hubx.

## Tecnologias

- HTML5 semântico
- Tailwind CSS 3
- HTMX para interações dinâmicas

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

## Ícones

- Utilize ícones [Lucide](https://lucide.dev) embutidos como SVG diretamente nos templates ou componentes.
- Ícones meramente decorativos devem incluir `aria-hidden="true"`.
- Quando o ícone transmitir significado, forneça um `aria-label` no elemento ou um texto auxiliar escondido com `sr-only`.

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

Use a partial `components/nav_sidebar.html` para menus de navegação fixos e
responsivos. Ela traz links contextualizados pelo tipo de usuário e alterna
entre visual mobile e desktop automaticamente.

```django
{% include "components/nav_sidebar.html" with active="dashboard" %}
```

### Hero

Seções de destaque devem ocupar a área inicial da página com uma mensagem
principal e call to action opcional. Utilize `components/hero.html` para manter
consistência de espaçamento e tipografia.

```django
{% include "components/hero.html" with title="Bem-vindo" subtitle="Resumo do app" %}
```

### Cartões e botões

Agrupe informações em elementos com a classe utilitária `.card`. Ela define
bordas suaves, espaçamento e adapta automaticamente para o modo escuro.

```html
<div class="card bg-white dark:bg-gray-900">
  <h3 class="font-semibold">Título</h3>
  <p class="text-sm text-muted-foreground">Descrição ou conteúdo.</p>
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

Use as variantes `dark:` para garantir contraste adequado em ambos os temas e
sempre informe textos alternativos.

```html
<main class="p-4 bg-gray-50 text-gray-900 dark:bg-gray-900 dark:text-gray-100">
  <p>
    Este parágrafo mantém contraste suficiente e é anunciado por leitores de
    tela.
  </p>
  <a href="#conteudo" class="sr-only focus:not-sr-only">Pular para conteúdo</a>
</main>
```

Evite usar apenas cores para transmitir significado e garanta que botões
interativos tenham `aria-label` quando não houver texto visível.
