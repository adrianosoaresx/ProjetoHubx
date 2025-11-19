# Guia de configuração do chat com IA

Este guia consolida variáveis de ambiente, limites e passos para habilitar o chat com chamadas de ferramenta do Hubx.

## Variáveis de ambiente
- `OPENAI_API_KEY` (obrigatória para produção): chave utilizada para autenticar as chamadas à API da OpenAI.
- `OPENAI_DEFAULT_MODEL` (opcional, padrão `gpt-4-turbo`): modelo usado nas requisições de chat.
- `OPENAI_MAX_TOKENS` (opcional, padrão `4096`): limite de tokens de entrada aceito em cada requisição.
- `OPENAI_MAX_COMPLETION_TOKENS` (opcional, padrão `1024`): quantidade máxima de tokens que podem ser gerados em uma resposta final.
- `OPENAI_REQUEST_TIMEOUT` (opcional, padrão `30` segundos): tempo limite para aguardar as respostas da API.

## Limites e segurança
- Rate limit: 30 requisições de chat por minuto por usuário, configurado via `REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["ai_chat"]`.
- Funções marcadas como pesadas (`get_membership_totals`, `get_event_status_totals`, `get_monthly_members`, `get_nucleo_metrics`) utilizam cache por 5 minutos para evitar chamadas repetidas.
- Somente perfis `admin`, `coordenador`, `consultor` e `root` podem acessar o assistente; usuários fora desses papéis recebem 403.

## Como habilitar o chat
1. Configure as variáveis de ambiente acima e reinicie o servidor para carregar o `OPENAI_API_KEY` e os limites desejados.
2. Garanta que o usuário esteja associado a uma organização ativa e possua um dos papéis permitidos. A sessão e as mensagens são sempre filtradas por `organizacao_id` e pelo usuário autenticado.
3. Acesse `/ai-chat/` após autenticação. A view cria (ou reaproveita) uma sessão ativa e envia as mensagens para o endpoint `/api/ai-chat/messages/`, que orquestra as chamadas de ferramenta e a resposta final do modelo.
