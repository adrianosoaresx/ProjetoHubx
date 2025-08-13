---
id: REQ-FINANCEIRO-001
title: Requisitos Financeiro Hubx
module: financeiro
status: Rascunho
version: "1.1.0"
authors: [preencher@hubx.space]
created: "2025-08-12"
updated: "2025-08-13"
owners: [preencher]
reviewers: [preencher]
tags: [backend, api, frontend, segurança, lgpd]
related_docs: []
dependencies: []
---

## 1. Visão Geral

O módulo **Financeiro** é responsável por gerenciar cobranças, pagamentos, aporte de associados, centro de custos, distribuição de receitas e relatórios para organizações, núcleos e eventos. Ele integra-se ao módulo de notificações para informar usuários sobre faturas pendentes, inadimplências, repasses e ajustes, e oferece APIs e páginas de administração para operadores financeiros. A versão 1.1 adiciona previsão financeira, ajustes pós-pagamento, repasses automáticos de receita de eventos, integrações externas e exportação de relatórios em múltiplos formatos.

## 2. Escopo

O escopo do módulo abrange:

- Organizações e núcleos que precisam gerenciar receitas e despesas, cadastrar cobranças recorrentes, registrar aportes e acompanhar a inadimplência de seus membros.
- Usuários associados que precisam visualizar e pagar suas faturas, consultar extratos e registrar aportes voluntários.
- Operadores e administradores financeiros responsáveis por importar pagamentos, analisar relatórios e auditar lançamentos.
- Integrações externas para processar pagamentos, enviar notificações e exportar dados (CSV, XLSX) para outros sistemas.

## 3. Requisitos Funcionais

### RF-01 – Importação de pagamentos

1. O sistema deve permitir a importação de arquivos de pagamento em formato CSV ou XLSX contendo cobranças quitadas ou canceladas.
2. Durante a importação deve haver uma fase de pré-visualização, onde apenas as linhas válidas são listadas e eventuais erros são destacados para correção pelo operador.
3. Após a confirmação, as linhas válidas devem ser processadas assincronamente, registrando os pagamentos, atualizando saldos e criando logs de importação. Linhas com erro devem ser salvas em um arquivo de erros disponível para reprocessamento posterior.
4. O sistema deve permitir reprocessar importações com erro sem duplicar lançamentos já processados.
5. A importação deve respeitar idempotência utilizando chaves únicas para evitar inserções duplicadas.

### RF-02 – Geração de cobranças recorrentes

1. O sistema deve gerar cobranças mensais automáticas para associados e núcleos, calculando valores conforme as configurações da organização (taxas de associação, porcentagens).
2. Cobranças devem ser registradas com datas de vencimento e tipos adequados (associação, núcleo, evento), evitando duplicidades para o mesmo período.
3. As cobranças geradas devem ser enviadas aos usuários via módulo de notificações e registradas no histórico de cobranças.
4. O sistema deve permitir ajustar valores das cobranças futuras conforme reajustes definidos pela organização (ex.: índices inflacionários).

### RF-03 – Centro de custos e saldos

1. Deve existir um modelo de **Centro de Custo** para organizar receitas e despesas por organização, núcleo ou evento. Cada centro possui nome, descrição, data de criação e campos de auditoria.
2. Cada usuário associado deve possuir uma **Conta Associado** com saldo acumulado, atualizada a cada pagamento ou aporte.
3. A aplicação deve permitir registrar **lançamentos financeiros** com tipo (aporte interno, receita, despesa, ajuste), valor, data de vencimento, data de pagamento, status (pendente, pago, cancelado), origem (cobrança recorrente, importação, repasse, ajuste manual), centro de custo e usuário responsável.
4. Os lançamentos devem suportar relacionamento com o lançamento original, permitindo criar ajustes posteriores que registram a diferença em um lançamento vinculado.
5. O sistema deve permitir cancelar ou marcar como pago um lançamento diretamente via API ou interface administrativa, registrando o responsável e o momento da ação.

### RF-04 – Aportes de associados

1. Os usuários devem poder registrar **aportes voluntários**, que creditem diretamente sua conta associada, gerando um lançamento positivo do tipo `APORTE` e atualizando saldo.
2. A plataforma deve emitir um recibo digital do aporte, notificando o usuário e a organização responsável.
3. Aportes podem ser estornados apenas por administradores, criando um lançamento inverso (ajuste) e mantendo registro da ação.

### RF-05 – Relatórios e dashboards

