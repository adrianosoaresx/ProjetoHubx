---
title: Requisitos do Módulo Financeiro – versão 1.1
version: "1.1"
data: 2025-08-12
descricao: >-
  Este documento descreve os requisitos funcionais, não‑funcionais e modelos de
  dados do módulo **Financeiro** do Projeto Hubx. A versão 1.1 incorpora
  funcionalidades adicionais identificadas no código fonte, tais como ajuste
  de lançamentos, previsão de fluxo de caixa, repasses automáticos de
  receita, logs de auditoria e métricas, integrações externas e novas
  opções de exportação. Os requisitos da versão 1.0 continuam válidos e
  foram ampliados para refletir as implementações observadas.
---

## Visão geral

O módulo **Financeiro** é responsável por gerenciar cobranças, pagamentos,
aporte de associados, centro de custos, distribuição de receitas e
relatórios para organizações, núcleos e eventos. Ele integra-se ao módulo
de notificações para informar usuários sobre faturas pendentes,
inadimplências, repasses e ajustes, e oferece APIs e páginas de
administração para operadores financeiros. A versão 1.1 adiciona
funcionalidades como previsão financeira, ajustes pós‑pagamento,
integração com provedores de pagamento via API, repasses automáticos de
receita de eventos e exportação de relatórios em múltiplos formatos.

## Escopo e públicos atendidos

O escopo do módulo abrange:

* Organizações e núcleos que precisam gerenciar receitas e despesas,
  cadastrar cobranças recorrentes, registrar aportes e acompanhar a
  inadimplência de seus membros.
* Usuários associados que precisam visualizar e pagar suas faturas,
  consultar extratos e registrar aportes voluntários.
* Operadores e administradores financeiros responsáveis por importar
  pagamentos, analisar relatórios e auditar lançamentos.
* Integrações externas para processar pagamentos, enviar notificações e
  exportar dados (CSV, XLSX) para outros sistemas.

## Requisitos funcionais

### RF‑01 – Importação de pagamentos

1. O sistema deve permitir a importação de arquivos de pagamento em
   formato CSV ou XLSX contendo cobranças quitadas ou canceladas【458396843023144†L166-L259】.
2. Durante a importação deve haver uma fase de pré‑visualização, onde
   apenas as linhas válidas são listadas e eventuais erros são
   destacados para correção pelo operador【458396843023144†L166-L259】.
3. Após a confirmação, as linhas válidas devem ser processadas
   assincronamente, registrando os pagamentos, atualizando saldos e
   criando logs de importação. Linhas com erro devem ser salvas em um
   arquivo de erros disponível para reprocessamento posterior【321491402577886†L43-L87】.
4. O sistema deve permitir reprocessar importações com erro sem
   duplicar lançamentos já processados【458396843023144†L166-L259】.
5. A importação deve respeitar idempotência utilizando chaves únicas
   para evitar inserções duplicadas【317557001661130†L282-L315】.

### RF‑02 – Geração de cobranças recorrentes

1. O sistema deve gerar cobranças mensais automáticas para associados e
   núcleos, calculando valores conforme as configurações da organização
   (taxas de associação, porcentagens)【41958861768121†L67-L119】.
2. Cobranças devem ser registradas com datas de vencimento e tipos
   adequados (associação, núcleo, evento), evitando duplicidades para o
   mesmo período【41958861768121†L67-L119】.
3. As cobranças geradas devem ser enviadas aos usuários via módulo de
   notificações e registradas no histórico de cobranças【41958861768121†L67-L119】.
4. O sistema deve permitir ajustar valores das cobranças futuras
   conforme reajustes definidos pela organização (ex.: índices
   inflacionários) – melhoria para versão futura.

### RF‑03 – Centro de custos e saldos

1. Deve existir um modelo de **Centro de Custo** para organizar
   receitas e despesas por organização, núcleo ou evento. Cada centro
   possui nome, descrição, data de criação e campos de auditoria.
2. Cada usuário associado deve possuir uma **Conta Associado** com
   saldo acumulado, atualizada a cada pagamento ou aporte.
3. A aplicação deve permitir registrar **lançamentos financeiros** com
   tipo (aporte interno, receita, despesa, ajuste), valor,
   data de vencimento, data de pagamento, status (pendente, pago,
   cancelado), origem (cobrança recorrente, importação, repasse, ajuste
   manual), centro de custo e usuário responsável【317557001661130†L80-L160】.
