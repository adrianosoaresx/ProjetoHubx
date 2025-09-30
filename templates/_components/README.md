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

## back_button.html

Botão/link de retorno que prioriza o histórico do navegador. Quando houver
referência válida (`document.referrer` ou cabeçalhos do HTMX), o componente
executa `history.back()`. Caso contrário, utiliza o `href` informado ou um
`fallback_href` explícito antes de seguir com o link padrão.

### Parâmetros

| Nome | Tipo / Valores | Padrão | Descrição |
| --- | --- | --- | --- |
| `href` | URL | `'#'` | Destino preferencial quando não há histórico aproveitável. |
| `fallback_href` | URL | — | Link alternativo quando `history.back()` falha; também define `data-fallback-href`. |
| `variant` | `'button'`, `'link'`, `'compact'` | `'button'` | Seleciona presets para botão, link ou modo compacto. |
| `classes` | string | — | Classes adicionais mescladas ao preset da variante. |
| `label` | texto | `gettext('Voltar')` | Texto visível do botão. |
| `aria_label` | texto | mesmo que `label` | Alternativa para leitores de tela. |
| `icon` | nome Lucide | `'arrow-left'` | Ícone exibido antes do texto. Usa a tag `{% lucide %}`. |
| `show_icon` | booleano | `True` | Define se o ícone padrão/personalizado deve ser renderizado. |
| `prevent_history` | booleano | `None` | Quando `True`, ignora a lógica de histórico e emite `data-prevent-history="true"`. |
| `hx_*` | atributos HTMX | — | Parâmetros `hx-*` são repassados diretamente; booleanos viram `true`/`false`. |

### Exemplos

**Botão grande (padrão)**

```django
{% include "_components/back_button.html" with href=back_href fallback_href=default_url %}
```

**Link inline com rótulo customizado**

```django
{% include "_components/back_button.html" with variant='link' label=_('Voltar para a listagem') show_icon=False %}
```

**Ação compacta com HTMX**

```django
{% include "_components/back_button.html" with
    variant='compact'
    hx_get=modal_url
    hx_target='#modal'
    hx_swap='innerHTML'
    prevent_history=True
    fallback_href=default_url
%}
```

### Convenções

- Ícones utilizam a biblioteca Lucide via `{% lucide %}` e devem receber `aria_hidden='true'`.
- Sempre forneça `label` traduzido ou use o padrão `gettext('Voltar')`.
- Prefira `prevent_history=True` quando o clique abre conteúdo via HTMX e a
  navegação do usuário não deve retroceder.
- `fallback_href` garante uma rota segura quando o histórico do navegador não
  está disponível (ex.: acesso direto por URL compartilhada).

### Populando `back_component_config`

Views que desejam personalizar o botão exibido automaticamente em
`templates/base.html` devem preencher o dicionário `back_component_config` no
contexto. Os campos aceitos correspondem aos parâmetros da partial e serão
mesclados antes da inclusão:

```python
context["back_component_config"] = {
    "href": resolve_back_href(request, fallback="minha-rota"),
    "variant": "link",
    "label": _("Voltar para a listagem"),
    "show_icon": False,
}
```

Quando `back_component_config` não é informado, o template usa `back_href`,
preenchido automaticamente pelo context processor
`core.context_processors.back_navigation` (que utiliza `resolve_back_href`).

## cancel_button.html

Partial especializada para ações de cancelamento. É um _wrapper_ do
`back_button.html`, com `label`, `aria_label` e `variant` padronizados para os
valores de cancelamento. Dessa forma, os formulários exibem sempre
`gettext('Cancelar')` (com ícone oculto por padrão) e mantêm a semântica de
"voltar" apenas quando o usuário realmente está navegando.

### Parâmetros

Aceita os mesmos parâmetros de `back_button.html`. Apenas os padrões mudam:

| Nome | Padrão | Observação |
| --- | --- | --- |
| `label` | `gettext('Cancelar')` | O texto visível sempre utiliza o fallback traduzido. |
| `aria_label` | igual a `label` | Pode ser sobrescrito para casos específicos (ex.: `Cancelar edição`). |
| `variant` | `'button'` | Mantém visual de botão secundário. |
| `icon` | `'x'` | O ícone só aparece quando `show_icon=True`. |
| `show_icon` | `False` | Evita ícone redundante em ações de cancelamento. |

### Boas práticas

- Inclua o componente ao lado do botão principal do formulário, utilizando os
  `href`/`fallback_href` vindos da view.
- Utilize `cancel_component_config` quando precisar reutilizar as mesmas
  configurações em múltiplos pontos do template.
- Só apresente "Cancelar" e "Voltar" simultaneamente quando forem ações com
  propósitos distintos (por exemplo, cancelar o formulário vs. navegar para a
  página anterior). Caso ambas levem para o mesmo destino, mantenha apenas o
  botão de cancelamento ou o `back_button` no cabeçalho.

## Convenções de i18n

- Todo texto visível deve estar dentro de `{% trans %}` ou `{% blocktrans %}`.
- Atributos como `aria-label`, `alt` e placeholders precisam ser traduzíveis.
- Componentes adicionais (cards, formulários, etc.) devem seguir as mesmas
  regras ao serem criados.
