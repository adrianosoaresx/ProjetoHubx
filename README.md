# Hubx

**Projeto Django 5 que conecta comunidades e empresas**, com suporte a perfis de usuário, notificações, multi-organizações e chat em tempo real via WebSocket.  
Inclui também geração de dados de teste e suporte a interface moderna com Tailwind CSS, HTMX e Font Awesome 6.

---

## 🚀 Funcionalidades

- Autenticação com formulários padrão Django
- Onboarding automático em `/accounts/onboarding/`
- Perfis personalizados
- Campo `redes_sociais` em JSON para registrar links de redes sociais
- Fórum e Chat integrados
- Suporte WebSocket via `channels` e `daphne`
- Sistema multi-tenant por organização
- Geração automatizada de massa de dados para testes
- Serviço central de notificações assíncronas
- Notificações push em tempo real via WebSocket
- Automação de inadimplências e API para lançamentos financeiros
- Denúncia e moderação básica de posts do feed
- Dashboard com métricas do feed e gráficos interativos
- Rotação automática de tokens de API

### Limitações de Design

Algumas telas ainda estão em processo de migração para Tailwind CSS e HTMX. Isso
significa que partes da interface podem apresentar diferenças visuais ou falta de
feedback. Caso encontre problemas, abra uma issue ou envie um pull request.

---

### Uso do campo `redes_sociais`

No formulário de perfil é possível informar um JSON com os links de redes sociais. Exemplo:

```json
{
  "github": "https://github.com/seuuser",
  "linkedin": "https://br.linkedin.com/in/seuuser"
}
```

O campo é opcional e é armazenado como `JSONField` no modelo `User`.

---

## ⚙️ Configuração Inicial

Antes de executar comandos de teste ou popular dados, instale as dependências e aplique as migrações:

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # dependências de desenvolvimento
python manage.py migrate
```

Essa etapa garante que bibliotecas como Pillow e clamd estejam disponíveis no ambiente virtual.
O pacote `twilio` também é instalado para envios de WhatsApp; defina as variáveis
`TWILIO_SID`, `TWILIO_TOKEN` e `TWILIO_WHATSAPP_FROM` para habilitá-lo.

Além disso, o Hubx depende do utilitário de linha de comando `ffmpeg` para gerar previews de vídeos.
Instale-o no sistema operacional (ex.: `sudo apt-get install ffmpeg` no Debian/Ubuntu ou
`brew install ffmpeg` no macOS) antes de enviar vídeos.

> Isso criará o usuário padrão `root` necessário para alguns comandos administrativos.

---

### 🧯 Erro comum: `No module named 'channels'`

Se ao executar:

```bash
python manage.py check
```

você receber o erro acima, é porque as dependências não foram instaladas corretamente.  
Verifique o ambiente virtual e reinstale os pacotes com:

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # se estiver desenvolvendo
```

---

## 🧪 Gerar Dados de Teste

Para popular o banco de forma completa, execute o script abaixo:

```bash
python scripts/populate_test_data.py
```

Ele cria organizações, núcleos, **todos os perfis de usuários** (incluindo o superusuário `root`),
eventos, inscrições, feed, conversas de chat, discussões, empresas, parcerias e tokens.

---

## 💬 Discussões

O módulo `discussao` permite a criação de tópicos e respostas por usuários autenticados.
Acesse:

```
/discussao/
```

para visualizar categorias e interações.

Na listagem de tópicos é possível ordenar por mais recentes, mais comentados ou mais votados. Na API, utilize `?ordering=score` para retornar os mais votados.

---

## 📡 Chat (WebSocket)

O módulo de chat registra mensagens trocadas entre usuários. Acesse `/chat/` para ver os canais disponíveis agrupados por contexto (privado, núcleo, evento, organização). Cada item exibe o número de mensagens não lidas e o preview da última mensagem. Ao abrir um canal é possível visualizar mensagens fixadas, reagir com emojis e enviar anexos. A interface usa HTMX + WebSocket e possui *fallback* para quando o JavaScript está desabilitado.

