# Imutabilidade dos Logs de Configuração

Os registros em `ConfiguracaoContaLog` são imutáveis e não possuem soft-delete.
A decisão foi tomada para garantir auditabilidade total das alterações de
preferências de usuários, em conformidade com o requisito normativo
REQ-CONFIGURACOES_CONTA-001. A exclusão física só ocorre por políticas de
retenção globais da aplicação.
