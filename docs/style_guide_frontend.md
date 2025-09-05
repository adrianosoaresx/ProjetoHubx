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
