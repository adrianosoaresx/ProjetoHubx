---
id: REQ-AGENDA-001
title: Requisitos Agenda Hubx
module: Agenda
status: Em vigor
version: '1.1'
authors: []
created: '2025-07-25'
updated: '2025-08-12'
---

## 1. Visão Geral

O App **Agenda** do Hubx administra todo o ciclo de vida de eventos e as suas relações com participantes, parceiros, materiais de divulgação e fluxos de briefing. Ele vai além do CRUD básico de eventos, implementando controle de inscrições com pagamentos e lista de espera, geração de QR codes para check‑in, upload e aprovação de materiais, avaliação de eventos e parcerias, gerenciamento de orçamentos e tarefas associadas.

Principais destaques:

- **Inscrições avançadas** – o app permite que um usuário se inscreva em um evento, informe o método de pagamento (Pix, boleto, gratuito ou outro) e envie comprovantes. A inscrição gerencia o status (pendente, confirmada, cancelada), calcula a posição na lista de espera quando o número máximo de participantes é atingido e gera um QR code único para check‑in【561401687002500†L97-L121】【561401687002500†L148-L158】.
- **Controle orçamentário e limite de público** – cada evento possui campos para orçamento inicial, orçamento estimado e valor gasto. É possível definir o máximo de participantes e habilitar lista de espera; o sistema promove automaticamente pessoas da lista quando surgem vagas【906211648821816†L11-L27】.
- **Materiais de divulgação com workflow** – além de guardar arquivos (banners, flyers, vídeos, PDFs) e imagens em miniatura, o módulo oferece status de aprovação (criado, aprovado ou devolvido), permite registrar quem avaliou o material e o motivo de devolução【561401687002500†L317-L349】. O upload para o storage é realizado de forma assíncrona com retentativas em caso de falha【906211648821816†L29-L41】.
- **Parcerias e patrocínios** – é possível cadastrar parcerias com empresas, incluindo CNPJ, contato, representante legal, contrato em arquivo e período de vigência. Parcerias podem ser avaliadas com notas de 1 a 5 e comentários【561401687002500†L275-L307】.
- **Fluxo de briefing** – coordenadores podem criar briefs com objetivos, público‑alvo e requisitos técnicos. O briefing percorre estados rascunho → orçamentado → aprovado/recusado; cada transição grava logs, notifica interessados e registra prazos, avaliações e motivos de recusa【410067135043595†L687-L725】.
- **Avaliação de eventos** – participantes confirmados podem avaliar o evento de 1 a 5 e deixar comentário após o término. As notas são gravadas em uma tabela própria e o evento fornece método para calcular a média de feedbacks【410067135043595†L310-L351】.
- **Tarefas e logs** – há um modelo para tarefas vinculadas a mensagens do chat (titulo, descrição, datas, responsável e status) e logs que registram alterações em eventos, inscrições, parcerias, briefings e tarefas. Todas as entidades herdam `TimeStampedModel` e `SoftDeleteModel`, garantindo marcação de criação/modificação e exclusão lógica【561401687002500†L430-L457】【561401687002500†L472-L504】.

## 2. Escopo

- **Inclui**:
  - CRUD de eventos, com campos de localização (cidade, estado, CEP), cronograma, informações adicionais e contato (nome, e‑mail, WhatsApp)【561401687002500†L171-L223】.
  - Gestão de inscrições de usuários: registro de presença, cancelamento, lista de espera, geração de QR code para check‑in e controle de pagamento (método, valor pago e comprovante)【561401687002500†L61-L79】【561401687002500†L97-L121】.
  - Gestão de orçamentos e despesas do evento: campos `orcamento`, `orcamento_estimado` e `valor_gasto`, com API para consulta e atualização por coordenadores【410067135043595†L360-L377】.
  - Upload e gerenciamento de materiais de divulgação (imagens, vídeos, PDFs), com miniatura opcional, tags, status de aprovação e registro de avaliador e motivo de devolução【561401687002500†L317-L349】.
  - Cadastro e avaliação de parcerias e patrocínios de eventos, incluindo CNPJ, contrato, data de início/fim e notas de avaliação【561401687002500†L275-L307】.
  - Fluxo de briefing de eventos (criação, orçamento, aprovação, recusa), com controle de prazos, histórico de avaliações e notificações automáticas【410067135043595†L687-L725】.
  - Avaliação de eventos pelos participantes após conclusão (notas de 1 a 5, comentário)【410067135043595†L310-L351】.
  - Gestão de tarefas relacionadas a eventos (criação, visualização e registro de logs)【561401687002500†L430-L457】.
  - Auditoria completa com logs para eventos, inscrições, parcerias, briefings e tarefas【561401687002500†L472-L504】.
  - Processos assíncronos para promover lista de espera, enviar notificações e fazer upload de arquivos【906211648821816†L11-L27】【906211648821816†L29-L41】.
