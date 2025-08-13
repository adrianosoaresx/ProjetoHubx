# Relatório de Análise do App Agenda

## Introdução

Este documento apresenta uma análise detalhada do aplicativo **Agenda** do projeto Hubx. O objetivo é verificar se as funcionalidades implementadas no código atendem aos requisitos especificados, identificar novos comportamentos não documentados e descrever os principais fluxos para orientar futuros usuários e desenvolvedores.

## Visão geral

O módulo Agenda é responsável por gerenciar eventos e todas as entidades relacionadas: inscrições de participantes, materiais de divulgação, parcerias/patrocínios, briefings, avaliações e tarefas. Além do CRUD básico de eventos, o app incorpora controle de orçamento, lista de espera com promoção automática, geração de QR codes para check‑in, workflow de aprovação de materiais, avaliação de parceiros e eventos, bem como um subsistema de tarefas e logs de auditoria. Todos os modelos herdam `TimeStampedModel` e `SoftDeleteModel`, garantindo controle de criação/modificação e exclusão lógica.

## Funcionalidades principais

### 1. Gestão de eventos

- **Criação e edição** – cada evento possui título, descrição, datas de início e fim, local, cidade, estado, CEP, capacidade máxima e público‑alvo. Campos extras incluem cronograma, informações adicionais, orçamento (real, estimado e gasto), valor do ingresso, nomes de contato, e‑mail, WhatsApp, imagens de avatar e capa e uma referência a uma mensagem do chat. Todos os campos são validados, por exemplo cidade/estado por regex e CEP no formato 00000-000【561401687002500†L171-L223】.
- **Orçamento** – campos `orcamento`, `orcamento_estimado` e `valor_gasto` permitem acompanhar previsões e gastos. Há uma API para leitura e atualização desses valores, restrita a administradores e coordenadores; mudanças são registradas em logs【410067135043595†L360-L377】.
- **Capacidade e lista de espera** – é possível definir `participantes_maximo` e habilitar `espera_habilitada`. Quando o limite é atingido, novas inscrições são marcadas como pendentes e recebem uma posição na fila【561401687002500†L97-L113】. Uma tarefa assíncrona promove pendentes quando há vagas【906211648821816†L11-L27】.
- **Avaliação** – o modelo disponibiliza método `calcular_media_feedback()` para calcular a média das notas dadas pelos participantes【561401687002500†L247-L249】.

### 2. Inscrições de usuários

Cada inscrição (`InscricaoEvento`) associa um usuário a um evento com campos para status (pendente, confirmada, cancelada), presença, valor pago, método de pagamento (Pix, boleto, gratuito ou outro)【561401687002500†L61-L74】, upload de comprovante, observação e data de confirmação. A inscrição guarda ainda um QR code para check‑in, data/hora em que o check‑in foi realizado e posição na lista de espera. Métodos de instância implementam a confirmação da inscrição (gerando QR code se necessário), cancelamento e registro de check‑in【561401687002500†L97-L121】. Avaliações (nota de 1 a 5 e feedback textual) podem ser armazenadas dentro da inscrição【561401687002500†L84-L90】.

### 3. Pagamentos

O app não realiza transações financeiras, mas registra informações sobre o pagamento de inscrições. O campo `metodo_pagamento` aceita Pix, boleto, inscrição gratuita ou outro meio, e `valor_pago` guarda o valor informado. O usuário pode anexar um comprovante de pagamento que será validado quanto ao formato e tamanho. Caso o evento seja gratuito, o sistema aceita o valor zero e marca o método como “gratuito”.

### 4. Check‑in via QR code

No momento da confirmação da inscrição, a aplicação gera um QR code único contendo o identificador da inscrição e o timestamp de criação e armazena a imagem no storage padrão【561401687002500†L148-L158】. A URL resultante é registrada em `qrcode_url`. Uma API específica permite validar o código enviado no dia do evento: se o código não corresponder ao formato esperado ou já tiver sido usado, a requisição é recusada; do contrário, a data/hora de check‑in é gravada【410067135043595†L411-L423】.

### 5. Materiais de divulgação

Para cada evento é possível enviar arquivos promocionais (banner, flyer, vídeo, PDF). Cada `MaterialDivulgacaoEvento` possui título, descrição, tipo, arquivo, miniatura opcional, data de publicação, tags e um status de aprovação (criado, aprovado ou devolvido). O status “criado” representa material aguardando revisão; “devolvido” inclui motivo de devolução e quem avaliou; “aprovado” torna o material visível a outros usuários【561401687002500†L317-L349】. O upload para o storage é realizado por tarefa assíncrona com tentativas automáticas em caso de falha【906211648821816†L29-L41】. O formulário de envio valida extensões (imagens, PDF) e tamanhos (10 MB para imagens, 20 MB para PDF) conforme a função de limpeza dos campos.