### Moderação e exportação

Mensagens podem ser sinalizadas pelos participantes através do endpoint `POST /api/chat/channels/<canal>/messages/<id>/flag/` ou via WebSocket com `{"tipo": "flag"}`. Após três sinalizações a mensagem é ocultada automaticamente. Moderadores acessam `/chat/moderacao/` para revisar os conteúdos reportados e podem aprovar (`POST /api/chat/moderacao/messages/<id>/approve/`) ou remover (`POST /api/chat/moderacao/messages/<id>/remove/`) definitivamente.

Administradores dos canais podem exportar o histórico acessando o botão *Exportar histórico* na página do canal ou via API `GET /api/chat/channels/<id>/export/` com parâmetros `formato` (`json` ou `csv`), intervalo de datas (`inicio`/`fim`) e tipos de mensagem (`tipos`). O arquivo gerado fica disponível em `media/chat_exports/`.

O módulo expõe métricas Prometheus em `/metrics`, incluindo `chat_mensagens_sinalizadas_total`, `chat_mensagens_ocultadas_total` e `chat_exportacoes_total`.

Para anexos existe o endpoint `POST /api/chat/upload/` que recebe o arquivo e retorna JSON com `{"tipo": tipo, "url": url}` a ser enviado pelo WebSocket. Notificações em tempo real podem ser recebidas conectando-se a `/ws/chat/notificacoes/`; cada evento inclui o título do canal e um resumo da mensagem, podendo ser marcado como lido via `POST /api/chat/notificacoes/<id>/ler/`.

Uma métrica `chat_websocket_latency_seconds` registra a latência (p95) das notificações enviadas pelo WebSocket.

![Demonstração do chat](docs/chat-demo.png)

Para que o WebSocket funcione:

1. Instale o pacote `daphne` (já listado em `requirements.txt`).
2. Execute um servidor Redis local em `localhost:6379`.
3. Rode o servidor com:

```bash
python manage.py runserver
```

> O `runserver` já usa o servidor ASGI do Django quando `channels` está instalado.

Para rodar manualmente com `daphne`:

```bash
daphne Hubx.asgi:application -b 0.0.0.0 -p 8000
```

### Produção
Em produção defina `ALLOWED_HOSTS` com o domínio usado e configure o proxy para aceitar conexões `wss://`. O endpoint do WebSocket segue o padrão `/ws/chat/<id>/`. Exemplo de configuração no `settings.py`:

```python
ALLOWED_HOSTS = ["seu-dominio.com"]
CSRF_TRUSTED_ORIGINS = ["https://seu-dominio.com"]
```

Certifique-se também de liberar o esquema `wss://` no servidor ou proxy reverso.

### Tasks de exportação

As exportações de histórico são processadas de forma assíncrona. Para
acompanhar o progresso e gerar os arquivos é necessário executar um
worker Celery apontando para o mesmo Redis:

```bash
celery -A Hubx worker -l INFO
```

Os arquivos gerados ficarão disponíveis em `media/chat_exports/` e o
endpoint `/api/chat/channels/<id>/export/` aceita os parâmetros
`inicio`, `fim` e `tipos` para filtrar o conteúdo exportado.

---

## 🛠️ Correção de tokens e usuários

Execute o comando abaixo para normalizar usuários legados e garantir que todos possuam o campo `user_type` e token:

```bash
python manage.py corrigir_base_token
```

> Evita falhas com CSRF e registro incompleto.
> O antigo modelo `UserType` foi removido; agora o tipo lógico é definido pelo campo `user_type` no modelo `User`.

---

### 🛡️ Exemplo de formulário seguro:

```html
<form method="post">
    {% csrf_token %}
    {{ form.as_p }}
</form>
```

### 📄 Exemplo de view com `render`:

```python
from django.shortcuts import render


def exemplo_view(request):
    return render(request, "pagina.html")
```

---

## 🎨 Compilar o Tailwind CSS

