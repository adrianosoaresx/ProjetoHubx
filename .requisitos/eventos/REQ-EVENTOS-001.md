---
id: REQ-EVENTOS-001
title: Requisitos do App Eventos
module: Eventos
status: Em vigor
version: '1.0'
authors: []
created: '2025-07-25'
updated: '2025-07-25'
source:
  - Requisitos_Eventos_Hubx.pdf fileciteturn3file4
  - Requisitos_InscricaoEvento_Hubx.pdf fileciteturn3file0
  - Requisitos_MaterialDivulgacaoEvento_Hubx.pdf fileciteturn3file1
  - Requisitos_ParceriaEvento_Hubx.pdf fileciteturn3file2
  - Requisitos_BriefingEvento_Hubx.pdf fileciteturn3file3
---

## 1. Visão Geral

Gerenciar todo o ciclo de vida de Eventos no Hubx: criação, edição e exclusão de eventos; inscrições de usuários; materiais de divulgação; parcerias e patrocínios; e briefing de eventos.

## 2. Escopo
- **Inclui**:
  - CRUD de eventos (título, descrição, datas, localizações).  
  - Gestão de inscrições: registro de presença, avaliação e pagamentos.  
  - Upload e gerenciamento de materiais de divulgação (imagens, vídeos, PDFs).  
  - Cadastro e gestão de parcerias e patrocínios de eventos.  
  - Fluxo de briefing: criação, aprovação, recusa e notificações.  
- **Exclui**:
  - Comunicação em tempo real (delegada a App Chat).  
  - Gestão de contas ou organizações (delegadas a Apps Accounts e Organizações).

## 3. Requisitos Funcionais

- **RF-01**  
  - Descrição: Criar, listar, editar e excluir eventos.  
  - Prioridade: Alta  
  - Critérios de Aceite: Endpoints RESTful retornam códigos HTTP apropriados.  

- **RF-02**  
  - Descrição: Registrar inscrição de usuários em eventos.  
  - Prioridade: Alta  
  - Critérios de Aceite: Usuário não pode inscrever-se mais de uma vez por evento; presença e avaliação registrados após término fileciteturn3file0.

- **RF-03**  
  - Descrição: Fazer upload e exibição de materiais de divulgação para eventos.  
  - Prioridade: Média  
  - Critérios de Aceite: Suporte a múltiplos formatos; links válidos fileciteturn3file1.

- **RF-04**  
  - Descrição: Cadastrar e gerenciar parcerias e patrocínios de eventos.  
  - Prioridade: Média  
  - Critérios de Aceite: Campos de empresa, representante e tipo de parceria validados fileciteturn3file2.

- **RF-05**  
  - Descrição: Criar e gerenciar briefing de eventos com controle de status (rascunho, orçamento, aprovação, recusa).  
  - Prioridade: Alta  
  - Critérios de Aceite: Estados transicionais válidos e notificações emitidas fileciteturn3file3.

- **RF-06**  
  - Descrição: Permitir avaliação de eventos pelos participantes após conclusão.  
  - Prioridade: Baixa  
  - Critérios de Aceite: Notas de 1 a 5 armazenadas; avaliação só pós-evento.

## 4. Requisitos Não-Funcionais

- **RNF-01**  
  - Categoria: Desempenho  
  - Descrição: Listagem de eventos e inscrições com p95 ≤ 300 ms.  
  - Métrica/Meta: 300 ms

- **RNF-02**  
  - Categoria: Confiabilidade  
  - Descrição: Upload de mídia resiliente a falhas de rede, com retries.  
  - Métrica/Meta: Até 3 tentativas automáticas

- **RNF-03**  
  - Categoria: Segurança  
  - Descrição: Validação de permissões por escopo (organização, núcleo).  
  - Métrica/Meta: 0 acessos indevidos em testes automatizados

- **RNF-04**  
  - Categoria: Auditoria  
  - Descrição: Logs e histórico de alterações para eventos, inscrições e briefings.  
  - Métrica/Meta: 100% dos eventos críticos registrados

## 5. Casos de Uso

### UC-01 – Criar Evento
1. Admin envia dados do evento.  
2. Sistema valida e cria evento.  
3. Retorna HTTP 201 com dados completos.

### UC-02 – Inscrever Usuário
1. Usuário autenticado solicita inscrição.  
2. Sistema cria registro e retorna confirmação.

### UC-03 – Upload de Material
1. Usuário autorizado faz upload de arquivo.  
2. Sistema valida formato e armazena em S3/Storage.

### UC-04 – Gerenciar Parcerias
1. Admin ou coordenador cadastra parceria.  
2. Sistema persiste dados e notifica equipe.

### UC-05 – Fluxo de Briefing
1. Coordenador preenche briefing e envia para orçamento.  
2. Admin aprova ou solicita revisão.  
3. Notificações disparadas conforme transição.

### UC-06 – Avaliar Evento
1. Participante informa nota e feedback.  
2. Sistema grava avaliação após data de fim.

## 6. Regras de Negócio
- Inscrição única por usuário por evento.  
- Avaliação permitida apenas após término do evento.  
- Material e parceria vinculados obrigatoriamente a um evento.  
- Briefing segue fluxo de estados: rascunho → orçamentado → aprovado/recusado.

## 7. Modelo de Dados

- **Evento**  
  - id: UUID  
  - titulo, descricao, data_inicio, data_fim  
  - local, cidade, estado, cep  
  - organizacao: FK → Organizacao.id  
  - nucleo: FK opcional → Nucleo.id  
  - status: enum('ativo','concluido','cancelado')  
  - created_at, updated_at: datetime

- **InscricaoEvento**  
  - user: FK → User.id  
  - evento: FK → Evento.id  
  - presente: boolean  
  - avaliacao: integer (1–5)  
  - valor_pago: decimal  
  - observacao: text

- **MaterialDivulgacaoEvento**  
  - evento: FK → Evento.id  
  - arquivo: FileField (S3)  
  - descricao: text  
  - tags: array[string]

- **ParceriaEvento**  
  - evento: FK → Evento.id  
  - empresa, cnpj, contato  
  - tipo_parceria: string  
  - representante_legal: user info

- **BriefingEvento**  
  - evento: OneToOne → Evento.id  
  - status: enum[...]  
  - coordenadora_aprovou, orcamento_enviado_em  
  - prazo_limite_resposta, recusado_por, recusado_em, motivo_recusa  
  - campos adicionais de briefing

## 8. Critérios de Aceite (Gherkin)
```gherkin
Feature: Gestão de Eventos
  Scenario: Criar e inscrever usuário
    Given usuário root autenticado  
    When POST /api/eventos/ e POST /api/eventos/<id>/inscricoes/  
    Then eventos e inscrições criados com sucesso
```

## 9. Dependências / Integrações
- **App Accounts, Organizações, Núcleos**: validações de escopo.  
- **Storage (S3)**: upload de mídia.  
- **Celery**: processamento assíncrono (emails, relatórios).  
- **Search Engine**: busca de eventos e materiais.  
- **Sentry**: monitoramento de erros.

## 10. Anexos e Referências
- PDF fontes originais de requisitos.