4. Os lançamentos devem suportar relacionamento com o lançamento
   original, permitindo criar ajustes posteriores que registram a
   diferença em um lançamento vinculado【93784247691659†L14-L52】.
5. O sistema deve permitir cancelar ou marcar como pago um lançamento
   diretamente via API ou interface administrativa, registrando o
   responsável e o momento da ação【936392746328106†L139-L153】.

### RF‑04 – Aportes de associados

1. Os usuários devem poder registrar **aportes voluntários**, que
   creditem diretamente sua conta associada, gerando um lançamento
   positivo do tipo `APORTE` e atualizando saldo.
2. A plataforma deve emitir um recibo digital do aporte, notificando
   o usuário e a organização responsável.
3. Aportes podem ser estornados apenas por administradores, criando um
   lançamento inverso (ajuste) e mantendo registro da ação【93784247691659†L14-L52】.

### RF‑05 – Relatórios e dashboards

1. Deve existir uma API para obter **relatórios financeiros**
   agregados com filtros por período, centro de custo, tipo de
   lançamento e status【458396843023144†L261-L327】.
2. Os relatórios devem apresentar métricas como total de receitas,
   despesas, aportes, número de inadimplentes e valores em atraso.
3. A interface deve permitir exportar relatórios em formatos CSV e
   XLSX com os mesmos filtros aplicados【458396843023144†L261-L327】.
4. O módulo deve oferecer também relatórios de **inadimplências**,
   listando lançamentos vencidos e não pagos e permitindo exportação
   em CSV/XLSX【458396843023144†L335-L399】.
5. Para fins de previsão, o sistema deve disponibilizar uma
   **previsão de fluxo de caixa** baseada em média móvel e ajustes
   sazonais, permitindo parametrizar crescimento e redução das
   receitas/despesas; os resultados devem ser armazenados em cache e
   exportáveis em CSV/XLSX【936392746328106†L214-L295】.

### RF‑06 – Gestão de inadimplência

1. O sistema deve identificar cobranças vencidas não pagas e
   notificar os devedores conforme regras definidas pela organização
   (quantidade de dias de atraso e periodicidade)【818264525686925†L18-L75】.
2. Para cada notificação, o lançamento deve ter atualizada a data da
   última notificação para evitar notificações repetidas no mesmo
   período【818264525686925†L18-L75】.
3. Administradores devem ter acesso a uma lista de inadimplentes, com
   possibilidade de exportar os dados e registrar acordos ou
   pagamentos parciais【458396843023144†L335-L399】.

### RF‑07 – Ajustes e correções de lançamentos

1. O sistema deve permitir ajustar um lançamento já pago, criando um
   novo lançamento que representa a diferença positiva ou negativa e
   marcando o original como ajustado【93784247691659†L14-L52】.
2. Ajustes devem ser auditados em log e notificar o usuário afetado
   sobre o valor corrigido【93784247691659†L14-L52】.

### RF‑08 – Distribuição de receitas de eventos

1. Quando ingressos de eventos são marcados como pagos, o sistema deve
   disparar automaticamente a **distribuição de receita**, creditando
   parte do valor para o núcleo organizador e parte para a organização
   conforme a política de repasse【779450757024936†L15-L60】.
2. Deve existir uma função para realizar **repasses manuais**,
   permitindo dividir receitas entre diferentes centros de custo e
   registrando a operação em log【779450757024936†L62-L135】.
3. O sistema deve atualizar saldos de cada centro de custo e emitir
   notificações aos usuários e administradores envolvidos【779450757024936†L15-L60】.

### RF‑09 – Integrações externas

1. O módulo deve permitir configurar provedores de pagamento
   (integrador financeiro) com informações de URL, credenciais e
   parâmetros de autenticação【317557001661130†L258-L279】.
2. Chamadas a provedores externos devem registrar logs de requisições e
   respostas, incluindo idempotência para evitar reenvio de dados【317557001661130†L282-L315】.
3. Em caso de falhas na integração, o sistema deve permitir retentar
   automaticamente e registrar os erros em log【317557001661130†L282-L315】.

### RF‑10 – Auditoria e métricas

1. Todas as ações que alteram dados financeiros (criação, edição,
   pagamento, cancelamento, importação, ajuste, repasse) devem ser
   registradas em um log contendo ação, usuário, dados anteriores e
   dados novos【317557001661130†L214-L237】.