Após instalar as dependências e aplicar as migrações, execute:

```bash
npm install
npm run build
```

> Isso gerará o CSS final otimizado para produção em `static/css/`.

---

## 🆕 Novos Fluxos Implementados

### Convites e Tokens
- **Gerar Token de Convite**: admins podem gerar um código único válido por 30 dias (`/tokens/convites/gerar/`).
- **Validar Token de Convite**: o usuário informa o código em `/tokens/convites/validar/`; se estiver "novo" e não expirado, o token é associado e marcado como usado.
- **Códigos de Autenticação**: geração e validação de OTP numérico para ações sensíveis (`/tokens/codigo/gerar/`).
- **2FA (TOTP)**: ativação opcional via aplicativo autenticador; exibe URL `otpauth://` para configuração inicial.

### Autenticação em Dois Fatores (2FA)
- **Ativar 2FA**: Gera um segredo TOTP e valida o código enviado.

### Feed e Discussões
- **Feed**: Suporte a tipos de feed (`global`, `usuario`, `nucleo`, `evento`).
- **Discussões**: Categorias e tópicos com respostas e interações.

### Núcleos: Convites, Suspensão e Feed
- **Convites de Núcleo**: admins geram convites com `POST /api/nucleos/<id>/convites/` e revogam com `DELETE /api/nucleos/<id>/convites/<convite_id>/`, respeitando a quota diária.
- **Suspensão de Membros**: coordenadores podem suspender ou reativar participantes (`POST /api/nucleos/<id>/membros/<user_id>/suspender` / `.../reativar`).
- **Membro Status**: consulta de papel e suspensão em `GET /api/nucleos/<id>/membro-status/`.
- **Feed do Núcleo**: membros ativos podem publicar via `POST /api/nucleos/<id>/posts/`.


### Dashboard
- **Dashboard**: Estatísticas de eventos, inscrições e interações.
- É possível registrar novas fontes de dados para métricas em tempo de execução
  com `DashboardCustomMetricService.register_source("chave", Modelo, {"campo"})`.

### Parcerias de Eventos
- **CRUD Web**: gerenciamento de `ParceriaEvento` em `/agenda/parcerias/` com criação, edição e exclusão restritas a administradores e coordenadores.

### Monitoramento de Desempenho
- **Django‑Silk** disponível em `/silk/` para análise de tempo de resposta das listagens e APIs.

---

## 🔧 Configuração de Redis/Celery

Para tarefas assíncronas, configure Redis e Celery:

1. Instale Redis:
   ```bash
   sudo apt install redis-server
   ```

2. Configure Celery no projeto:
   ```bash
   pip install celery[redis]
   ```

3. Inicie o worker:
   ```bash
   celery -A Hubx worker -B --loglevel=info
   ```

As tarefas `enviar_relatorios_diarios` e `enviar_relatorios_semanais` são agendadas via
*Celery beat* utilizando `crontab`. O agendamento consulta os horários definidos
em `ConfiguracaoConta`. Para registrar intervalos personalizados é possível
utilizar o **django-celery-beat**, criando `PeriodicTask` com o `crontab`
apropriado para cada combinação de dia e hora desejada.

Variáveis de ambiente utilizadas para envio:

```bash
export NOTIFICATIONS_EMAIL_API_URL=https://example
export NOTIFICATIONS_EMAIL_API_KEY=token
export NOTIFICATIONS_WHATSAPP_API_URL=https://example
export NOTIFICATIONS_WHATSAPP_API_KEY=token
```

---

## 🏢 Estratégia Multi-tenant (Organizações)

- Cada usuário pertence a **uma única organização**.
- Consultas filtram dados via:

```python
User.objects.filter_current_org(request.user.organization)
```

- Superusuários não possuem organização associada e visualizam todos os dados.
- A administração respeita automaticamente a organização do usuário logado.

---

## 📂 Estrutura Recomendada

