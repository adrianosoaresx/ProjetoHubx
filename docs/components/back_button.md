# Componente `_components/back_button.html`

O componente de botão de retorno centraliza o comportamento padrão de "voltar" na interface do HubX. Ele deve ser preferido em vez de botões avulsos com `history.back()` ou links manuais.

## Uso básico

```django
{% include '_components/back_button.html' %}
```

Exibe um botão secundário com ícone de seta e texto "Voltar", tentando navegar pelo histórico do navegador quando houver uma origem válida.

## Parâmetros disponíveis

| Parâmetro | Tipo | Padrão | Descrição |
| --- | --- | --- | --- |
| `label` | string | `"Voltar"` | Texto visível no botão. |
| `aria_label` | string | `label` | Rótulo acessível para leitores de tela. |
| `href` | string | `#` | URL usada para navegação padrão ou abertura em nova aba. |
| `fallback_href` | string | `None` | URL utilizada quando não há histórico válido. |
| `use_history` | boolean | `True` | Quando ativo, tenta usar `history.back()` antes de seguir o `href`. |
| `variant` | string | `"button"` | Aparência do componente: `button`, `link` ou `compact`. |
| `size` | string | `"md"` | Apenas para `variant="button"`. Aceita `sm`, `md` ou `lg`. |
| `classes` | string | `""` | Classes adicionais anexadas ao elemento principal. |
| `icon` | string | `"arrow-left"` | Ícone Lucide exibido ao lado do texto. |
| `hide_icon` | boolean | `False` | Remove o ícone quando verdadeiro. |
| `element` | string | `"a"` | Elemento HTML renderizado (`a` ou `button`). |
| `button_type` | string | `"button"` | Valor do atributo `type` quando `element="button"`. |
| `htmx_attrs` | dict | `None` | Dicionário com atributos HTMX (chaves sem o prefixo `hx-`). |
| `extra_attrs` | dict | `None` | Atributos arbitrários adicionais (`{"data-test": "foo"}`, por exemplo). |
| `hx_get`, `hx_post`, ... | string | `None` | Atributos HTMX individuais suportados diretamente (`hx_get`, `hx_target`, `hx_swap`, `hx_push_url`, etc.). |

## Variantes visuais

- `variant="button"` (padrão): botão cheio com classes `btn btn-secondary`. Combine com `size="sm"` ou `size="lg"` quando necessário.
- `variant="link"`: link textual com ícone.
- `variant="compact"`: botão circular icônico com rótulo apenas visível para leitores de tela.

## Integração com o histórico

Todos os elementos renderizam com `data-back-button`. Um script global (injetado em `base.html`) gerencia o comportamento de histórico e fallback automaticamente.

Quando `use_history=True`, o script tentará voltar à página anterior caso a origem pertença ao mesmo domínio e exista histórico. Caso contrário, usa `fallback_href` (se definido) ou respeita o `href` informado.

## Uso com HTMX

Informe `use_history=False` para evitar interferência com requisições HTMX e forneça os atributos necessários:

```django
{% include '_components/back_button.html' with
    variant='button'
    size='sm'
    use_history=False
    hx_get=conexoes_partial_url
    hx_target='#perfil-content'
    hx_push_url='?section=conexoes'
%}
```

O componente aplicará automaticamente os atributos `hx-*` suportados.

## Integração com templates base

`base.html` injeta automaticamente o componente antes do bloco principal de conteúdo sempre que a view definir `back_href` ou `back_component_config`. Esse comportamento pode ser sobrescrito redefinindo o bloco `{% block back_button %}` em templates específicos.