2. As tarefas assíncronas devem registrar seu início, fim, status e
   detalhes em um log de tarefas【317557001661130†L240-L255】.
3. O sistema deve expor métricas via Prometheus, incluindo contador de
   lançamentos criados, métricas de duração de tarefas, número de
   notificações enviadas e erros encontrados【311417496235686†L23-L53】.

### RF‑11 – Notificações

1. O módulo financeiro deve integrar-se ao sistema de notificações para
   enviar mensagens sobre novas cobranças, vencimentos, inadimplências,
   repasses de eventos e ajustes de lançamentos【130417569016172†L14-L68】.
2. As notificações devem incluir detalhes do lançamento (valor, data
   de vencimento, status) e links para pagamento ou consulta do
   extrato.
3. Deve existir um mecanismo para evitar envio de notificações
   duplicadas para o mesmo lançamento no mesmo dia【818264525686925†L18-L75】.

## Requisitos não funcionais

### RNF‑01 – Desempenho

1. Importações de pagamentos devem processar no mínimo 1000 linhas por
   segundo em ambiente de produção, utilizando processamento
   assíncrono e batch. Pré‑visualizações devem responder em menos de
   2 s.
2. As consultas de relatórios e previsões devem entregar resultados em
   até 2 s para conjuntos de até 10 000 lançamentos.
3. Geração de cobranças mensais não deve impactar a performance do
   sistema de forma perceptível aos usuários.

### RNF‑02 – Confiabilidade e consistência

1. O sistema deve garantir consistência das transações financeiras
   utilizando bloqueios e transações atômicas, evitando
   duplicidades.
2. Em caso de falhas na importação ou geração de cobranças, as
   operações devem ser revertidas e logs de erro gerados para
   investigação.

### RNF‑03 – Segurança e auditoria

1. Dados sensíveis (como credenciais de provedores e chaves
   idempotência) devem ser armazenados de forma criptografada e
   mascarados em logs.
2. Apenas usuários com perfil apropriado (financeiro, admin) podem
   acessar APIs de importação, geração de cobranças, ajustes e
   repasses. As permissões devem ser aplicadas nas views e viewsets.

### RNF‑04 – Escalabilidade e integridade

1. O módulo deve suportar múltiplas organizações e núcleos isolados,
   garantindo que dados de uma entidade não sejam expostos a outra.
2. Previsões financeiras e relatórios devem ser cacheados por
   parâmetros de consulta para reduzir carga de cálculo e banco de
   dados【936392746328106†L214-L295】.

### RNF‑05 – Observabilidade

1. O módulo deve expor métricas de performance, uso e erros via
   Prometheus, permitindo a monitoração contínua【311417496235686†L23-L53】.
2. Os logs de auditoria e tarefas devem ser persistidos por no mínimo
   cinco anos para fins de compliance【317557001661130†L214-L237】.

### RNF‑06 – Usabilidade

1. As interfaces administrativas devem ser responsivas e apresentar
   informações financeiras de forma clara, com filtros, gráficos e
   exportações acessíveis.
2. As mensagens de erro e de importação devem ser claras, indicando
   linha e motivo do problema para facilitar correção pelo operador.

## Modelos de dados

Os principais modelos são listados a seguir (substituindo a tabela por
descrições lineares):

* **Centro de Custo** – representa um agrupador de receitas e despesas
  vinculado a uma organização, núcleo ou evento. Contém campos como
  nome, descrição, tipo de escopo, identificador do escopo e
  metadados de auditoria.
* **Conta Associado** – registra o saldo de um usuário associado,
  incluindo valores acumulados de cobranças pagas, aportes e ajustes.
* **Lancamento Financeiro** – representa um registro financeiro de
  receita, despesa, aporte ou ajuste. Contém valor, data de
  vencimento, data de pagamento, status (pendente, pago, cancelado),
  origem do lançamento, usuário, centro de custo, indicação de
  lançamento original (para ajustes) e campos de auditoria【317557001661130†L80-L160】.
* **ImportacaoPagamentos** – armazena metadados de importações de
  pagamentos, incluindo nome do arquivo importado, status
  (processando, concluído, erro), quantidade de linhas processadas e
  arquivo de erros, bem como ligação ao usuário que iniciou a
  importação【317557001661130†L182-L208】.
* **FinanceiroLog** – registra ações relevantes sobre lançamentos
  (criação, edição, cancelamento, pagamento, ajuste, repasse),
  armazenando usuário, ação, dados anteriores e novos e timestamp
  【317557001661130†L214-L237】.
