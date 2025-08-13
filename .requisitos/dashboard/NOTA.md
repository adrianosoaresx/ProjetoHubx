# Relatório de Análise do App Dashboard

## Visão geral

O módulo **dashboard** do Hubx.Space oferece visualizações dinâmicas de métricas e estatísticas para diferentes perfis de usuário.  A arquitetura baseia‑se em uma `DashboardBaseView` que filtra dados por período (mensal, trimestral, semestral ou anual), escopo (global, organização, núcleo ou evento) e filtros adicionais (datas, organização, núcleo ou evento), e utiliza um serviço para calcular métricas agregadas.  As views derivadas (root, admin, gerente, cliente) herdam este comportamento, aplicando templates e verificações de permissão.

## Comparação entre requisitos e código

### Requisitos implementados

- **RF‑01 – Aceitar parâmetros** \(versão 1.1): A `DashboardBaseView.get_metrics()` extrai `periodo`, `escopo`, `data_inicio`, `data_fim` e filtros de organização/núcleo/evento e passa para o serviço de métricas【787689370844584†L104-L143】.  Isso atende ao requisito de receber parâmetros via `request.GET`.
- **RF‑02 – Função `get_metrics()` parametrizável**: a view invoca `DashboardMetricsService.get_metrics()` com os parâmetros, retornando um dicionário com métricas e crescimento【787689370844584†L104-L143】.
- **RF‑03 – Calcular variação percentual**: a função `get_variation()` em `dashboard/utils.py` implementa a fórmula solicitada, protegendo contra divisão por zero ao usar 1 como denominador mínimo【79069676018619†L2-L4】.  As métricas retornadas incluem o campo `crescimento`.
- **RF‑04 – Redirecionamento inteligente**: a função `dashboard_redirect` redireciona o usuário conforme seu tipo (root, admin, coordenador ou cliente)【787689370844584†L194-L206】.
- **RF‑05 – Métricas de inscrições confirmadas e lançamentos pendentes**: o serviço `DashboardMetricsService` inclui métricas `inscricoes_confirmadas` e `lancamentos_pendentes` no mapa de consultas【568506279805381†L600-L612】.  Embora não estejam listadas no dicionário `METRICAS_INFO`, estão disponíveis para uso e podem ser selecionadas via parâmetro `metricas`.
- **RF‑06 – Criar múltiplos dashboards**: existem modelos `DashboardConfig` e `DashboardFilter` para salvar configurações e filtros em JSON, com views para criação, listagem, aplicação e exclusão.  Apenas admins/root podem tornar públicos filtros e configurações (ver validação em `clean()` dos modelos)【296492142424983†L12-L30】.
- **RF‑07 – Integração com Agenda e Financeiro**: o serviço de métricas integra dados de eventos e inscrições do módulo Agenda e lançamentos financeiros pendentes do módulo Financeiro【568506279805381†L600-L612】.  Outras métricas incluem posts de feed, mensagens de chat, tópicos de discussão e tokens consumidos.
- **RF‑09 – Log de ações**: as operações de exportação e criação de configurações ou filtros registram logs de auditoria via `log_audit`, incluindo IP anoniminizado【787689370844584†L354-L423】.
- **RNF – Uso de `TimeStampedModel` e `SoftDeleteModel`**: todos os modelos (`DashboardFilter`, `DashboardConfig`, `DashboardLayout`) herdam desses mixins, garantindo timestamps automáticos e exclusão lógica【296492142424983†L12-L40】.
- **RNF – Cache de métricas**: `DashboardMetricsService.get_metrics()` utiliza cache do Django, gerando chaves que incluem período, datas e filtros; os resultados são armazenados por 5 minutos【568506279805381†L494-L521】.  Este comportamento atende ao requisito não‑funcional de cache com invalidação periódica.
- **RNF – Internacionalização**: as labels das métricas e mensagens de interface usam `gettext_lazy`, permitindo tradução para português e inglês【787689370844584†L55-L76】.

### Funcionalidades adicionais não previstas

1. **Conquistas e gamificação** – Foram adicionadas entidades `Achievement` e `UserAchievement` para registrar conquistas de usuários, como criar cinco dashboards ou realizar cem inscrições.  A função `check_achievements` verifica condições e cria registros de conquistas【568506279805381†L767-L791】, e uma view `AchievementListView` permite que usuários visualizem conquistas obtidas【787689370844584†L457-L468】.
2. **Layouts personalizados** – O modelo `DashboardLayout` permite salvar e compartilhar layouts de dashboards em JSON, com views para criar, editar, excluir e salvar layouts【296492142424983†L81-L100】【787689370844584†L618-L681】.  Isso fornece flexibilidade na disposição de gráficos e métricas.
3. **Exportação ampliada** – A `DashboardExportView` oferece exportação de métricas em CSV, PDF, XLSX e PNG.  Além das exportações definidas nos requisitos, o código gera planilhas Excel e gráficos em PNG utilizando Matplotlib【787689370844584†L354-L423】.
4. **Listas parciais (HTMX)** – A aplicação oferece endpoints para renderizar trechos de interface via HTMX: métricas selecionadas, últimos lançamentos financeiros, últimas notificações, tarefas pendentes e próximos eventos【787689370844584†L208-L313】.  Esses métodos retornam HTML parcial e não utilizam WebSockets; as atualizações em tempo real são baseadas em requisições assíncronas.
5. **Filtro de métricas** – Usuários podem passar parâmetros `metricas` para limitar quais métricas são calculadas e exibidas【787689370844584†L120-L129】.  Isso permite dashboards sob medida e melhora o desempenho.
6. **Campos e permissões adicionais** – Os modelos verificam se apenas usuários `ROOT` ou `ADMIN` podem tornar filtros ou configurações públicas【296492142424983†L25-L31】; list views exibem filtros/layouts públicos pertencentes à organização; e a aplicação impede acesso a configurações ou filtros de outros usuários, exceto quando públicos【787689370844584†L526-L607】.

