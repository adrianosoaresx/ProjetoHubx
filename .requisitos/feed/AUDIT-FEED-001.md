# Auditoria do Feed — REQ-FEED-001

## Cobertura dos Requisitos

| Requisito | Situação | Observações |
|-----------|----------|-------------|
| RF‑01 – RF‑06 | Atendido | Listagem, criação, filtros, upload e URLs assinadas implementados |
| RF‑07 | Parcial | Falta geração de pré‑visualização para vídeos |
| RF‑08 | Não atendido | API não expõe CRUD de tags |
| RF‑09 – RF‑11, RF‑14, RF‑16 – RF‑20, RF‑23 – RF‑24 | Atendido | Funcionalidades principais implementadas conforme especificação |
| RF‑12 | Parcial | `ModeracaoPost` armazena apenas último estado (OneToOne) |
| RF‑13 | Parcial | Curtidas não fazem toggle automático e podem ser manipuladas por outros usuários |
| RF‑15 | Parcial | Remoção de comentários não restringe ao autor ou moderador |
| RF‑21 | Parcial | Métricas contabilizam apenas notificações de novos posts |
| RF‑22 | Parcial | Existe loader de plugins, mas não há agendamento de execução automática |
| RF‑25 | Parcial | Tasks Celery não registram falhas no Sentry nem realizam retries; uploads síncronos |
| RNF‑02 | Parcial | Controle de acesso para edição de posts e comentários incompleto |
| RNF‑03 & RNF‑05 | Parcial | Falta integração Sentry e retries para tasks/ uploads |

## Questões Encontradas e Ações Recomendadas

1. **Edição de posts acessível a qualquer usuário autenticado (RF‑03 / RNF‑02)**  
   - Restringir edição de posts ao autor ou moderadores.  
   - Criar testes cobrindo edição não autorizada.

2. **Ausência de pré‑visualização de vídeos (RF‑07)**  
   - Gerar thumbnail de vídeo no upload.  
   - Expor URL da pré‑visualização na API.

3. **CRUD de tags inexistente (RF‑08)**  
   - Criar API para gerenciamento de tags (serializers, viewset, rotas).  
   - Cobrir CRUD com testes.

4. **Histórico de moderação não preservado (RF‑12)**  
   - Registrar histórico de decisões de moderação em vez de sobrescrever estado.  
   - Ajustar modelo, lógica e testes.

5. **Curtidas não realizam toggle automático e não restringem autoria (RF‑13)**  
   - Implementar toggle seguro de curtidas.  
   - Bloquear manipulação de curtidas de terceiros.

6. **Remoção de comentários sem verificação de autor (RF‑15)**  
   - Permitir remoção/edição apenas ao autor ou moderador.  
   - Adicionar testes de permissão.

7. **Envio duplicado de notificações de curtidas/comentários (RF‑19)**  
   - Unificar mecanismo de envio (síncrono ou assíncrono).  
   - Garantir único disparo em testes.

8. **Métricas de notificações incompletas (RF‑21)**  
   - Incrementar métricas para todas as notificações enviadas.  
   - Testar contagem de likes e moderação.

9. **Execução automática de plugins inexistente (RF‑22)**  
   - Agendar task periódica para executar plugins do feed.  
   - Cobrir execução agendada em testes.

10. **Tasks Celery sem Sentry e sem retries; uploads síncronos (RF‑25, RNF‑03, RNF‑05)**  
    - Integrar `sentry_sdk` e configurar retries nas tasks.  
    - Tornar upload de mídia assíncrono com tentativas de repetição.

## Plano de Sprints

**Sprint 1 – Correções de segurança e bugs (capacidade: 3 tarefas)**  
- Restringir edição de posts ao autor ou moderadores  
- Restringir remoção/edição de comentários  
- Evitar notificações duplicadas  

**Sprint 2 – Funcionalidades essenciais faltantes**  
- Expor API para gerenciamento de tags  
- Implementar toggle seguro de curtidas  
- Contabilizar todas as notificações  

**Sprint 3 – Melhorias avançadas e resiliência**  
- Gerar thumbnail para vídeos  
- Registrar histórico de moderação  
- Agendar execução de plugins  
- Adicionar Sentry e retries às tasks e uploads  

Cada sprint foi planejado considerando que o Codex realiza de 3 a 4 entregáveis por ciclo, mantendo complexidade equilibrada entre correções e novas implementações.

## Testing

Nenhum teste ou comando de validação foi executado nesta análise.

## Notes

O arquivo `AUDIT-FEED-001.md` foi gerado apenas para referência e pode ser salvo manualmente em `.requisitos/feed/`.
