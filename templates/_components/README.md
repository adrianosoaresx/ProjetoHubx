# Componentes de templates

Os arquivos deste diretório servem como partes reutilizáveis em páginas do Hubx.
Cada componente deve manter semântica HTML, classes do Tailwind e suporte a
tradução.

## nav_sidebar.html
Sidebar fixa e colapsável posicionada à esquerda da página. Os itens exibidos
são controlados por permissões do usuário e cada entrada usa ícones SVG da
biblioteca Lucide, sem dependência do Font Awesome.

Todo texto visível e atributos de acessibilidade (`aria-label`, `aria-current`,
`aria-expanded`, `aria-controls`) devem utilizar `{% trans %}` ou
`{% blocktrans %}` para suporte a i18n e conformidade com padrões ARIA.

```django
{% include "_partials/sidebar.html" %}
```

## hero.html
Seção de destaque para cabeçalhos de páginas. Aceita variáveis `title`,
`subtitle` e `cta` para botões de ação. Os valores devem ser textos já
traduzidos ou envolvidos por `{% trans %}` dentro da partial.

```django
{% include "_components/hero.html" with title=_("Título") %}
```

O gradiente utiliza as variáveis CSS `--hero-from` e `--hero-to`, com valores
padronizados de `var(--color-primary-500)` e `var(--color-primary-700)`.
Essas cores podem ser sobrescritas ao incluir o componente passando o atributo
`style`:

```django
{% include "_components/hero.html" with title=_("Título") style="--hero-from: var(--color-accent-500); --hero-to: var(--color-accent-700);" %}
```

## Convenções de i18n

- Todo texto visível deve estar dentro de `{% trans %}` ou `{% blocktrans %}`.
- Atributos como `aria-label`, `alt` e placeholders precisam ser traduzíveis.
- Componentes adicionais (cards, formulários, etc.) devem seguir as mesmas
  regras ao serem criados.
