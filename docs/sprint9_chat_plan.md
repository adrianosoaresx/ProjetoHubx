# Planejamento da Sprint 9 – Chat (Hubx)

## Contexto
Após oito sprints de evolução contínua, o módulo de chat do Hubx já oferece funcionalidades robustas: mensagens em tempo real com WebSocket, reações acessíveis, busca com filtros, citações e threads, presença e digitação, notificações direcionadas, papéis e permissões por canal, favoritos, agendamento e PWA. Para consolidar e expandir a plataforma, a Sprint 9 foca em análise de uso, organização de canais, gerenciamento de arquivos e personalização da experiência do usuário, além de reforçar medidas anti‑spam.

## Objetivos da Sprint 9
- Painel de métricas e estatísticas de chat
- Categorias e filtros de canais para navegação eficiente
- Aprimoramento do sistema de uploads e gerenciamento de arquivos
- Preferências avançadas de usuário e busca salva
- Mecanismos de rate limiting e detecção de spam

## Tarefas priorizadas
### 1. Painel de métricas e estatísticas
- **API de agregação**: Desenvolver endpoints no backend (DRF) que retornem estatísticas agregadas, como mensagens enviadas por dia/semana/mês, número de mensagens por canal, top usuários ativos, total de reações por tipo, e quantidade de mensagens sinalizadas. Utilizar agregações do Django ORM e otimizar com índices e cache.
- **Dashboard administrativo**: Criar uma página no frontend (HTMX/React se necessário) acessível apenas a administradores, que consuma essas APIs e exiba gráficos (via Chart.js ou similar) e tabelas interativas. Incluir filtros por período e canal. Assegurar acessibilidade nos gráficos (descrições textuais).
- **Exportação de relatórios**: Permitir que admins exportem os dados agregados em CSV/JSON para análise externa. Utilizar Celery para processamento assíncrono se os conjuntos forem grandes.

### 2. Categorias e filtros de canais
- **Modelo de categoria**: Adicionar um modelo `ChatChannelCategory` (campos: nome, slug, descrição, organização/núcleo). Relacionar `ChatChannel` a uma categoria opcional. Migrar canais existentes para categorias padrão (ex.: “Público”, “Projetos”, “Eventos”).
- **Navegação por categoria**: No frontend, reorganizar a lista de canais (sidebar) agrupando‑os por categoria. Adicionar filtros (ex.: pesquisa por nome, categoria, contextos). Permitir ao usuário favoritar categorias.
- **Permissões e gestão**: Criar views e forms para que admins possam criar, renomear e excluir categorias. Garantir que apenas usuários com permissão apropriada possam gerenciar categorias.

### 3. Uploads e gerenciamento de arquivos
- **Barra de progresso e uploads grandes**: Implementar envio de arquivos em partes (chunked upload) usando API de streaming no DRF e JavaScript com fetch e `ReadableStream`. Exibir barra de progresso e permitir cancelamento. Ajustar `UploadArquivoAPIView` para montar o arquivo final ao receber todos os chunks.
- **Scanning de vírus**: Integrar um antivírus (ex.: ClamAV) ou serviço externo para varrer arquivos antes de disponibilizá‑los. Executar a varredura via Celery após upload; atualizar o status da mensagem (scanned, infected) e notificar o usuário se um arquivo for bloqueado.
- **Gerenciador de arquivos**: Adicionar página/modal para listar arquivos enviados em cada canal, com metadados (nome, tipo, tamanho, data). Permitir busca por nome, filtro por tipo e exclusão de arquivos (respeitando permissões e retenção).

### 4. Preferências avançadas de usuário
- **Temas e aparência**: Permitir ao usuário escolher temas (claro, escuro, alto contraste) que afetam cores do chat. Salvar a escolha em `UserChatSettings` e aplicar via classes CSS dinamicamente.
- **Busca salva**: Permitir que usuários salvem consultas de pesquisa frequentes (ex.: “@joao PDF 2025”) e acessem‑nas rapidamente. Criar modelo `SavedSearch` associado a `user`. Criar endpoints e UI (drop‑down ou modal) para salvar, listar e executar buscas salvas.
- **Resumo diário**: Oferecer opção de receber um resumo diário por e‑mail com highlights (canais com mais atividade, mensagens marcadas como importantes ou sinalizadas). Implementar tarefa Celery diária que gera e envia os resumos conforme as preferências.

### 5. Rate limiting e detecção de spam
- **Rate limiter por mensagem**: Adicionar limitação de envio de mensagens (ex.: máx. 60 mensagens/minuto por usuário) via DRF e Channels. Quando o limite for ultrapassado, responder com 429 Too Many Requests e bloquear envio por alguns minutos. Usar Redis para armazenar contadores temporários.
- **Detecção heurística de spam**: Implementar mecanismos simples para detectar padrões de spam (mensagens repetitivas, links suspeitos). Ao identificar possíveis spammers, notificar moderadores e, opcionalmente, aplicar medidas como mutar o usuário temporariamente. Registrar eventos no `ChatModerationLog`.
- **Feedback ao usuário**: No frontend, mostrar avisos quando o usuário estiver próximo do limite de envio ou se uma mensagem for sinalizada como spam, com orientações sobre boas práticas.

## Critérios de aceite
- As estatísticas fornecem dados corretos e são carregadas em menos de 2 segundos para intervalos de até 30 dias; dashboards são acessíveis e responsivos.
- Canais estão organizados por categoria na UI; criação/edição/exclusão de categorias respeita permissões e é refletida na navegação.
- Uploads grandes mostram barra de progresso, são reconstituídos corretamente e passam por varredura antivírus; arquivos infectados são bloqueados com mensagem adequada.
- Usuários podem personalizar tema, salvar buscas e receber resumos diários; todas as preferências são persistidas e podem ser atualizadas via API.
- Rate limiting impede spam sem prejudicar usuários legítimos; detecção de spam sinaliza casos suspeitos e notifica moderadores.
- Todos os testes continuam passando com cobertura de pelo menos 90%; métricas e logs dos novos recursos são exportados via Prometheus e Loki.
