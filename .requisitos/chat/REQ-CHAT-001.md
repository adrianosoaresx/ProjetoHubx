---
id: REQ-CHAT-001
title: Requisitos do App Chat
module: Chat
status: Em vigor
version: "1.0"
authors: []
created: "2025-07-25"
updated: "2025-07-25"
source:
  - requisitos_app_chat_hubx.pdf
  - explicacao_modelo_chat.pdf
---

## 1. Visão Geral

O App Chat deve permitir comunicação em tempo real via WebSocket e interface visual entre usuários em diferentes contextos organizacionais (privado, núcleo, evento e organização), de forma modular e reutilizável.

## 2. Escopo
- **Inclui**  
  - Chat privado (1:1) entre dois usuários do mesmo núcleo.  
  - Chat de núcleo: canal coletivo para membros de um núcleo.  
  - Chat de evento: canal para participantes de um evento.  
  - Chat de organização: canal público para associados e admins.  
  - Fixar mensagens e exportar histórico para admins.  
- **Exclui**  
  - Ferramentas de edição de mensagem além do básico.  
  - Armazenamento offline de histórico de chat.

## 3. Requisitos Funcionais

- **RF‑01**  
  - Descrição: Suporte a WebSocket para comunicação em tempo real.  
  - Prioridade: Alta  
  - Critérios de Aceite: Conexão estável e bidirecional via `ws/chat/.../`.  

- **RF‑02**  
  - Descrição: Envio e recebimento de mensagens de texto, imagem, vídeo e arquivo.  
  - Prioridade: Alta  
  - Critérios de Aceite: Suporta tipos `text`, `image`, `video`, `file`.  

- **RF‑03**  
  - Descrição: Validação de escopo: usuário deve pertencer ao contexto (núcleo, evento ou organização).  
  - Prioridade: Alta  
  - Critérios de Aceite: Verifica `user.context_id` antes de publicar mensagem.  

- **RF‑04**  
  - Descrição: Notificação de novas mensagens em tempo real.  
  - Prioridade: Média  
  - Critérios de Aceite: Notificações aparecem no frontend sem refresh.  

- **RF‑05**  
  - Descrição: Permissões extras para admins: fixar mensagens e exportar histórico.  
  - Prioridade: Baixa  
  - Critérios de Aceite: Admin pode fixar mensagens e baixar histórico via endpoint.  

## 4. Requisitos Não‑Funcionais

- **RNF‑01**  
  - Categoria: Desempenho  
  - Descrição: Latência máxima de resposta do WebSocket  
  - Métrica/Meta: p95 ≤ 200 ms  

- **RNF‑02**  
  - Categoria: Manutenibilidade  
  - Descrição: Código modular e documentado  
  - Métrica/Meta: Cobertura ≥ 90 %  


- **RNF‑03**: Todos os modelos deste app devem herdar de `TimeStampedModel` para timestamps automáticos (`created` e `modified`), garantindo consistência e evitando campos manuais.
- **RNF‑04**: Quando houver necessidade de exclusão lógica, os modelos devem implementar `SoftDeleteModel` (ou mixin equivalente), evitando remoções físicas e padronizando os campos `deleted` e `deleted_at`.

## 5. Casos de Uso

### UC‑01 – Comunicação em Tempo Real
1. Usuário acessa a página de chat e estabelece conexão WebSocket.  
2. Envia mensagem via `ChatConsumer`.  
3. Mensagem é retransmitida a todos os participantes do canal.

### UC‑02 – Enviar Mensagem
1. Usuário digita mensagem e confirma envio.  
2. Sistema valida permissões e publica no canal correto.  
3. Todos os participantes recebem em tempo real.

### UC‑03 – Fixar Mensagem (Admin)
1. Admin envia comando de fixação em uma mensagem.  
2. Sistema marca a mensagem como fixa e notifica o canal.

### UC‑04 – Exportar Histórico (Admin)
1. Admin solicita exportação de histórico de um canal.  
2. Sistema gera arquivo JSON/CSV com todas as mensagens do canal.

## 6. Modelo de Dados
*Nota:* Todos os modelos herdam de `TimeStampedModel` (campos `created` e `modified`) e utilizam `SoftDeleteModel` para exclusão lógica quando necessário. Assim, campos de timestamp e exclusão lógica não são listados individualmente.

- **ChatChannel**  
  - id: UUID  
  - tipo: enum('privado','nucleo','evento','organizacao')  
  - context_id: UUID  

- **Mensagem**  
  - id: UUID  
  - channel: FK → ChatChannel.id  
  - remetente: FK → User.id  
  - tipo: enum('text','image','video','file')  
  - conteudo: text ou URL  
  - timestamp: datetime  

- **Notificacao**  
  - id: UUID  
  - usuario: FK → User.id  
  - mensagem: FK → Mensagem.id  
  - lida: boolean  

## 7. Regras de Negócio
- Usuário deve estar autenticado e ter vínculo com o contexto.  
- Apenas admins podem fixar mensagens e exportar histórico.  

## 8. Critérios de Aceite (Gherkin)
```gherkin
Feature: Chat em tempo real
  Scenario: Envio de mensagem de texto
    Given usuário autenticado no canal de organização
    When envia "Olá, mundo!"
    Then todos no canal recebem "Olá, mundo!"
```

## 9. Dependências / Integrações
- **WebSocket**: consumers em `chat/consumers.py`.  
- **Channels Redis**: camada de broadcast e grupo de canais.  
- **Modelos**: `chat.models.ChatChannel`, `chat.models.Mensagem`, `chat.models.Notificacao`.  
- **Accounts Service**: autenticação e associação de usuários.  
- **Celery**: envio de notificações assíncronas.  
- **Sentry**: monitoramento de erros.

## 10. Anexos e Referências
- `requisitos_app_chat_hubx.pdf`  
- `explicacao_modelo_chat.pdf`

## 11. Requisitos Adicionais e Melhorias (Auditoria 2025‑07‑25)

### Requisitos Funcionais Adicionais
- **RF‑06** – Mensagens podem ser fixadas por administradores e exibidas no topo do chat com indicação visual. Campo `pinned_at` registra quando a mensagem foi fixada.  
- **RF‑07** – Exportar histórico de mensagens em formatos JSON e CSV, com possibilidade de filtro por data e tipo de mensagem.  
- **RF‑08** – Suporte a moderação de mensagens (edição ou exclusão) e sinalização por usuários para remoção de conteúdo inadequado.  
- **RF‑09** – Sistema de reação (emoji) nas mensagens para aumentar engajamento.  

### Requisitos Não‑Funcionais Adicionais
- **RNF‑05** – Escalabilidade para suportar 10 000 conexões WebSocket simultâneas.  
- **RNF‑06** – Históricos exportados devem incluir metadados (remetente, timestamp, tipo) e ser gerados em ≤ 500 ms.  

### Modelo de Dados Adicional
- Em `Mensagem`, adicionar `pinned_at: datetime` (opcional) e `reactions: JSONField` (mapeamento emoji→contagem).  
- Criar entidade `RelatorioChatExport` para rastrear exportações (id, channel_id, formato, gerado_por, gerado_em, arquivo_url).  

### Regras de Negócio Adicionais
- Apenas usuários com permissão `admin` podem moderar ou fixar mensagens.  
- Mensagens sinalizadas por ≥ 3 usuários devem ser ocultadas até revisão de um moderador.