### Pontos ausentes

- **Atualizações via WebSocket** – O requisito RF‑08 menciona atualizações em tempo real via WebSocket, mas o código utiliza HTMX para requisições parciais.  Não há consumidores WebSocket no app `dashboard`, portanto essa capacidade não foi implementada.  Se necessário, deverá ser desenvolvida via Django Channels ou outro serviço de tempo real.
- **Inclusão das métricas de inscrições e lançamentos no UI** – Embora `inscricoes_confirmadas` e `lancamentos_pendentes` sejam calculadas, elas não aparecem no dicionário `METRICAS_INFO` usado na interface.  Para exibi‑las na UI, seria preciso adicionar labels e ícones correspondentes.

## Funcionalidades e fluxos

- **Cálculo de métricas**: A `DashboardBaseView` extrai parâmetros de período, escopo e filtros do `request.GET` e invoca `DashboardMetricsService.get_metrics()`, que calcula métricas de usuários, organizações, núcleos, eventos, posts de feed, mensagens de chat, tópicos, respostas, inscrições confirmadas, lançamentos pendentes e outras, aplicando filtros de organização/núcleo/evento e escopo de acesso【787689370844584†L104-L143】【568506279805381†L524-L556】.  Os resultados são cacheados por cinco minutos【568506279805381†L494-L521】 e incluem total e variação percentual.
- **Exibição de dashboards**: As views `RootDashboardView`, `AdminDashboardView`, `GerenteDashboardView` e `ClienteDashboardView` renderizam templates diferentes e preenchem o contexto com métricas, período selecionado, escopo e filtros.  A view `RootDashboardView` inclui métricas de disco e fila de tarefas para superadmins【787689370844584†L170-L183】.
- **Dashboards salvos e filtros**: Usuários podem criar e listar `DashboardConfig` e `DashboardFilter`.  Ao salvar, são armazenados os parâmetros de período, escopo, datas e filtros selecionados.  Filtros e configurações podem ser públicos, permitindo compartilhamento.  As views verificam permissões antes de aplicar ou excluir itens【787689370844584†L526-L607】.
- **Layouts personalizados**: `DashboardLayout` armazena um JSON representando a posição e tamanho dos widgets no dashboard.  Há views para criar, listar, atualizar, excluir e salvar layouts, respeitando permissões de acesso【787689370844584†L618-L681】.
- **Exportação de métricas**: `DashboardExportView` permite exportar as métricas do período filtrado em CSV (padrão), PDF, XLSX ou PNG.  Para PDF, utiliza WeasyPrint; para XLSX, usa openpyxl; para PNG, gera um gráfico de barras com Matplotlib e salva em um diretório de exportações.  Cada exportação registra um log de auditoria com ação, formato e parâmetros【787689370844584†L354-L423】.
- **Conquistas**: O serviço `check_achievements()` avalia se o usuário atingiu marcos como “100 inscrições” ou “5 dashboards criados” e cria um registro `UserAchievement` quando necessário【568506279805381†L767-L791】.  A view `AchievementListView` exibe uma lista de conquistas disponíveis, indicando quais foram obtidas pelo usuário【787689370844584†L457-L468】.
- **Parciais HTMX**: Funções como `metrics_partial`, `lancamentos_partial`, `notificacoes_partial`, `tarefas_partial` e `eventos_partial` retornam HTML com listas de métricas, lançamentos financeiros, notificações recentes, tarefas pendentes e próximos eventos para inserção dinâmica na página via HTMX【787689370844584†L208-L313】.

## Observações finais

O app dashboard está robusto e bem estruturado, indo além dos requisitos originais ao oferecer gamificação (conquistas), layouts customizados e múltiplos formatos de exportação.  No entanto, a ausência de consumidores WebSocket significa que as atualizações em tempo real são simuladas via requisições assíncronas; se a necessidade de tempo real for crítica, recomenda‑se implementar WebSocket com Django Channels.  As novas funcionalidades foram incorporadas no documento de requisitos atualizado (versão 1.2), garantindo alinhamento entre especificação e implementação.
