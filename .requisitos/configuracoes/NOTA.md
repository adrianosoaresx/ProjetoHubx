# Relatório de Análise do App Configurações

## Visão Geral

O aplicativo **Configurações** (ou Configuracoes_Conta) do Projeto Hubx permite que cada usuário personalize as preferências de notificação e aparência da interface. Ele oferece também a possibilidade de definir configurações específicas por escopo (organização, núcleo ou evento) e implementa um mecanismo de envio de notificações resumidas baseadas em frequência. O código utiliza o framework Django com modelos extensivos, serviços para cache e resolução de preferências, formulários com validações, API REST, tarefas assíncronas e integração com serviços de notificação como Twilio.

## Principais Funcionalidades Implementadas

### Configurações de Conta

* **Notificações por canal** – A classe `ConfiguracaoConta` associa um usuário a um conjunto de preferências. Além de opções para habilitar ou desabilitar notificações por e‑mail e WhatsApp (conforme exigido no requisito original), o modelo inclui campos para ativar ou desativar notificações **push** e para definir a frequência de cada canal (`imediata`, `diaria` ou `semanal`)【74186655470974†L44-L61】.  
* **Aparência e idioma** – O modelo armazena o idioma (`idioma`) e o tema da interface (`tema`), com opções `claro`, `escuro` ou `automatico`【74186655470974†L62-L65】.
* **Horário e dia das notificações** – Novos campos permitem escolher o horário para envio de notificações diárias (`hora_notificacao_diaria`) e o horário e dia da semana para notificações semanais (`hora_notificacao_semanal` e `dia_semana_notificacao`)【74186655470974†L66-L77】.
* **Exclusão lógica e unicidade** – O modelo herda de `TimeStampedModel` e `SoftDeleteModel`; uma restrição de unicidade garante uma configuração por usuário【74186655470974†L80-L86】.

### Configurações Contextuais

* O modelo `ConfiguracaoContextual` permite que um usuário defina preferências específicas para um determinado escopo (`organizacao`, `nucleo` ou `evento`). Cada registro inclui o tipo e o ID do escopo, as frequências de notificações por e‑mail e WhatsApp, o idioma e o tema【74186655470974†L88-L116】. Uma restrição `unique_together` garante que não existam configurações duplicadas para o mesmo usuário e escopo【74186655470974†L120-L127】.

### Logs de Configurações

* O modelo `ConfiguracaoContaLog` registra alterações nas preferências: campo alterado, valor antigo, valor novo, IP e user‑agent, e origem da modificação (UI, API ou import)【74186655470974†L129-L145】.  Esse mecanismo fornece rastreabilidade e auditoria das alterações de configuração.

### Serviços e Cache

* A função `get_configuracao_conta` busca a configuração de um usuário a partir de um cache (chave baseada no ID). Se não houver registro, ele é criado; se existir e estiver marcado como deletado, o registro é restaurado【498180863719394†L16-L33】. A função registra métricas de hits e misses e latência de leitura【498180863719394†L16-L41】.
* A função `get_user_preferences` resolve as preferências do usuário para um escopo específico: clona a configuração global e, se houver configuração contextual, substitui frequências de email/WhatsApp, idioma e tema pela configuração desse escopo【498180863719394†L54-L69】.
* `atualizar_preferencias_usuario` aplica alterações às configurações, salva e atualiza o cache【498180863719394†L72-L81】.

### Formulário e Validações

O `ConfiguracaoContaForm` expõe todos os campos de `ConfiguracaoConta`, incluindo os de push, horários e idioma. O método `clean()` garante que horários e dia da semana sejam fornecidos quando a frequência diária ou semanal está ativada para qualquer canal; também mantém as frequências anteriores se a notificação for desativada【184069624769776†L61-L104】.

### API REST

* O `ConfiguracaoContaViewSet` oferece operações de leitura (`retrieve`), atualização (`update`) e atualização parcial (`partial_update`) das preferências via Django REST Framework. Cada chamada é metrificada para latência. O serializer utiliza o modelo completo com campos adicionais, refletindo push, idioma e horários【96271031922130†L22-L73】.
* A `TestarNotificacaoView` permite que o usuário teste o envio de notificações em um canal específico (email, WhatsApp ou push). Ela resolve as preferências de contexto, verifica se o canal está ativo e utiliza `NotificationTemplate` e `enviar_para_usuario` para disparar a mensagem. Este recurso não está descrito nos requisitos originais【96271031922130†L104-L131】.

### Tarefas Assíncronas

O módulo `configuracoes.tasks` implementa um sistema de envio de resumos por e‑mail ou WhatsApp com frequência diária ou semanal:

