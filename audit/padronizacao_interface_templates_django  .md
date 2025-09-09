# Refatoração de Templates Django  
## Relatório de Inconsistências de Estilo

### Objetivo
Este relatório analisa o **padrão de estilos** do repositório **ProjetoHubx** para verificar se os templates de listas (e outras páginas) estão alinhados com o layout desejado.  
O objetivo final é alcançar um **layout unificado**, com barra lateral fixa, cabeçalho superior, seção *hero* e grade de cards responsiva:contentReference[oaicite:0]{index=0}.

As análises consideraram os arquivos **CSS** e **templates HTML** da aplicação, com foco em:
- Uso de cores e classes utilitárias do Tailwind e do design system (`hubx.css`);
- Componentes reutilizáveis (cards, botões, modais, formulários);
- Padronização de listas (grade de cards vs tabelas);
- Suporte a tema claro/escuro;
- Acessibilidade e uso de semântica HTML.

---

### Resumo do Layout Esperado
- **Navegação lateral fixa e colapsável**: menu à esquerda, com ícones e etiquetas traduzidas; cores e *hover* baseados em variáveis do tema.  
- **Cabeçalho superior**: logotipo, campo de busca, seletor de tema, notificações e avatar do usuário.  
- **Seção Hero**: gradiente azul (de `#3b82f6` para `#1e40af`), título/subtítulo e ações contextuais.  
- **Grade de cards**: lista de itens dispostos em *grid* responsivo (`card-grid`) com espaçamento consistente e cartões arredondados:contentReference[oaicite:1]{index=1}.

---

### Mapeamento de Estilos Existentes
#### Design System (`hubx.css`)
- Variáveis CSS para cores, tipografia, espaçamento, bordas e sombras, com variantes claro/escuro.  
- Reset e estilos base com `@layer base`.  
- Componentes utilitários em `@layer components` (`.card`, `.btn`, `.alert`, `.badge`, `.modal`, `.dropdown`).  
- Suporte a variações de botões, modais, alerts etc.  
- Definição de classes para contêineres (`.container`, `.container-sm`, `.container-lg`) e estados (`#sidebar a[aria-current='page']`):contentReference[oaicite:2]{index=2}.

#### Layout Base (`templates/base.html`)
- Carga dinâmica de tema via `localStorage` (`claro`, `escuro` ou automático).  
- Inclusão de Tailwind e `hubx.css`.  
- Barra lateral e *header* definidos em parciais (`nav_sidebar.html`, `hero.html`).  
- Estrutura flexível com `ml-64` ou `ml-0` para colapsação:contentReference[oaicite:3]{index=3}.

#### Componentes
- `hero.html`: seção com gradiente azul e títulos; usa classes *hardcoded*.  
- `nav_sidebar.html`: menu vertical com links e ícones, usa classes Tailwind diretas em vez de variáveis.  
- `pagination.html` e `search_form.html`: paginação padrão e busca com HTMX.  
- `templates/partials/cards/*.html`: cards de empresas, eventos, núcleos; variação entre utilitários Tailwind e classes de design system:contentReference[oaicite:4]{index=4}.

---

### Inconsistências Identificadas
1. Mistura de **cores fixas** e variáveis do design system.  
2. Repetição de utilitários Tailwind sem uso de **componentes reutilizáveis**.  
3. **Hero** e menu lateral com estilos inconsistentes.  
4. Uso heterogêneo de **tabelas versus cards**.  
5. Formulários e inputs sem padronização, ausência do plugin `@tailwindcss/forms`.  
6. **Dark mode parcial**, com elementos sem variantes `dark:`.  
7. **Nomenclatura inconsistente** de parciais e componentes:contentReference[oaicite:5]{index=5}.

---

### Recomendações para Unificação de Estilos
1. **Centralizar tokens de cor** – substituir cores fixas (`bg-white`, `bg-slate-100`) por variáveis (`--bg-secondary`, `--bg-tertiary`).  
2. **Adotar componentes utilitários** (`.card`, `.btn-primary`, `.container`, `.card-grid`).  
3. **Parametrizar o Hero** – variáveis `--hero-from`, `--hero-to` no design system.  
4. **Unificar menu lateral** – criar `.sidebar-item`, `.sidebar-item-active`, com variáveis de cor e `aria-current="page"`.  
5. **Converter tabelas simples em cards** – listas pequenas devem migrar para `card-grid`.  
6. **Uniformizar formulários** – uso consistente de `@tailwindcss/forms`, macros ou parciais de campos.  
7. **Cobertura completa do dark mode** – revisar todos os componentes.  
8. **Padronizar nomenclatura e organização** – mover componentes para `templates/components/`, renomear arquivos duplicados:contentReference[oaicite:6]{index=6}.

---

### Próximos Passos
- Inventariar componentes – catálogo com exemplos de cards, botões, formulários, modais.  
- Refatorar incrementalmente – começar por **empresas**, aplicar variáveis e componentes.  
- Remover CSS legado – eliminar classes duplicadas e arquivos obsoletos.  
- Atualizar documentação – manter guia em Markdown no repositório para evitar regressões:contentReference[oaicite:7]{index=7}.

---

📌 **Conclusão**:  
Seguindo estas diretrizes, o projeto alcançará **uniformidade visual**, facilitará a **manutenção de código** e garantirá aderência ao **layout ideal** definido para o Hubx.Space.