1. Deve existir uma API para obter **relatórios financeiros** agregados com filtros por período, centro de custo, tipo de lançamento e status.
2. Os relatórios devem apresentar métricas como total de receitas, despesas, aportes, número de inadimplentes e valores em atraso.
3. A interface deve permitir exportar relatórios em formatos CSV e XLSX com os mesmos filtros aplicados.
4. O módulo deve oferecer também relatórios de **inadimplências**, listando lançamentos vencidos e não pagos e permitindo exportação em CSV/XLSX.
5. Para fins de previsão, o sistema deve disponibilizar uma **previsão de fluxo de caixa** baseada em média móvel e ajustes sazonais, permitindo parametrizar crescimento e redução das receitas/despesas; os resultados devem ser armazenados em cache e exportáveis em CSV/XLSX.

### RF-06 – Gestão de inadimplência

1. O sistema deve identificar cobranças vencidas não pagas e notificar os devedores conforme regras definidas pela organização, incluindo lembretes antes e após o vencimento.
2. As notificações devem conter informações relevantes (valor, data de vencimento, status) e links para pagamento ou consulta do extrato.
3. Deve existir um mecanismo para evitar envio de notificações duplicadas para o mesmo lançamento no mesmo dia.

### RF-07 – Ajustes e correções de lançamentos

1. O sistema deve permitir criar lançamentos de ajuste vinculados a lançamentos originais, registrando diferenças positivas ou negativas.
2. Ajustes devem atualizar saldos das contas associadas e gerar logs de auditoria.

### RF-08 – Distribuição de receitas de eventos

1. Receitas de eventos devem ser distribuídas automaticamente entre organização, núcleo e participantes conforme regras configuráveis.
2. O sistema deve registrar lançamentos de repasse e permitir relatórios de distribuição.

### RF-09 – Integrações externas

1. O módulo deve integrar-se a provedores de pagamento via API para processar cobranças e registrar retornos.
2. Deve permitir configuração de credenciais, URLs e opções de autenticação por organização.

### RF-10 – Auditoria e métricas

1. Todas as ações relevantes sobre lançamentos (criação, edição, cancelamento, pagamento, ajuste, repasse) devem ser registradas em logs de auditoria.
2. Métricas de processamento (tempo, volume, erros) devem ser coletadas para análise e monitoramento.

### RF-11 – Notificações

1. O módulo deve enviar notificações para eventos financeiros relevantes, como geração de cobrança, confirmação de pagamento, ajuste e repasse.
2. As notificações devem ser registradas e permitir rastreabilidade.

## 4. Requisitos Não Funcionais

### Performance
- **RNF-01** Importações de pagamentos devem processar no mínimo 1000 linhas por segundo em produção, com processamento assíncrono e batch; pré-visualizações devem responder em menos de 2 s.
- **RNF-02** Consultas de relatórios e previsões devem entregar resultados em até 2 s para conjuntos de até 10 000 lançamentos.
- **RNF-03** Geração de cobranças mensais não deve impactar perceptivelmente a performance do sistema.

### Segurança & LGPD
- **RNF-04** Dados sensíveis, como credenciais de provedores e chaves idempotentes, devem ser armazenados de forma criptografada e mascarados em logs.
- **RNF-05** Apenas usuários com perfil apropriado (financeiro, admin) podem acessar APIs de importação, geração de cobranças, ajustes e repasses; permissões devem ser aplicadas nas views e viewsets.

### Observabilidade
- **RNF-06** O módulo deve expor métricas de performance, uso e erros via Prometheus, permitindo a monitoração contínua.
- **RNF-07** Logs de auditoria e tarefas devem ser persistidos por no mínimo cinco anos para fins de compliance.

### Acessibilidade & i18n
- **RNF-08** Interfaces administrativas devem ser responsivas e apresentar informações financeiras de forma clara, com filtros, gráficos e exportações acessíveis.
- **RNF-09** Mensagens de erro e de importação devem indicar linha e motivo do problema para facilitar correção pelo operador.

### Resiliência
- **RNF-10** O sistema deve garantir consistência das transações financeiras utilizando bloqueios e transações atômicas; em caso de falhas na importação ou geração de cobranças, as operações devem ser revertidas e logs de erro gerados.

### Arquitetura & Escala
- **RNF-11** O módulo deve suportar múltiplas organizações e núcleos isolados, garantindo que dados de uma entidade não sejam expostos a outra.
- **RNF-12** Previsões financeiras e relatórios devem ser cacheados por parâmetros de consulta para reduzir carga de cálculo e banco de dados.

