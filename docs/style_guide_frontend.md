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

### Sidebar

Use a partial `nav_sidebar.html` para menus de navegação fixos e responsivos.
Ela traz links contextualizados pelo tipo de usuário e alterna entre visual
mobile e desktop automaticamente.

```django
{% include "components/nav_sidebar.html" %}
```

### Hero

Seções de destaque devem ocupar a área inicial da página com uma mensagem
principal e call to action opcional. Utilize a partial `hero.html` para manter
consistência de espaçamento e tipografia.

```django
{% include "components/hero.html" with title="Bem-vindo" subtitle="Resumo do app" %}
```

### Cartões

Agrupe informações em cartões usando contêineres com borda suave e sombra
leve.

```html
<div class="p-4 bg-white rounded-lg shadow">
  <h3 class="font-semibold">Título</h3>
  <p class="text-sm text-gray-600">Descrição ou conteúdo.</p>
</div>
```

### Formulários

Formulários devem ser compostos por `label`, `input` ou componentes do
Tailwind, sempre com `aria-label` ou `aria-describedby` quando necessário.
Botões primários usam `btn btn-primary` e ações secundárias `btn btn-secondary`.

```html
<form hx-post="/salvar" class="space-y-4">
  <label class="block">
    <span class="text-sm">Nome</span>
    <input type="text" name="nome" class="mt-1 block w-full" />
  </label>
  <button type="submit" class="btn btn-primary">Enviar</button>
</form>
```