- **Exclui**:
  - Comunicação em tempo real (delegada ao App Chat).  
  - Gestão de contas, organizações ou núcleos (delegada aos Apps Accounts, Organizações e Núcleos).  
  - Cobrança de ingressos e integração com gateways de pagamento externos (apenas coleta e registro de valor pago e comprovante).

## 3. Requisitos Funcionais

- **RF‑01 – Gerenciar eventos**  
  - Descrição: Criar, listar, editar e excluir eventos, incluindo informações de local, cronograma, público‑alvo, capacidade, imagens e contatos.  
  - Critérios de Aceite: Campos validados (CEP, UF, cidade alfabética)【561401687002500†L171-L223】; somente usuários autorizados podem alterar ou excluir.  

- **RF‑02 – Gerenciar inscrições de usuários**  
  - Descrição: Inscrever usuários em eventos com possibilidade de selecionar método de pagamento e enviar comprovante; cancelar inscrição; registrar presença e avaliação.  
  - Critérios de Aceite: Um usuário não pode ter mais de uma inscrição para o mesmo evento; inscrição fica pendente se a capacidade estiver esgotada, alocando posição na lista de espera【561401687002500†L97-L113】; envio de comprovantes aceita formatos .jpg, .png e PDF; cancelamento disponível antes do evento; avaliação (1–5) e feedback apenas após o término【410067135043595†L310-L351】.

- **RF‑03 – Gerar QR Code para check‑in**  
  - Descrição: Gerar QR code exclusivo para cada inscrição confirmada e permitir check‑in via API.  
  - Critérios de Aceite: QR code contém identificador de inscrição e timestamp, é salvo no storage padrão e associado a `qrcode_url`【561401687002500†L117-L120】【561401687002500†L148-L158】; check‑in apenas uma vez por inscrição e invalida o código【410067135043595†L411-L423】.

- **RF‑04 – Gerenciar materiais de divulgação**  
  - Descrição: Upload, listagem, edição e exclusão de materiais de divulgação; aprovação ou devolução de materiais por administradores/coordenadores.  
  - Critérios de Aceite: Suporte a formatos de arquivo (imagem, vídeo, PDF), com tamanho máximo validado; miniatura opcional com tamanho máximo de 10 MB; status inicia em ‘criado’ e pode ser alterado para ‘aprovado’ ou ‘devolvido’ com registro de avaliador e motivo【561401687002500†L317-L349】; upload é efetuado de forma assíncrona com retentativas em caso de falha【906211648821816†L29-L41】.

- **RF‑05 – Gerenciar parcerias e patrocínios**  
  - Descrição: Criar, editar, excluir e listar parcerias de eventos; registrar dados de empresa, CNPJ, contato, representante legal, tipo de parceria, contrato e vigência.  
  - Critérios de Aceite: Campos obrigatórios validados (CNPJ numérico, datas coerentes); apenas administradores e coordenadores podem gerenciar; notas de avaliação (1–5) e comentário podem ser registradas uma única vez por parceria【410067135043595†L390-L409】【561401687002500†L275-L307】.

