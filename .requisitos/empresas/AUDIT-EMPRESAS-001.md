# AUDIT-EMPRESAS-001

Revisão do código do módulo **empresas** em relação aos requisitos `REQ-EMPRESAS-001` (v1.1.0).

| ID | Descrição resumida | Status | Observações |
|----|--------------------|--------|-------------|
| RF‑01 | Listar empresas com filtros por organização, município, estado, palavras‑chave, tags e busca textual | **Parcial** | API aceita `nome`, `tag`, `q` e `palavras_chave`, mas não filtra por organização/município/estado nem usa busca avançada (`SearchVector`). |
| RF‑02 | Cadastrar empresa com validação de CNPJ único | **Parcial** | `clean` do modelo valida CNPJ, porém o serializer não invoca `full_clean`; duplicidades podem estourar erro 500. |
| RF‑03 | Editar apenas por responsável ou admins | **Atendido** | Método `update` verifica autor ou `UserType.ADMIN/ROOT`. |
| RF‑04 | Exclusão lógica, restauração e purga com registro | **Atendido** | Ações `destroy`, `restaurar` e `purgar` presentes, com logs e métricas. |
| RF‑05 | Busca textual e filtros combinados (tags, nome, município, estado, organização) | **Parcial** | Serviço `search_empresas` suporta todos os filtros, porém o `EmpresaViewSet` não o utiliza. |
| RF‑06 | Histórico de alterações com CNPJ mascarado | **Atendido** | `registrar_alteracoes` em `signals.py`. |
| RF‑07 | Versionamento automático | **Atendido** | `pre_save` incrementa `versao`. |
| RF‑10 | Gerenciar tags hierárquicas com autocomplete | **Parcial** | Modelo e views HTML existem, mas falta API REST dedicada. |
| RF‑12 | CRUD de contatos de empresa com único principal | **Parcial** | Modelo e views HTML presentes; API REST ausente. |
| RF‑13 | Favoritar/desfavoritar com métricas | **Parcial** | Métrica usa `Counter` e não decrementa ao desfavoritar. |
| RF‑14/15 | Avaliação de empresas com notificação e post no feed | **Atendido** | Endpoint `avaliacoes` e tasks de notificação/post. |
| RF‑16 | API REST completa com controle de permissões por tipo de usuário | **Parcial** | Ausência de endpoints de contatos/tags e filtro do queryset por perfil. |
| RF‑17/18 | Integração com Celery (CNPJ, notificações, feed) | **Parcial** | Tasks implementadas, porém `validar_cnpj_empresa` usa `self` sem `bind=True` e falta `import sentry_sdk`. |
| RNF‑02 | Sanitização e controle de acesso | **Parcial** | Forms sanitizam tags; API não valida CNPJ antes de salvar. |
| RNF‑04 | Sentry e métricas | **Parcial** | Métricas expostas; falta importar `sentry_sdk`, impedindo captura de exceções. |