* **FinanceiroTaskLog** – guarda informações sobre tarefas assíncronas
  (importação, geração de cobranças, previsões) como nome, status,
  data de início e término, detalhes e usuário responsável【317557001661130†L240-L255】.
* **IntegracaoConfig** – contém configurações de provedores externos
  (URLs, credenciais) e opções de autenticação【317557001661130†L258-L279】.
* **IntegracaoIdempotency** – armazena chaves idempotentes usadas para
  evitar reprocessamento de pedidos externos【317557001661130†L282-L315】.
* **IntegracaoLog** – registra todas as chamadas a provedores externos,
  incluindo requisição, resposta, status e relação com a chave
  idempotente【317557001661130†L282-L315】.

## Casos de uso (cenários Gherkin)

### Importação de pagamentos com pré‑visualização

```
Funcionalidade: Importar pagamentos
  Como operador financeiro da organização
  Desejo importar um arquivo de pagamentos com pré‑visualização
  Para processar cobranças pagas de forma segura

  Cenário: Pré‑visualizar importação
    Dado que estou autenticado como operador
    E forneço um arquivo CSV contendo cobranças pagas
    Quando solicito a pré‑visualização da importação
    Então o sistema deve listar as linhas válidas e exibir mensagens
    de erro para linhas inválidas
    E não deve criar lançamentos neste momento

  Cenário: Confirmar importação
    Dado que revisei a pré‑visualização da importação
    Quando confirmo a importação
    Então o sistema deve processar as linhas válidas de forma assíncrona
    E atualizar saldos e status dos lançamentos
    E notificar os usuários sobre seus pagamentos registrados

  Cenário: Reprocessar importação com erro
    Dado que existe uma importação com status "erro" e um arquivo de erros
    Quando seleciono reprocessar a importação
    Então o sistema deve tentar processar apenas as linhas ainda não
    processadas, evitando duplicidade
    E atualizar o status da importação conforme o resultado
```

### Ajustar lançamento de cobrança

```
Funcionalidade: Ajustar lançamento
  Como administrador financeiro
  Desejo corrigir um lançamento pago
  Para refletir o valor correto e manter histórico

  Cenário: Criar ajuste positivo
    Dado que existe um lançamento pago com valor incorreto
    Quando registro um ajuste com valor maior
    Então o sistema deve criar um novo lançamento de diferença
    E associar o ajuste ao lançamento original
    E notificar o usuário sobre o valor ajustado

  Cenário: Criar ajuste negativo
    Dado que existe um lançamento pago com valor maior que o devido
    Quando registro um ajuste com valor menor
    Então o sistema deve criar um novo lançamento com valor negativo
    E associar o ajuste ao lançamento original
    E notificar o usuário sobre o valor corrigido
```

### Previsão de fluxo de caixa

```
Funcionalidade: Prever fluxo de caixa
  Como gestor financeiro
  Desejo projetar receitas e despesas futuras
  Para planejar o orçamento e tomada de decisão

  Cenário: Gerar previsão básica
    Dado que há dados de lançamentos dos últimos 12 meses
    Quando solicito a previsão sem parâmetros adicionais
    Então o sistema deve calcular a média móvel e tendências
    E apresentar as previsões de receitas e despesas para os próximos 6 meses
    E permitir exportar os resultados em CSV ou XLSX

  Cenário: Ajustar crescimento e redução
    Dado que desejo simular cenários de crescimento e redução
    Quando forneço parâmetros de aumento de receita de 10% e redução de despesas de 5%
    Então o sistema deve aplicar esses percentuais à previsão
    E apresentar os valores ajustados nos relatórios e exportações
```

## Considerações finais

A versão 1.1 do módulo **Financeiro** amplia substancialmente o escopo
original, oferecendo importação robusta de pagamentos com pré‑visualização
e reprocessamento, geração de cobranças recorrentes, gestão de saldos e
centros de custo, ajustes pós‑pagamento, distribuição automática de
receitas de eventos, previsões de fluxo de caixa, integração com
provedores externos, auditoria detalhada, notificações e métricas.
Todas as funcionalidades implementadas no código foram mapeadas neste
documento. A partir desta versão, recomenda‑se atualizar a análise de
risco e políticas de segurança para contemplar o armazenamento de
credenciais de integrações e a retenção prolongada de logs.