## 5. Casos de Uso

### UC-01 – Importar pagamentos
1. Operador seleciona arquivo CSV ou XLSX contendo cobranças.
2. Sistema pré-visualiza linhas válidas e erros.
3. Operador confirma a importação.
4. Sistema processa linhas válidas assincronamente, atualiza saldos e notifica usuários.

### UC-02 – Ajustar lançamento
1. Administrador seleciona lançamento pago com valor incorreto.
2. Sistema permite criar ajuste positivo ou negativo associado ao lançamento original.
3. Sistema notifica o usuário sobre o valor ajustado.

### UC-03 – Prever fluxo de caixa
1. Gestor solicita previsão com dados dos últimos 12 meses.
2. Sistema calcula média móvel e tendências, permitindo parâmetros de crescimento e redução.
3. Resultado é apresentado e pode ser exportado em CSV ou XLSX.

## 6. Regras de Negócio
- ...

## 7. Modelo de Dados

### Financeiro.CentroDeCusto
Descrição: Agrupador de receitas e despesas por organização, núcleo ou evento.
Campos:
- `nome`: …
- `descricao`: …
- `tipo_escopo`: …
- `escopo_id`: …
- metadados de auditoria
Constraints adicionais:
- …

### Financeiro.ContaAssociado
Descrição: Saldo de um usuário associado.
Campos:
- `saldo`: …
- metadados de auditoria
Constraints adicionais:
- …

### Financeiro.LancamentoFinanceiro
Descrição: Registro de receita, despesa, aporte ou ajuste.
Campos:
- `valor`: …
- `data_vencimento`: …
- `data_pagamento`: …
- `status`: pendente | pago | cancelado
- `origem`: …
- `usuario`: …
- `centro_custo`: …
- `lancamento_original`: …
- metadados de auditoria
Constraints adicionais:
- …

### Financeiro.ImportacaoPagamentos
Descrição: Metadados de importações de pagamentos.
Campos:
- `arquivo_nome`: …
- `status`: processando | concluido | erro
- `linhas_processadas`: …
- `arquivo_erros`: …
- `usuario`: …
Constraints adicionais:
- …

### Financeiro.FinanceiroLog
Descrição: Registro de ações sobre lançamentos.
Campos:
- `usuario`: …
- `acao`: …
- `dados_anteriores`: …
- `dados_novos`: …
- `timestamp`: …
Constraints adicionais:
- …

### Financeiro.FinanceiroTaskLog
Descrição: Informações sobre tarefas assíncronas.
Campos:
- `nome`: …
- `status`: …
- `inicio`: …
- `fim`: …
- `detalhes`: …
- `usuario`: …
Constraints adicionais:
- …

### Financeiro.IntegracaoConfig
Descrição: Configurações de provedores externos.
Campos:
- `url`: …
- `credenciais`: …
- `autenticacao`: …
Constraints adicionais:
- …

### Financeiro.IntegracaoIdempotency
Descrição: Chaves idempotentes para evitar reprocessamento.
Campos:
- `chave`: …
- metadados de requisição
Constraints adicionais:
- …

### Financeiro.IntegracaoLog
Descrição: Registro de chamadas a provedores externos.
Campos:
- `requisicao`: …
- `resposta`: …
- `status`: …
- `chave_idempotente`: …
Constraints adicionais:
- …

## 8. Critérios de Aceite (Gherkin)

### Importação de pagamentos com pré-visualização
```gherkin
Funcionalidade: Importar pagamentos
  Como operador financeiro da organização
  Desejo importar um arquivo de pagamentos com pré-visualização
  Para processar cobranças pagas de forma segura

  Cenário: Pré-visualizar importação
    Dado que estou autenticado como operador
    E forneço um arquivo CSV contendo cobranças pagas
    Quando solicito a pré-visualização da importação
    Então o sistema deve listar as linhas válidas e exibir mensagens
    de erro para linhas inválidas
    E não deve criar lançamentos neste momento

  Cenário: Confirmar importação
    Dado que revisei a pré-visualização da importação
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
```gherkin
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
```gherkin
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

## 9. Dependências e Integrações
- Módulo de notificações para envio de alertas financeiros.
- Provedores de pagamento externos via API.
- ...

## Anexos e Referências
- ...

## Changelog
- 1.1.0 — 2025-08-13 — Normalização para Padrão Unificado v3.1

