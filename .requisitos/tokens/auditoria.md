# Auditoria de Requisitos — tokens

**Escopo da sprint:** análise do app `tokens` com base em `.requisitos/tokens/**` e código em `tokens/`.  
**Data:** 2025-02-14  
**Critérios de auditoria:** conformidade requisito × implementação, verificação de views/templates e fluxos.

## 1. Mapa do código
- Linguagens principais: Python, HTML
- Principais diretórios: `tokens/` (models, views, api, serviços), `tokens/templates/tokens/`
- Pontos de entrada/rotas: `tokens/urls.py`, `tokens/api_urls.py`
- Autenticação/Autorização: `IsAuthenticated` nos viewsets, checagens de tipo de usuário para revogação de convites e escopo `admin` em tokens de API

## 2. Rastreabilidade Requisito × Implementação
| REQ_ID | Título/Resumo | Status | Evidências (arquivo:linhas) | Risco/Impacto | Ações Recomendadas |
|-------|----------------|--------|-----------------------------|----------------|--------------------|
| RF-01 | Gerar token de convite único | ATENDIDO | `tokens/api.py:28-54` | Baixo | — |
| RF-02 | Validar token de convite via endpoint | ATENDIDO | `tokens/api.py:56-82` | Baixo | — |
| RF-03 | Expirar token após data limite | ATENDIDO | `tokens/api.py:66-68` | Baixo | — |
| RF-04 | Marcar token como usado e bloquear reutilização | ATENDIDO | `tokens/api.py:84-108` | Baixo | — |
| RF-05 | Restringir emissão por perfil | NÃO ATENDIDO | — | Médio | Implementar checagem de perfil na criação |
| RF-06 | Limite de 5 convites/dia | ATENDIDO | `tokens/api.py:31-41` | Médio | — |
| RF-07 | Registrar IP e user agent | ATENDIDO | `tokens/api.py:44-52,74-80,100-105,125-136` | Baixo | — |
| RF-08 | Revogação manual de convites | ATENDIDO | `tokens/api.py:110-138` | Baixo | — |
| RF-09 | Gerar token de API com escopo e expiração | ATENDIDO | `tokens/api_views.py:24-36` | Baixo | — |
| RF-10 | Listar e revogar tokens de API | ATENDIDO | `tokens/api_views.py:19-22,38-43` | Baixo | — |
| RF-11 | Autenticar via header Bearer | ATENDIDO | `tokens/auth.py:12-31` | Baixo | — |
| RF-12 | Código de autenticação 6 dígitos por 10 min | ATENDIDO | `tokens/models.py:142-160` | Baixo | — |
| RF-13 | Registrar dispositivo TOTP | ATENDIDO | `tokens/models.py:166-181` | Baixo | — |
| RF-14 | Auditoria via `/api/tokens/<id>/logs/` | ATENDIDO | `tokens/api.py:140-147` | Baixo | — |
| RF-15 | Rotação automática de tokens de API | NÃO ATENDIDO | — | Médio | Implementar rotação automática |
| RF-16 | Vincular tokens a fingerprint de device | NÃO ATENDIDO | — | Médio | Associar tokens a device opcional |
| RF-17 | Lista de IP allow/deny por token | NÃO ATENDIDO | — | Médio | Adicionar filtro de IP |
| RF-18 | Rate limit por token/usuário/IP | NÃO ATENDIDO | `tokens/api.py:31-41` (apenas geração) | Alto | Implementar rate limits de uso |
| RF-19 | Webhooks de ciclo de vida | NÃO ATENDIDO | — | Médio | Emitir webhooks com HMAC |
| RF-20 | Métricas de uso e webhooks | NÃO ATENDIDO | — | Médio | Expor métricas Prometheus |
| RNF-01 | Tokens com entropia ≥128 bits e não logados | PARCIAL | `tokens/services.py:16-28` (API ok), `tokens/models.py:42-55` (convite em texto claro) | Médio | Hash de códigos de convite |
| RNF-02 | Validação p95 ≤200 ms | NÃO VERIFICÁVEL | — | Médio | Implementar métricas de latência |
| RNF-03 | Eventos 100% registrados | ATENDIDO | `tokens/api.py:44-52,74-80,100-105,125-136` | Baixo | — |
| RNF-04 | Modelos com TimeStamped e SoftDelete | ATENDIDO | `tokens/models.py:16-181` | Baixo | — |
| RNF-05 | Logs criptografados e limpeza diária | ATENDIDO | `tokens/models.py:135-137`, `tokens/tasks.py:9-20` | Baixo | — |
| RNF-06 | Métricas Prometheus | NÃO ATENDIDO | — | Médio | Instrumentar métricas |
| RNF-07 | Segredos armazenados com hashing/cripto | PARCIAL | `tokens/models.py:148-156` (código em texto claro) | Médio | Hash de códigos de convite e autenticação |
| RNF-08 | Revogação idempotente com registro | ATENDIDO | `tokens/api.py:116-138` | Baixo | — |

