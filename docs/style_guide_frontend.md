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

## Ícones

- Utilize ícones [Lucide](https://lucide.dev) embutidos como SVG diretamente nos templates ou componentes.
- Ícones meramente decorativos devem incluir `aria-hidden="true"`.
- Quando o ícone transmitir significado, forneça um `aria-label` no elemento ou um texto auxiliar escondido com `sr-only`.

## Paleta de cores oficial

A identidade do Hubx usa um gradiente de marca e tokens de cores para garantir
consistência entre componentes.

- **Gradiente:** utilize `bg-gradient-to-r from-primary-600 to-primary-400` para
  barras ou destaques de marca.
- **Primárias:** `text-primary-600`, `bg-primary-500` e `border-primary-400`.
- **Neutras:** `bg-background`, `text-foreground`, `border-border` e
  `text-muted-foreground`.
- **Sucesso/Erro:** `text-success-600`, `bg-success-100`, `bg-destructive` e
  `text-destructive-foreground`.

```html
<div class="h-8 bg-gradient-to-r from-primary-600 to-primary-400"></div>
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

Botões com o atributo `data-theme-option` alternam o tema global (`claro`,
`escuro` ou `automatico`) atualizando o `aria-pressed` automaticamente:

```html
<div class="flex gap-2" role="group" aria-label="Tema">
  <button type="button" data-theme-option="claro" class="btn-secondary">Claro</button>
  <button type="button" data-theme-option="escuro" class="btn-secondary">Escuro</button>
  <button type="button" data-theme-option="automatico" class="btn-secondary">Automático</button>
</div>
```

Evite usar apenas cores para transmitir significado e garanta que botões
interativos tenham `aria-label` quando não houver texto visível.

### Componentes em modo claro e escuro

Os componentes devem apresentar boa aparência em ambos os temas:

```html
<div class="p-4 rounded bg-white text-gray-900 dark:bg-gray-800 dark:text-gray-100">
  <p class="mb-2">Conteúdo do cartão</p>
  <button class="btn btn-primary">Ação</button>
</div>
```