- **RF‑06 – Gerenciar briefing de eventos**  
  - Descrição: Criar e editar briefing com objetivos, público‑alvo, requisitos técnicos e cronograma resumido; transicionar status para orçamentado, aprovado ou recusado.  
  - Critérios de Aceite: Apenas um briefing ativo por evento; transições seguem fluxo rascunho → orçamentado → aprovado/recusado; administrador ou coordenador pode aprovar ou recusar; sistema registra avaliador, timestamps e motivo de recusa, envia notificação e atualiza prazo de resposta【410067135043595†L687-L725】.

- **RF‑07 – Avaliar eventos**  
  - Descrição: Permitir que participantes confirmados avaliem um evento após a sua conclusão, registrando nota de 1 a 5 e comentário opcional.  
  - Critérios de Aceite: Avaliação gravada apenas se o usuário estiver inscrito e o evento tiver terminado【410067135043595†L310-L351】; evento calcula média das avaliações【561401687002500†L247-L249】.

- **RF‑08 – Registrar e controlar orçamento do evento**  
  - Descrição: Armazenar e atualizar valores de orçamento inicial, orçamento estimado e valor gasto; expor API para consultar e alterar orçamentos.  
  - Critérios de Aceite: Somente administradores e coordenadores podem alterar valores; alterações são validadas como números decimais e registradas em logs【410067135043595†L360-L377】.

- **RF‑09 – Definir capacidade e gerenciar lista de espera**  
  - Descrição: Definir número máximo de participantes e habilitar lista de espera; promover inscrições pendentes quando houver vagas.  
  - Critérios de Aceite: Campos `participantes_maximo` e `espera_habilitada` configuráveis; sistema calcula posição de espera ao confirmar inscrição【561401687002500†L97-L113】; tarefa assíncrona promove inscrições pendentes quando surgem vagas【906211648821816†L11-L27】; API expõe lista de espera ordenada por posição【410067135043595†L379-L387】.

- **RF‑10 – Gerenciar tarefas de evento**  
  - Descrição: Criar e visualizar tarefas associadas a eventos ou mensagens do chat, incluindo título, descrição, datas de início/fim, responsável e status (pendente/concluída).  
  - Critérios de Aceite: Apenas usuários autorizados podem criar tarefas; logs registram alterações e conclusões【561401687002500†L430-L457】【561401687002500†L472-L504】.

- **RF‑11 – Registrar avaliação de parcerias**  
  - Descrição: Permitir que administradores ou coordenadores avaliem uma parceria uma única vez, atribuindo nota (1–5) e comentário.  
  - Critérios de Aceite: Avaliação gravada via API específica; campos validados; operação proibida se já houver avaliação【410067135043595†L390-L409】.

## 4. Requisitos Não‑Funcionais

- **RNF‑01 – Desempenho**: Listagens de eventos, inscrições e materiais devem apresentar p95 ≤ 300 ms.  
- **RNF‑02 – Confiabilidade**: Upload de mídia resiliente a falhas de rede, com até 3 retentativas automáticas【906211648821816†L29-L41】.  
- **RNF‑03 – Segurança**: Validação de permissões por escopo (organização e núcleo) e restrição de ações a administradores e coordenadores.  
- **RNF‑04 – Auditoria**: Todas as ações de criação, edição, exclusão e transições de status em eventos, inscrições, parcerias, briefings e tarefas devem ser registradas em logs【561401687002500†L472-L504】.  
- **RNF‑05 – Modelagem**: Todos os modelos deste app devem herdar de `TimeStampedModel` para timestamps automáticos e `SoftDeleteModel` para exclusão lógica.  
- **RNF‑06 – Geração de QR code**: A geração do QR code para inscrições deve ocorrer em ≤ 100 ms.  
- **RNF‑07 – Validação de arquivos**: Materiais de divulgação e comprovantes de pagamento devem ter formato e tamanho validados (imagens até 10 MB, PDFs até 20 MB)【561401687002500†L317-L349】.  
- **RNF‑08 – Log de orçamento**: Alterações de orçamento e gastos devem ser registradas com detalhes antes/depois【561401687002500†L256-L273】.

## 5. Casos de Uso