### 6. Parcerias e patrocínios

O modelo `ParceriaEvento` registra parcerias associadas a eventos, com campos para empresa, núcleo, CNPJ (validado como 14 dígitos), contato, representante legal, tipo de parceria (patrocínio, mentoria, mantenedor ou outro), contrato em arquivo, período de vigência e descrição. Após a conclusão da parceria, administradores ou coordenadores podem avaliar a parceria atribuindo nota de 1 a 5 e comentário, via endpoint específico【410067135043595†L390-L409】. Logs registram alterações e exclusões de parcerias.

### 7. Briefing de eventos

Cada evento pode ter um briefing que detalha objetivos, público‑alvo, requisitos técnicos, cronograma resumido, conteúdo programático e observações. O briefing inicia em estado rascunho e pode transitar para orçamentado, aprovado ou recusado. A ação de orçamento registra a data de envio e prazo limite de resposta; aprovação marca o briefing como finalizado; recusa registra data, motivo e usuário responsável. Um endpoint permite alterar o status e uma tarefa assíncrona notifica os envolvidos【410067135043595†L687-L725】.

### 8. Avaliação de eventos

Além da avaliação opcional armazenada na própria inscrição, existe um modelo dedicado `FeedbackNota` que relaciona evento e usuário, permitindo guardar uma nota (1 a 5), comentário e data de feedback. O endpoint de feedback verifica se o usuário está inscrito e se o evento já terminou; cada usuário pode avaliar um evento uma única vez【410067135043595†L310-L351】.

### 9. Tarefas e logs

O app oferece um modelo `Tarefa` para registrar tarefas simples associadas a eventos ou a mensagens do chat. Cada tarefa possui título, descrição, datas de início/fim, responsável, organização, núcleo e status (pendente ou concluída). As tarefas são listadas e podem ser visualizadas por usuários autorizados. Modelos `TarefaLog` e `EventoLog` registram quaisquer alterações, criações ou exclusões nas tarefas e eventos, armazenando a ação realizada e detalhes relevantes【561401687002500†L430-L457】【561401687002500†L472-L504】.

## Fluxos principais

### Inscrição e lista de espera

1. Um usuário autenticado solicita inscrição em um evento. O sistema verifica se o usuário já está inscrito; caso contrário, cria o registro e define o status como confirmado ou pendente.  
2. Se o número de participantes confirmados atingir o valor máximo (`participantes_maximo`), a inscrição torna‑se pendente e recebe `posicao_espera` calculada como último valor + 1【561401687002500†L97-L113】.  
3. Quando houver novas vagas (por cancelamento ou aumento de capacidade), uma tarefa Celery promove automaticamente as inscrições pendentes de acordo com a ordem da lista de espera, marcando-as como confirmadas e removendo a posição de espera【906211648821816†L11-L27】.

### Check‑in com QR code

1. Ao confirmar uma inscrição, o método `confirmar_inscricao()` gera um QR code contendo `inscricao:<pk>:<timestamp>` e o salva em `qrcode_url`【561401687002500†L148-L158】.  
2. No dia do evento, o participante apresenta o QR code; a API `checkin_inscricao` valida o código e registra `check_in_realizado_em`【410067135043595†L411-L423】.  
3. Um QR code reutilizado ou inválido retorna erro de acesso.

### Aprovação de material de divulgação

1. Usuário autorizado faz upload de um arquivo e, opcionalmente, uma miniatura. O sistema valida extensão e tamanho e envia o arquivo para o storage em segundo plano【906211648821816†L29-L41】.  
2. Materiais ficam com status “criado”.  
3. Um administrador ou coordenador lista os materiais pendentes e decide aprovar ou devolver. Ao devolver, deve registrar o motivo e a data; ao aprovar, muda o status para “aprovado”【561401687002500†L317-L349】.

### Gerenciamento de parcerias

1. Administrador ou coordenador cria uma parceria para um evento, informando dados obrigatórios (empresa, CNPJ, tipo, contrato, vigência).  
2. O sistema valida e salva; alterações futuras são registradas em logs.  
3. Após a prestação de serviços ou realização do evento, o responsável pode avaliar a parceria uma única vez com nota e comentário【410067135043595†L390-L409】.

