# Auditoria de Requisitos — empresas

**Escopo da sprint:** análise do app `empresas` com base em `.requisitos/empresas` e código em `empresas/`.  
**Data:** 2025-08-15  
**Critérios de auditoria:** conformidade requisito × implementação, verificação de views/templates e fluxos.

## 1. Mapa do código
- Linguagens principais: Python, HTML, CSS (templates)
- Principais diretórios: `models.py`, `views.py`, `api.py`, `forms.py`, `tasks.py`, `templates/empresas`
- Pontos de entrada/rotas: `urls.py` para páginas web e `api_urls.py` para API REST
- Autenticação/Autorização: mixins como `LoginRequiredMixin`, `ClienteGerenteRequiredMixin`, permissões checadas com `pode_crud_empresa` e validações por `UserType`

## 2. Rastreabilidade Requisito × Implementação
| REQ_ID | Título/Resumo | Status | Evidências (arquivo:linhas) | Risco/Impacto | Ações Recomendadas |
|-------|----------------|--------|-----------------------------|----------------|--------------------|
| RF-01 | Listagem paginada e filtros | ATENDIDO | `views.py:25-47`, `services.py:16-72` | Baixo | — |
| RF-02 | Cadastro com CNPJ único | ATENDIDO | `forms.py:43-53`, `models.py:80-82` | Baixo | — |
| RF-03 | Edição restrita a autor/admin | ATENDIDO | `views.py:84-88`, `api.py:64-73` | Médio | — |
| RF-04 | Soft delete e restauração | ATENDIDO | `views.py:100-114`, `api.py:47-58` | Médio | — |
| RF-05 | Busca por campos e texto | ATENDIDO | `services.py:40-72` | Baixo | — |
| RF-06 | Restaurar empresas | ATENDIDO | `api.py:135-151` | Médio | — |
| RF-07 | Purgar definitivamente | ATENDIDO | `api.py:153-169` | Médio | — |
| RF-08 | Histórico de alterações | ATENDIDO | `services.py:86-129`, `signals.py:19-51` | Médio | — |
| RF-09 | Versionamento automático | ATENDIDO | `signals.py:19-29` | Baixo | — |
| RF-10 | Gerenciamento de tags hierárquicas | ATENDIDO | `models.py:14-33`, `views.py:126-157` | Baixo | — |
| RF-11 | Filtrar por múltiplas tags (AND) | PARCIAL | `services.py:58-59` | Médio | Ajustar filtro para exigir todas as tags selecionadas |
| RF-12 | CRUD de contatos com único principal | ATENDIDO | `models.py:109-133`, `views.py:216-253` | Médio | — |
| RF-13 | Favoritar/desfavoritar empresas | ATENDIDO | `api.py:76-99`, `models.py:172-187` | Baixo | — |
| RF-14 | Avaliação única por usuário e média | ATENDIDO | `models.py:154-166`, `views.py:200-249`, `api.py:100-124` | Médio | — |
| RF-15 | Notificar responsável e postar no feed | ATENDIDO | `tasks.py:36-53`, `tasks.py:74-92`, `tasks.py:95-98` | Baixo | — |
| RF-16 | API REST completa + extras | PARCIAL | `api.py:24-169` | Alto | Criar endpoint para validação de CNPJ |
| RF-17 | Tasks Celery com Sentry e retries | ATENDIDO | `tasks.py:18-33`, `tasks.py:36-53`, `tasks.py:56-92` | Médio | — |
| RF-18 | Post automático ao criar empresa | ATENDIDO | `signals.py:32-41`, `tasks.py:56-71` | Baixo | — |
| RNF-01 | Uso de indexes e otimização de queries | ATENDIDO | `models.py:65-75`, `services.py:25` | Médio | — |
| RNF-02 | Segurança de dados e permissões | ATENDIDO | `forms.py:43-67`, `api.py:64-73` | Médio | — |
| RNF-03 | Logs mascarados e storage seguro | ATENDIDO | `services.py:118-123`, `models.py:52` | Baixo | — |
| RNF-04 | Integração com Sentry e métricas | ATENDIDO | `tasks.py:3`, `metrics.py:1-14`, `api.py:87-98` | Baixo | — |
| RNF-05 | Reprocessar validação de CNPJ em falhas | PARCIAL | `tasks.py:18-33` | Médio | Implementar retry com backoff |
| RNF-06 | Código modular e testes ≥90% | NÃO VERIFICÁVEL | — | Alto | Medir cobertura de testes |
| RNF-07 | Herança de TimeStamped/SoftDelete | ATENDIDO | `models.py:43-74`, `models.py:109-133` | Baixo | — |