### UC‑01 – Criar Evento
1. Usuário administrador/coordenador acessa a tela de criação e informa dados do evento (título, descrição, datas, local, público, capacidade, orçamentos e contatos).  
2. Sistema valida os campos, grava o evento e registra log.  
3. O usuário é redirecionado à lista ou calendário com mensagem de sucesso.

### UC‑02 – Inscrever Usuário e Gerar QR Code
1. Usuário autenticado acessa a página do evento e solicita inscrição, selecionando método de pagamento e enviando comprovante se necessário.  
2. Sistema verifica se já existe inscrição e se há vagas. Se o evento estiver lotado e a lista de espera estiver habilitada, a inscrição é marcada como pendente e recebe posição na fila【561401687002500†L97-L113】.  
3. Se houver vagas, a inscrição é confirmada; o sistema registra data de confirmação, gera o QR code e envia link de download【561401687002500†L117-L121】.  
4. Usuário pode cancelar a inscrição antes do evento.  
5. No dia do evento, o check‑in é realizado via API que valida o QR code e registra data/hora【410067135043595†L411-L423】.

### UC‑03 – Upload e Aprovação de Material de Divulgação
1. Usuário autorizado seleciona um evento e envia arquivos de divulgação (banner, flyer, vídeo, PDF) com título, descrição, tags e miniatura opcional.  
2. Sistema valida formato e tamanho de arquivo e executa upload assíncrono para o storage【906211648821816†L29-L41】.  
3. O material fica com status “criado”; administradores ou coordenadores podem aprovar ou devolver o material informando o motivo【561401687002500†L335-L349】.  
4. O status e os metadados de avaliação ficam registrados para auditoria.

### UC‑04 – Gerenciar Parcerias
1. Administrador ou coordenador preenche os dados da parceria (empresa, CNPJ, contato, representante legal, tipo, contrato, descrição, datas).  
2. Sistema valida campos e cria a parceria; logs são gravados.  
3. Após o evento, o responsável pode registrar uma avaliação única de 1 a 5 com comentário【410067135043595†L390-L409】.

### UC‑05 – Fluxo de Briefing
1. Coordenador cria um briefing para o evento preenchendo objetivos, público‑alvo, requisitos técnicos e cronograma resumido.  
2. Administrador avalia o briefing: pode marcar como orçamentado (informando prazo de resposta), aprovado ou recusado.  
3. Em cada transição, o sistema registra avaliador, data/hora, motivo de recusa (se houver) e aciona tarefa assíncrona para notificar os envolvidos【410067135043595†L687-L725】.

### UC‑06 – Avaliar Evento
1. Após a data de término do evento, participantes confirmados acessam o formulário de avaliação e registram nota de 1 a 5 e comentário opcional【410067135043595†L310-L351】.  
2. Sistema grava a avaliação e atualiza a média do evento【561401687002500†L247-L249】.

### UC‑07 – Gerenciar Tarefas do Evento
1. Usuário autorizado cria uma tarefa relacionada a um evento ou mensagem do chat, informando título, descrição e datas de início/fim.  
2. O responsável pela tarefa pode marcar como concluída; cada mudança gera log de tarefa【561401687002500†L430-L457】【561401687002500†L472-L504】.  
3. Tarefas podem ser consultadas em listagens e detalhes.

## 6. Regras de Negócio

- Cada usuário pode ter no máximo uma inscrição por evento.  
- Inscrição só pode ser avaliada após a data de término do evento e se o usuário participou.  
- Inscrições pendentes são ordenadas pela posição na lista de espera; promoção de vagas respeita esta ordem【906211648821816†L11-L27】.  
- Materiais e parcerias devem estar vinculados a um evento existente.  
- Briefing segue obrigatoriamente o fluxo rascunho → orçamentado → aprovado/recusado.  
- Só administradores e coordenadores podem gerenciar orçamentos, parcerias, briefings e aprovar materiais; participantes comuns podem apenas inscrever‑se, avaliar e visualizar.

## 7. Modelo de Dados

*Observação:* todos os modelos herdam de `TimeStampedModel` (campos `created` e `modified`) e de `SoftDeleteModel` para exclusão lógica. Campos de auditoria não são listados individualmente.