### Fluxo de briefing

1. Coordenador cria um briefing em estado rascunho com objetivo, público‑alvo e requisitos técnicos.  
2. Um administrador analisa e altera o status: “orcamentado” define prazo de resposta e data de envio; “aprovado” finaliza o processo; “recusado” registra motivo e data【410067135043595†L687-L725】.  
3. Em cada transição, o sistema grava logs e envia notificações assíncronas.

### Avaliação de eventos

1. Após o término do evento (`data_fim` passada), participantes confirmados podem enviar nota de 1 a 5 e comentário. A vista `EventoFeedbackView` valida se o evento terminou e se o usuário possui inscrição confirmada【410067135043595†L310-L351】.  
2. A nota e o comentário são salvos em `FeedbackNota` (ou `InscricaoEvento.avaliacao`); uma entrada de log registra a ação e a nota.  
3. O método do modelo de evento recalcula a média das avaliações.

### Tarefas e logs

1. Usuários autorizados podem criar tarefas associadas a eventos ou mensagens do chat. A tarefa mantém estado (pendente/concluída) e registra data de início e fim【561401687002500†L430-L457】.  
2. Cada criação, atualização de status ou exclusão de tarefa gera uma entrada em `TarefaLog` com detalhes da ação【561401687002500†L472-L504】.  
3. Da mesma forma, alterações em eventos (criação, edição, exclusão, mudanças de orçamento, confirmação de inscrição, check‑in, alteração de presença) geram logs em `EventoLog`, permitindo auditoria completa.

## Resultado da comparação de requisitos

O código do app Agenda implementa todos os requisitos definidos na versão 1.0 do documento de requisitos, incluindo CRUD de eventos, inscrições com presença e avaliação, upload de materiais, parcerias e fluxo de briefing. Além disso, foram identificadas funcionalidades adicionais que não estavam originalmente documentadas:

1. **Pagamentos e comprovantes** – o modelo de inscrição aceita diferentes métodos de pagamento (Pix, boleto, gratuito, outro), registra valor pago e armazena comprovantes de pagamento【561401687002500†L61-L79】.  
2. **Geração de QR code e check‑in** – o sistema gera um QR code único para cada inscrição confirmada e possui endpoint para validar e registrar o check‑in【561401687002500†L148-L158】【410067135043595†L411-L423】.  
3. **Capacidade e lista de espera** – é possível definir número máximo de participantes e habilitar uma lista de espera automática; tarefas Celery promovem inscritos pendentes quando há vagas【561401687002500†L97-L113】【906211648821816†L11-L27】.  
4. **Materiais com workflow de aprovação** – cada material possui status e campos de avaliação, incluindo quem avaliou, quando e motivo de devolução【561401687002500†L317-L349】.  
5. **Campos e validações adicionais nos modelos** – eventos incluem campos de cidade, estado, CEP, orçamentos, participantes máximos, cronograma, informações adicionais e contatos; parcerias têm contrato em arquivo e vigência; briefings guardam prazos e estados detalhados; esses campos não estavam listados no documento original【561401687002500†L171-L223】【561401687002500†L275-L307】【561401687002500†L361-L399】.  
6. **Sistema de tarefas e logs** – implementação de tarefas relacionadas a eventos e logs de auditoria para todas as operações relevantes【561401687002500†L430-L457】【561401687002500†L472-L504】.  
7. **Processamento assíncrono** – uso de tarefas Celery para upload de materiais, promoção da lista de espera e envio de notificações, garantindo resiliência a falhas【906211648821816†L11-L27】【906211648821816†L29-L41】.

Essas funcionalidades foram incorporadas na versão 1.1 do documento de requisitos, com novos requisitos funcionais (RF‑03, RF‑10, RF‑11) e não funcionais (RNF‑07, RNF‑08) específicos para QR codes, lista de espera, aprovação de materiais e logs de orçamento. Assim, o documento atualizado reflete fielmente o comportamento atual do app.

## Conclusão

O app Agenda oferece um conjunto robusto de funcionalidades para organizar eventos, gerir inscrições e pagamentos, aprovar materiais, manter parcerias, produzir briefings e administrar tarefas. O código está bem alinhado com os requisitos originais e adiciona recursos úteis, como controle de orçamento, lista de espera com promoção automática, check‑in via QR code e auditoria abrangente. O novo documento de requisitos (versão 1.1) formaliza esses acréscimos e garante que as equipes de desenvolvimento e usuários tenham uma visão clara das capacidades e fluxos do sistema.