```text
ProjetoHubx/
├── apps/                  # Apps Django modularizados
├── templates/             # Templates HTML com Tailwind
├── static/                # CSS compilado e assets
├── manage.py
├── requirements.txt       # Dependências básicas
├── requirements-dev.txt   # Dependências de desenvolvimento
├── AGENTS.md              # Manifesto para agentes Codex
├── README.md              # Este arquivo
```

---

## 📌 Requisitos

- Python 3.10+
- Django 5.2.2
- channels, daphne
- Tailwind CSS 3
- HTMX
- Font Awesome 6
- Pillow
- clamd

---

> Para mais informações, consulte o arquivo `AGENTS.md` e utilize agentes como `refactor_bot`, `test_guru`, `seed_bot` e `ux_polish` para acelerar o desenvolvimento.

# Qualidade de Código

make format    # corrige estilo automaticamente
make vet       # verifica padrões, imports, etc.
make test      # roda testes com pytest
pytest tests/configuracoes/test_accessibility.py  # testa acessibilidade com axe-core
pytest tests/notificacoes/test_summary_tasks.py   # testa integrações Celery
make security  # roda análise de segurança com bandit
make           # roda tudo acima

### Importação de Pagamentos

```
POST /api/financeiro/importar-pagamentos/
Multipart: file=<planilha.csv>

POST /api/financeiro/importar-pagamentos/confirmar
Payload: {"id": "<token>"}
```

### Cobranças Recorrentes

Lançamentos mensais são gerados automaticamente no primeiro dia de cada mês.
Os valores padrão ficam em `Hubx/settings.py` e podem ser ajustados:

- `MENSALIDADE_ASSOCIACAO`
- `MENSALIDADE_NUCLEO`
- `MENSALIDADE_VENCIMENTO_DIA`

Consulte `docs/financeiro.md` para detalhes.

---

## 📧 Preferências de Notificação

As preferências de cada usuário podem ser consultadas e atualizadas via API.

### Exemplo de requisição

```
GET /api/configuracoes/configuracoes-conta/
```

Resposta:

```json
{
  "receber_notificacoes_email": true,
  "frequencia_notificacoes_email": "imediata",
  "receber_notificacoes_whatsapp": false,
  "frequencia_notificacoes_whatsapp": "diaria",
  "receber_notificacoes_push": true,
  "frequencia_notificacoes_push": "imediata",
  "idioma": "pt-BR",
  "tema": "claro",
  "hora_notificacao_diaria": "08:00:00",
  "hora_notificacao_semanal": "08:00:00",
  "dia_semana_notificacao": 0
}
```

Atualizações podem ser feitas com `PUT` ou `PATCH` no mesmo endpoint.

Para receber notificações push em navegadores, registre o token do service worker:

```bash
curl -X POST -H "Authorization: Token <seu_token>" \
  -H "Content-Type: application/json" \
  -d '{"token": "TOKEN_DO_BROWSER"}' \
  http://localhost:8000/api/notificacoes/push-subscription/
```

Para remover a inscrição:

```bash
curl -X DELETE -H "Authorization: Token <seu_token>" \
  -d '{"token": "TOKEN_DO_BROWSER"}' \
  http://localhost:8000/api/notificacoes/push-subscription/
```

Mensagens em tempo real são enviadas pelo WebSocket em `/ws/notificacoes/`. É possível
testar localmente com [wscat](https://github.com/websockets/wscat):

```bash
wscat -c ws://localhost:8000/ws/notificacoes/
```

### Histórico de notificações

O usuário pode acompanhar suas mensagens enviadas em `/notificacoes/historico/`.

### Métricas e logs das tarefas

As tarefas Celery de notificações expõem métricas Prometheus como
`notificacoes_enviadas_total`, `notificacoes_falhadas_total` e
`notificacao_task_duration_seconds`. Para coletá-las, execute o worker com o
`PrometheusExporter` habilitado.

### Esquema OpenAPI

O esquema da API pode ser gerado com:

```bash
make openapi
```

O arquivo `openapi-schema.yml` será criado na raiz do projeto.