- **Evento**  
  - id: UUID  
  - titulo: string  
  - descricao: text  
  - data_inicio, data_fim: datetime  
  - local, cidade, estado, cep: strings (cidade e estado validados por regex; CEP no formato 00000-000)【561401687002500†L171-L191】  
  - coordenador: FK → User.id  
  - organizacao: FK → Organizacao.id  
  - nucleo: FK opcional → Nucleo.id  
  - status: enum {0: Ativo, 1: Concluído, 2: Cancelado}  
  - publico_alvo: enum {0: Público, 1: Somente nucleados, 2: Apenas associados}【561401687002500†L203-L204】  
  - numero_convidados, numero_presentes: integers  
  - valor_ingresso: decimal (opcional)  
  - orcamento, orcamento_estimado, valor_gasto: decimal (opcionais)【561401687002500†L210-L215】  
  - participantes_maximo: integer (opcional)【561401687002500†L216-L218】  
  - espera_habilitada: boolean【561401687002500†L216-L218】  
  - cronograma, informacoes_adicionais: text  
  - contato_nome: string; contato_email: email; contato_whatsapp: string【561401687002500†L219-L223】  
  - avatar, cover: ImageField (upload)  
  - briefing: text (observações adicionais)  
  - mensagem_origem: FK opcional → ChatMessage.id  
  - Métodos: `calcular_media_feedback()` (calcula média das avaliações)【561401687002500†L247-L249】; `endereco_completo()` (concatena local e endereço completo)【561401687002500†L251-L252】.

- **InscricaoEvento**  
  - user: FK → User.id  
  - evento: FK → Evento.id  
  - status: enum {pendente, confirmada, cancelada}  
  - presente: boolean  
  - valor_pago: decimal (opcional)  
  - metodo_pagamento: enum {pix, boleto, gratuito, outro}【561401687002500†L39-L44】  
  - comprovante_pagamento: FileField (opcional)  
  - observacao: text  
  - data_confirmacao: datetime (opcional)  
  - qrcode_url: URL (opcional)【561401687002500†L81-L83】  
  - check_in_realizado_em: datetime (opcional)【561401687002500†L81-L83】  
  - posicao_espera: integer (opcional)  
  - avaliacao: integer (1–5) (opcional)【561401687002500†L84-L88】  
  - feedback: text (opcional)【561401687002500†L89-L90】  
  - Métodos: `confirmar_inscricao()`, `cancelar_inscricao()`, `realizar_check_in()`, `gerar_qrcode()`【561401687002500†L97-L121】【561401687002500†L148-L158】; registra logs de presença【561401687002500†L159-L168】.

- **MaterialDivulgacaoEvento**  
  - evento: FK → Evento.id  
  - titulo: string; descricao: text  
  - tipo: enum {banner, flyer, video, outro}  
  - arquivo: FileField (obrigatório)  
  - imagem_thumb: ImageField (opcional)  
  - data_publicacao: date (auto)  
  - tags: string  
  - status: enum {criado, aprovado, devolvido}【561401687002500†L335-L339】  
  - avaliado_por: FK → User.id (opcional)【561401687002500†L341-L348】  
  - avaliado_em: datetime (opcional)【561401687002500†L341-L349】  
  - motivo_devolucao: text (opcional)【561401687002500†L349-L349】  
  - Métodos: `url_publicacao()` retorna URL do arquivo【561401687002500†L358-L360】.

- **ParceriaEvento**  
  - evento: FK → Evento.id  
  - nucleo: FK opcional → Nucleo.id  
  - empresa: FK → Empresa.id  
  - cnpj: string de 14 dígitos com validação【561401687002500†L281-L284】  
  - contato: string; representante_legal: string  
  - tipo_parceria: enum {patrocinio, mentoria, mantenedor, outro}  
  - acordo: FileField (contrato)【561401687002500†L297-L298】  
  - data_inicio, data_fim: date  
  - descricao: text  
  - avaliacao: integer (1–5) (opcional)【561401687002500†L302-L307】  
  - comentario: text (opcional)【561401687002500†L307-L307】.