### 2.1 Detalhes por requisito (com evidências)
**RF-11 — Filtrar por múltiplas tags (AND)**  
- **Descrição:** Listagens devem aceitar várias tags com lógica AND.  
- **Evidências:** `services.py:58-59` utiliza `qs.filter(tags__in=tags)` (lógica OR).  
- **Conclusão:** PARCIAL.  
- **Ação:** Iterar sobre lista de tags aplicando filtro sequencial para exigir todas as tags.

**RF-16 — API REST completa + extras**  
- **Descrição:** Endpoint deve incluir operações de validação de CNPJ.  
- **Evidências:** `api.py:24-169` cobre CRUD, favoritos, avaliações e histórico, mas não há endpoint para validar CNPJ.  
- **Conclusão:** PARCIAL.  
- **Ação:** Expor ação `validar_cnpj` no `EmpresaViewSet`.

**RNF-05 — Reprocesso em falhas de validação**  
- **Descrição:** Em falhas externas, validação de CNPJ deve ser reprocessada.  
- **Evidências:** `tasks.py:18-33` registra exceção e retorna sem retry.  
- **Conclusão:** PARCIAL.  
- **Ação:** Configurar `retry` com backoff exponencial.

**RNF-06 — Cobertura de testes ≥90%**  
- **Descrição:** Exige métricas de cobertura.  
- **Evidências:** Não há relatório de cobertura.  
- **Conclusão:** NÃO VERIFICÁVEL.  
- **Ação:** Executar `pytest --cov` e registrar métricas.

## 3. Checklist de Views/Templates & Fluxos
- **Navegação:** Botão "Nova Empresa" e filtros presentes em `templates/empresas/lista.html`.
- **Roteamento:** URLs mapeadas em `urls.py` contemplam CRUD, tags, contatos, avaliações e histórico.
- **Acesso/Permissões:** Uso de `LoginRequiredMixin` e checagem `pode_crud_empresa` nas views; API valida tipo de usuário.
- **UI/Validações/Feedback:** Mensagens de sucesso/erro via `messages` e respostas JSON para HTMX.
- **I18n/A11y:** Templates usam `{% trans %}` e etiquetas de formulário, mas acessibilidade detalhada não foi auditada.
- **Links/ações quebradas:** Não foram encontrados links órfãos na inspeção manual.
- **Cobertura de fluxos críticos:** Cadastro, edição, exclusão lógica, avaliação, favoritos e histórico verificados nas views e templates correspondentes.
- **Resumo:** Prioridades 1) ajustar filtro de múltiplas tags, 2) criar endpoint de validação de CNPJ, 3) implementar retry na task de validação.

## 4. Gaps e Plano de Ação Priorizado
1. [Alta] Filtro AND de tags — alterar `services.py` para aplicar `.filter(tags=tag)` iterativamente.  
2. [Alta] Endpoint de validação de CNPJ — adicionar ação customizada no `EmpresaViewSet`.  
3. [Média] Retry na validação de CNPJ — usar `autoretry_for` ou `retry` manual no task `validar_cnpj_empresa`.  
4. [Baixa] Medir cobertura de testes do app.

## 5. Decisões de Auditoria
- Critério de match do app: selecionado diretório `./empresas` por ser único com arquivos de código.  
- Assunções: cobertura de testes e storage externo não puderam ser verificadas em ambiente local.

## 6. Anexos (buscas e referências)
- `pytest tests/empresas -q`
- Listagem de templates em `templates/empresas/`