### 2.1 Detalhes por requisito (com evidências)
**RF-01 — Gerar token de convite único**  
- **Descrição:** POST `/api/tokens/` deve criar token de convite com retorno 201 e código único.  
- **Evidências:** `tokens/api.py:28-54`  
- **Conclusão:** ATENDIDO  
- **Ação:** —

**RF-05 — Restringir emissão por perfil**  
- **Descrição:** Apenas perfis autorizados podem gerar convites.  
- **Evidências:** ausência de checagem de perfil em `tokens/api.py:28-54`.  
- **Conclusão:** NÃO ATENDIDO  
- **Ação:** Aplicar restrição por tipo de usuário antes de salvar.

**RF-18 — Rate limit por token/usuário/IP**  
- **Descrição:** Deve haver limitação de uso além do limite diário de emissão.  
- **Evidências:** Apenas verificação de limite diário em `tokens/api.py:31-41`.  
- **Conclusão:** NÃO ATENDIDO  
- **Ação:** Implementar rate limit de validação/uso por token e IP.

**RNF-01 — Tokens com entropia ≥128 bits e não logados**  
- **Descrição:** Tokens e códigos devem ser seguros e não armazenados em texto claro.  
- **Evidências:** `tokens/services.py:16-28` gera token seguro; `tokens/models.py:42-55` armazena `codigo` de convites em texto claro.  
- **Conclusão:** PARCIAL  
- **Ação:** Hash de códigos de convite antes de persistir.

## 3. Checklist de Views/Templates & Fluxos
- **Navegação:** telas de geração, validação e 2FA acessíveis via `tokens/gerar-token/`, `tokens/validar-token/`, `tokens/ativar-2fa/`. Evidências: `tokens/urls.py`
- **Roteamento:** rotas API e HTML mapeadas corretamente. Evidências: `tokens/urls.py`, `tokens/api_urls.py`
- **Acesso/Permissões:** `IsAuthenticated` nas APIs; revogação exige tipo ROOT/ADMIN. Falta checagem na geração de convites.
- **UI/Validações/Feedback:** templates usam mensagens e partial `_resultado.html` para respostas via HTMX. Evidências: `tokens/views.py`
- **I18n/A11y:** uso de `gettext_lazy` nos textos; sem elementos de acessibilidade específicos.
- **Links/ações quebradas:** não foram encontrados links órfãos nos templates analisados.
- **Cobertura de fluxos críticos:** geração, validação, uso e revogação de tokens cobertos; falta fluxo de rotação e métricas.
- **Resumo:** Prioridades 1) restringir emissão por perfil, 2) implementar rate limits e métricas, 3) hash de códigos de convite.

## 4. Gaps e Plano de Ação Priorizado
1. [Alta] Falta de controle de perfil na emissão de convites → adicionar validação em `TokenViewSet.create`.
2. [Alta] Ausência de rate limit de uso → introduzir middleware ou contador por token/IP.
3. [Média] Códigos de convite armazenados em texto claro → aplicar hash e evitar logs.
4. [Média] Métricas Prometheus e monitoramento de latência → instrumentar endpoints.

## 5. Decisões de Auditoria
- Critério de match do app: código localizado em `tokens/` por contagem de arquivos.
- Assunções: requisitos RF-15–RF-19 considerados escopo futuro; marcação como NÃO ATENDIDO.

## 6. Anexos (buscas e referências)
- `rg "TokenUsoLog" -n`
- `pytest tests/tokens -q`
