# Auditoria de Navegação de Retorno

Este relatório resume o mapeamento dos principais fluxos solicitados para
validar o comportamento do botão de voltar/cancelar com e sem histórico do
navegador. Cada cenário foi acessado via menu interno e diretamente pela URL
para confirmar a presença de `fallback_href` seguro.

## Cenários auditados

1. **Criação de eventos** (`/eventos/novo/`)
   - Acesso pelo menu Eventos → "Adicionar evento" e acesso direto via URL.
   - O botão "Voltar" utiliza `resolve_back_href` com fallback para o
     calendário de eventos, evitando loops quando não há histórico.
   - Evidência sugerida: capturar o formulário vazio com o botão configurado
     apontando para `/eventos/calendario/`.

2. **Cadastro de organizações** (`/organizacoes/nova/`)
   - Acesso via menu Administrador → "Organizações" → "Adicionar" e acesso
     direto via URL.
   - Tanto o botão de voltar do rodapé quanto o botão global utilizam o fallback
     para a listagem de organizações.
   - Evidência sugerida: screenshot do formulário exibindo o botão "Cancelar"
     com destino `/organizacoes/`.

3. **Tokens – geração e listagem**
   - Listagem (`/tokens/`): abertura pelo menu lateral e acesso direto. O botão
     de retorno agora cai no mural pessoal (`/feed/mural/`) caso não exista
     histórico válido.
   - Geração (`/tokens/gerar/`): abertura via CTA do hero e acesso direto. O
     botão de voltar/cancelar aponta para a listagem de convites.
   - Evidência sugerida: capturas separadas da listagem e da tela de geração
     destacando o atributo `data-fallback-href` aplicado.

4. **Publicação no feed** (`/feed/nova/`)
   - Fluxo exercitado pelo botão "Nova postagem" do feed e acesso direto.
   - O fallback mantém o retorno seguro para `/feed/listar/` para garantir que o
     usuário não fica preso ao formulário.
   - Evidência sugerida: screenshot do formulário de publicação com o botão
     "Cancelar" visível.

## Como validar

Para repetir os testes:

1. Autentique-se com um usuário habilitado para o fluxo.
2. Limpe o histórico do navegador (ou abra em aba anônima) e acesse a rota
   diretamente; clique em "Voltar" e confirme que o fallback é utilizado.
3. Navegue até o fluxo através dos links internos; clique em "Voltar" e
   verifique que o histórico imediato é respeitado.
4. Ao capturar evidências visuais, inclua o console do navegador mostrando o
   atributo `data-fallback-href` ou a URL de destino para apoiar o time de
   design.

Os ajustes aplicados garantem que os componentes compartilham a mesma lógica de
fallback definida pelo utilitário `resolve_back_href`, centralizando a gestão de
rotas seguras e reduzindo loops involuntários.
