# Relatório de Análise – App Organizações

### Visão geral
O app Organizações gerencia dados cadastrais de entidades, permite criar, editar, inativar, reativar e excluir organizações, além de registrar alterações e enviar notificações aos membros.

### Funcionalidades faltantes em relação ao requisito
- Endpoints para associar ou remover usuários, núcleos, eventos, empresas e posts não foram implementados.
- Não há medições de desempenho p95 das APIs.
- Falta cache e otimizações `select_related/prefetch_related` nas rotas de API.
- Logs de auditoria não estão integrados ao Sentry.
- Cobertura de testes automatizados e métricas de qualidade não são evidenciadas.

### Funcionalidades extras encontradas no código
- Cadastro de CNPJ com validação e mascaramento.
- Campos de endereço e contato: rua, cidade, estado, contato_nome, contato_email, contato_telefone.
- Campo `rate_limit_multiplier` para ajustar limites de requisições.
- Inativação e reativação de organizações com registro de data.
- Logs imutáveis de alterações (`OrganizacaoChangeLog`) e atividades (`OrganizacaoAtividadeLog`).
- Exportação de histórico em CSV e sinal `organizacao_alterada` que dispara notificações assíncronas aos membros.

### Divergências de contratos de API
- Requisito prevê endpoints de associação de recursos; código expõe apenas o CRUD principal e ações `inativar`, `reativar` e `history`.
- Filtros suportados (`inativa`, `ordering`) e campos retornados (CNPJ, contatos, endereço) não constam no requisito original.
- Modelo de dados inclui campos extras não especificados inicialmente.

### RNFs atendidos vs. pendentes
- **Atendidos:** soft delete em `Organizacao`; validação de formato e tamanho de imagens; registro de atividades e mudanças.
- **Pendentes:** p95 das views, cache, otimizações de consulta, integração com Sentry, cobertura de testes ≥90 %, herança de `TimeStampedModel` e `SoftDeleteModel` para logs auxiliares, acessibilidade e auditoria centralizada.

### Riscos técnicos e débito tecnológico
- Ausência de métricas de desempenho e cobertura pode ocultar regressões.
- Falta de cache e otimização pode causar N+1 em consultas extensas.
- Logs auxiliares sem `SoftDeleteModel` dificultam limpeza e controle de retenção.
- Testes de API falhando indicam instabilidade.

### Recomendações e próximos passos
1. Implementar endpoints de associação de usuários e recursos ou revisar requisito.
2. Adicionar medições de desempenho, cache e `select_related/prefetch_related` nas consultas.
3. Incluir Sentry e logs estruturados para auditoria.
4. Garantir que todos os modelos adotem `TimeStampedModel` e `SoftDeleteModel` quando aplicável.
5. Aumentar cobertura de testes e corrigir falhas existentes.

### Checklist de Conformidade
- [ ] Soft delete padronizado em todos os modelos (logs não aderem).
- [ ] Todos os modelos herdam de `TimeStampedModel` (logs não aderem).
- [x] Permissões por perfil: root cria/edita/exclui; admin apenas lê e consulta histórico.
- [x] Listagem aceita busca por slug e filtros básicos; paginação padrão DRF.
- [ ] Upload de avatar/cover com storage externo comprovado.
- [ ] Testes automatizados cobrindo fluxos críticos ≥90 %.
- [ ] Logs enviados ao Sentry e auditáveis.
- [ ] Cache ou `select_related/prefetch_related` para evitar N+1.
- [ ] p95 das views ≤250 ms evidenciado.