- **BriefingEvento**  
  - evento: FK → Evento.id  
  - objetivos, publico_alvo, requisitos_tecnicos, cronograma_resumido, conteudo_programatico, observacoes: text  
  - status: enum {rascunho, orcamentado, aprovado, recusado}【561401687002500†L369-L378】  
  - orcamento_enviado_em, aprovado_em, recusado_em: datetime (opcionais)【561401687002500†L379-L383】  
  - motivo_recusa: text (opcional)【561401687002500†L382-L383】  
  - coordenadora_aprovou: boolean  
  - recusado_por, avaliado_por: FK → User.id (opcionais)【561401687002500†L384-L399】  
  - prazo_limite_resposta: datetime (opcional)【561401687002500†L391-L392】  
  - avaliado_em: datetime (opcional)【561401687002500†L399-L399】.

- **FeedbackNota**  
  - evento: FK → Evento.id  
  - usuario: FK → User.id  
  - nota: integer (1–5)【561401687002500†L416-L417】  
  - comentario: text  
  - data_feedback: datetime (auto)【561401687002500†L419-L420】.

- **Tarefa**  
  - id: UUID  
  - titulo: string  
  - descricao: text  
  - data_inicio, data_fim: datetime【561401687002500†L437-L438】  
  - responsavel: FK → User.id  
  - organizacao: FK → Organizacao.id  
  - nucleo: FK opcional → Nucleo.id  
  - mensagem_origem: FK opcional → ChatMessage.id【561401687002500†L447-L452】  
  - status: enum {pendente, concluida}【561401687002500†L454-L457】.

- **TarefaLog**  
  - tarefa: FK → Tarefa.id  
  - usuario: FK → User.id  
  - acao: string  
  - detalhes: JSON【561401687002500†L472-L504】.

- **EventoLog**  
  - evento: FK → Evento.id  
  - usuario: FK → User.id  
  - acao: string  
  - detalhes: JSON【561401687002500†L472-L504】.

## 8. Critérios de Aceite (Gherkin)

```gherkin
Feature: Gestão de Eventos e Inscrições
  Scenario: Criar evento e inscrever usuário
    Given usuário administrador autenticado
    When POST /api/eventos/ com dados válidos
    And POST /api/eventos/<id>/inscricoes/ com método de pagamento
    Then evento é criado e inscrição confirmada ou posicionada na lista de espera
    And QR code é gerado para a inscrição confirmada

  Scenario: Avaliar evento
    Given usuário participante com inscrição confirmada
    When POST /api/eventos/<id>/feedback/ com nota e comentário após data de fim
    Then avaliação é registrada e média do evento é atualizada

  Scenario: Fluxo de briefing
    Given coordenador cria briefing em estado rascunho
    When administrador altera status para orcamentado, aprovado ou recusado
    Then sistema registra avaliador, timestamps e motivo de recusa (se houver) e notifica interessados

  Scenario: Aprovar material de divulgação
    Given material enviado por usuário autorizado
    When administrador devolve ou aprova
    Then status e motivo de devolução ficam registrados e material aprovado fica visível aos participantes

  Scenario: Gerenciar orçamento
    Given evento existente
    When administrador envia valores de orçamento estimado e valor gasto
    Then sistema atualiza campos e registra log de alteração

  Scenario: Criar tarefa
    Given usuário autorizado
    When POST /api/tarefas/ com título, datas e responsável
    Then tarefa é criada e status inicial é pendente
```

## 9. Dependências / Integrações

- **App Accounts, Organizações e Núcleos**: validações de escopo e permissões de usuário.  
- **App Chat**: tarefas podem estar vinculadas a mensagens do chat.  
- **Storage (S3)**: upload de mídias e comprovantes de pagamento.  
- **Celery**: tarefas assíncronas de upload de material, promoção da lista de espera e notificações.  
- **Search Engine**: busca de eventos e materiais (a ser integrado).  
- **Sentry**: monitoramento de erros e performance.