* `_send_for_frequency()` filtra usuários que desejam receber notificações na frequência especificada, considerando o horário e o dia configurados. Ele agrega contagens de itens pendentes (notificações de chat não lidas, novos posts no feed e novos eventos) e envia um resumo por e‑mail ou WhatsApp, conforme habilitado【449563910561256†L22-L63】.  
* `enviar_notificacoes_diarias` e `enviar_notificacoes_semanais` são tarefas Celery que chamam `_send_for_frequency()` para as frequências “diaria” e “semanal” respectivamente【449563910561256†L83-L89】.  
* A função auxiliar `enviar_notificacao_whatsapp` usa o SDK do Twilio para enviar mensagens via WhatsApp, utilizando credenciais definidas em variáveis de ambiente【449563910561256†L65-L79】.

## Comparação com o Documento de Requisitos (v 1.0)

### Requisitos Atendidos

* **RF‑01, RF‑02 (notificações por email/WhatsApp)** – Implementados conforme a especificação. O código possui campos booleanos para habilitar cada canal【74186655470974†L44-L55】.
* **RF‑03 (alternar tema claro/escuro)** – Atendido; o campo `tema` inclui opções `claro` e `escuro`【74186655470974†L62-L65】.
* **RF‑04 (criação automática de configuração)** – Satisfeito: `get_configuracao_conta` cria uma configuração caso ela não exista【498180863719394†L16-L33】.
* **RF‑05‑RF‑07 (frequência de notificações, idioma, tema automático)** – Atendido e expandido: o modelo contém campos de frequência para email e WhatsApp, idioma (`pt-BR`, `en-US`, `es-ES`) e tema automático【74186655470974†L44-L65】.

### Funcionalidades Adicionais Encontradas

1. **Notificações Push** – Novo canal de notificação (`receber_notificacoes_push`) com frequência configurável (`frequencia_notificacoes_push`)【74186655470974†L56-L61】. Esta funcionalidade não consta nos requisitos originais e foi incluída como RF adicional.
2. **Horários Personalizados e Dia da Semana** – O usuário define a hora de envio para notificações diárias e semanais (`hora_notificacao_diaria`, `hora_notificacao_semanal`) e escolhe o dia da semana para notificações semanais (`dia_semana_notificacao`)【74186655470974†L66-L77】. Não especificado originalmente.
3. **Configurações Contextuais** – Preferências específicas por escopo (organização, núcleo ou evento) em `ConfiguracaoContextual`, sobrescrevendo frequências, idioma e tema【74186655470974†L88-L116】.
4. **Logs de Alterações** – `ConfiguracaoContaLog` registra todas as mudanças de preferências incluindo IP, user‑agent e fonte (UI/API/import)【74186655470974†L129-L145】.
5. **Cache e Métricas de Leitura** – Serviço de cache para reduzir tempo de acesso às configurações, com contadores de hits/misses e medição de latência【498180863719394†L16-L41】.
6. **Integração com Notificações e Twilio** – Tarefas que enviam resumos periódicos e função para enviar via WhatsApp usando Twilio【449563910561256†L22-L79】.
7. **Formulário Completo e Validações** – Formulário `ConfiguracaoContaForm` engloba todos os campos e valida a necessidade de horários quando as frequências são diárias ou semanais【184069624769776†L61-L104】.
8. **API de Teste de Notificação** – Endpoint que permite ao usuário disparar uma mensagem de teste verificando se o canal está habilitado【96271031922130†L104-L115】. Não contemplado no documento original.

### Pontos Não Encontrados ou Divergências

* O documento menciona campos `tema_escuro` e `ConfiguracoesConta` com `receber_notificacoes_email`, `receber_notificacoes_whatsapp` e `tema_escuro`【143376793063504†L102-L107】; no código, esse modelo foi renomeado para `ConfiguracaoConta` e o campo `tema_escuro` foi substituído por `tema` com opções claro/escuro/automático【74186655470974†L62-L65】.
* Não há menção a **Agendamento de resumo** ou **configurações contextuais** no requisito v1.0. A implementação adiciona esses recursos.

## Considerações e Recomendações

O módulo de Configurações do Hubx evoluiu de um simples gerenciador de preferências para uma solução sofisticada com suporte a múltiplos canais, frequências personalizadas, horários e escopos específicos. Para refletir essas mudanças, recomenda‑se atualizar o documento de requisitos para a **versão 1.1**, incorporando os novos requisitos funcionais e não‑funcionais:

* Incluir a capacidade de configurar notificações push e frequências associadas.
* Permitir a definição de horários e dia da semana para disparo de notificações agregadas.
* Descrever o modelo `ConfiguracaoContextual` e como ele sobrepõe as configurações globais.
* Documentar o log de alterações (`ConfiguracaoContaLog`) e sua utilidade para auditoria.
* Detalhar as tarefas assíncronas de envio de resumos e o uso do Twilio para WhatsApp.
* Mencionar a API de teste de notificações como ferramenta de verificação pelo usuário.

Atualizar o requisito trará maior transparência e alinhamento entre documentação e código. Também será útil garantir que métricas de desempenho (cache, API) e logs sejam monitorados conforme as boas práticas de observabilidade.