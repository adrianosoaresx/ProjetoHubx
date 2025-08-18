# AUDIT-NUCLEOS-001.md

## Escopo
Auditoria do app **nucleos** confrontando o documento de requisitos
`REQ-NUCLEOS-001.md` com o código disponível em `/nucleos`.

## Resumo Executivo
- **Cobertura geral:** a maioria dos requisitos funcionais (RF-01 a RF-15) está implementada.
- **Pendências principais:** gerenciamento de coordenadores via API, listagem de núcleos do usuário, controle de acesso por organização e campo `ativo` no modelo.
- **Riscos identificados:** contagem incorreta de membros ativos ao incluir suspensos.

## Requisitos Funcionais

| Código | Situação | Evidência |
|-------|----------|-----------|
| RF-01–RF-15 | Atendidos | Endpoints em `nucleos/api.py` e modelos correspondentes. |
| RF-16 | Parcial | Ausência de endpoint de API para alteração de papel. |
| RF-17 | Não implementado | Não há listagem “meus núcleos”. |
| RF-18 | Parcial | Promover/rebaixar coordenador apenas via views HTML. |

## Regras de Negócio

| Regra | Situação | Observação |
|-------|----------|------------|
| Suspenso não conta como ativo | Parcial | Publicação bloqueada, mas consultas e métricas contam suspensos. |
| Controle de acesso organizacional | Parcial | Listagem não valida organização do usuário. |

## Pendências de Implementação
1. Adicionar campo `ativo` em `Nucleo`.
2. Corrigir consultas e métricas para ignorar suspensos.
3. Criar endpoints de API para gestão de coordenadores e listagem de núcleos do usuário.
4. Restringir listagem ao escopo da organização autenticada.

## Conclusão
O módulo já oferece funcionalidades centrais, mas precisa de ajustes
para cumprir integralmente os requisitos e regras de negócio.
