# Componentes de templates

Os arquivos deste diretório servem como partes reutilizáveis em páginas do Hubx.
Cada componente deve manter semântica HTML, classes do Tailwind e suporte a
tradução.

## nav_sidebar.html
Barra de navegação responsiva que alterna entre menu superior e sidebar.
Todos os links utilizam `{% trans %}` para i18n e incluem atributos de
acessibilidade como `aria-label` e `aria-current`.

```django
{% include "components/nav_sidebar.html" %}
```

## hero.html
Seção de destaque para cabeçalhos de páginas. Aceita variáveis `title`,
`subtitle` e `cta` para botões de ação. Os valores devem ser textos já
traduzidos ou envolvidos por `{% trans %}` dentro da partial.

```django
{% include "components/hero.html" with title=_("Título") %}
```

## Convenções de i18n

- Todo texto visível deve estar dentro de `{% trans %}` ou `{% blocktrans %}`.
- Atributos como `aria-label`, `alt` e placeholders precisam ser traduzíveis.
- Componentes adicionais (cards, formulários, etc.) devem seguir as mesmas
  regras ao serem criados.
