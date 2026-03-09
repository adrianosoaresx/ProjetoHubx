# Hubx

**Projeto Django 5 que conecta comunidades e empresas**, com suporte a perfis de usuário, notificações e multi-organizações.  
Inclui também geração de dados de teste e suporte a interface moderna com Tailwind CSS, HTMX e Font Awesome 6.

---

## 🚀 Funcionalidades

- Autenticação com formulários padrão Django
- Cadastro multietapas em `/tokens/`
- Perfis personalizados
- Campo `redes_sociais` em JSON para registrar links de redes sociais
- Fórum integrado
- Suporte WebSocket via `channels` e `daphne`
- Sistema multi-tenant por organização
- Geração automatizada de massa de dados para testes
- Serviço central de notificações assíncronas
- Notificações push em tempo real via WebSocket
- Denúncia e moderação básica de posts do feed
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

Essa etapa garante que bibliotecas como Pillow estejam disponíveis no ambiente virtual.
O pacote `twilio` também é instalado para envios de WhatsApp; defina as variáveis
`TWILIO_SID`, `TWILIO_TOKEN` e `TWILIO_WHATSAPP_FROM` para habilitá-lo.

Para notificações push, defina também:

- `ONESIGNAL_APP_ID` e `ONESIGNAL_API_KEY` para o cliente OneSignal (`onesignal_sdk`).
- `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY` e `VAPID_CLAIMS_SUBJECT` usados pelo `pywebpush`.

### Pagamentos (Mercado Pago e PayPal)

O checkout usa o `django-payments` com o backend `django-payments-mercadopago`. Defina:

- `MERCADO_PAGO_ACCESS_TOKEN`: token privado para o backend do Mercado Pago.
- `PAYMENT_HOST`: host público usado pelo `django-payments` para montar URLs de retorno (por padrão, usamos o host do `FRONTEND_URL`).
- `MERCADO_PAGO_WEBHOOK_SECRET`: segredo opcional para validar a assinatura `X-Signature` recebida no webhook.
- `MERCADO_PAGO_RETURN_BASE_URL`: base usada para montar os links de retorno do checkout (padrão `https://hubx.space`).
- `MERCADO_PAGO_SUCCESS_URL`, `MERCADO_PAGO_FAILURE_URL`, `MERCADO_PAGO_PENDING_URL`: URLs completas para retorno de sucesso, falha e pendência (sobrepõem a base quando definidas).

Para habilitar PayPal como método adicional:

- `PAYPAL_CLIENT_ID` e `PAYPAL_CLIENT_SECRET`: credenciais da REST API do PayPal.
- `PAYPAL_API_URL`: endpoint base (use `https://api-m.sandbox.paypal.com` em testes).
- `PAYPAL_CURRENCY`: código da moeda (padrão `BRL`).
- `PAYPAL_WEBHOOK_SECRET`: segredo opcional para validar a assinatura `X-Paypal-Signature` recebida no webhook.

Endpoints envolvidos:

- `/pagamentos/checkout/` – formulário HTMX com fluxo simplificado usando o `django-payments`.
- `/pagamentos/mp/retorno/<status>/` – rota de retorno do Mercado Pago (`sucesso`, `falha` ou `pendente`).
- `https://hubx.space/pagamentos/webhook/mercadopago/` – recepção das notificações assíncronas (em dev use `http://127.0.0.1:8000/pagamentos/webhook/mercadopago/`). O endpoint valida o cabeçalho `X-Signature` com o valor de `MERCADO_PAGO_WEBHOOK_SECRET` e também está disponível em `/api/payments/mercadopago/webhook/` para compatibilidade com o painel do Mercado Pago.
- `/pagamentos/webhook/paypal/` – webhook opcional para sincronizar ordens do PayPal.

#### Banco de dados recomendado para pagamentos

Em produção, priorize PostgreSQL para reduzir contenção de locks durante o *polling* e o processamento concorrente de webhooks. O mecanismo de `SELECT FOR UPDATE` é usado para proteger as atualizações de `Transacao`/`Pedido` e pode ser controlado pela variável `PAGAMENTOS_ROW_LOCKS_ENABLED` (ativada por padrão). Em ambientes locais com SQLite, ajuste para `0/false/no/off` caso encontre `OperationalError` por falta de suporte a locks.

### Testes locais do webhook do Mercado Pago

- Ao expor o projeto via túnel (ex.: `ngrok http 8000`), configure a URL pública apontando para `http://127.0.0.1:8000/pagamentos/webhook/mercadopago/` (ou para `/api/payments/mercadopago/webhook/` caso o painel exija esse caminho).
- Defina `MERCADO_PAGO_WEBHOOK_SECRET` no `.env` com o mesmo valor registrado na configuração do webhook do Mercado Pago; a view valida o cabeçalho `X-Signature` enviado pelo provedor usando HMAC com esse segredo.
- Em produção, mantenha o endpoint configurado como `https://hubx.space/pagamentos/webhook/mercadopago/` para receber notificações oficiais.

Exemplo de configuração no `.env`:

```env
ONESIGNAL_APP_ID=2a1e1809-79e2-4fc0-8738-69f9a5d9d6c0
ONESIGNAL_API_KEY=sua-chave-api
```

Sem essas variáveis, os serviços de push permanecem indisponíveis.

Além disso, o Hubx depende do utilitário de linha de comando `ffmpeg` para gerar previews de vídeos.
Instale-o no sistema operacional (ex.: `sudo apt-get install ffmpeg` no Debian/Ubuntu ou
`brew install ffmpeg` no macOS) antes de enviar vídeos.

> Isso criará o usuário padrão `root` necessário para alguns comandos administrativos.

---

## 🔔 Notificações em tempo real e fallback

- O contador do sino usa WebSocket para receber broadcasts com o total de pendências e atualizar o `aria-label` traduzido exibido no cabeçalho. Quando WebSockets não estão disponíveis, o badge segue fazendo *polling* via HTMX (`hx-get` a cada 60s) para manter o mesmo número e texto de apoio.
- Para desativar WebSockets, defina `WEBSOCKETS_ENABLED=0` (o `start_server.py` já faz isso ao usar `runserver`). Ao rodar com ASGI (`uvicorn`/`daphne`), use `WEBSOCKETS_ENABLED=1` para habilitar o script `push_socket.js` incluído em `base.html`.
- Diagnóstico rápido: verifique no console do navegador se há logs de "WebSocket desabilitado ou indisponível"; confirme que o badge continua atualizando pelo atributo `hx-trigger="every 60s"`. Em ambientes de produção, garanta que o Channel Layer esteja configurado e que `WEBSOCKETS_ENABLED` corresponda ao modo do servidor.
- O sino do cabeçalho abre um dropdown acessível com as últimas notificações push (limitado às mais recentes). Clique, use Enter ou Espaço para abrir; navegue pelos itens com as setas ↑/↓ e feche com Esc ou clique fora. O conteúdo é carregado via HTMX na primeira abertura e se mantém sincronizado com o contador ao receber mensagens pelo WebSocket.

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
eventos, inscrições, feed, discussões, empresas e tokens.

---

## 💬 Discussões

O módulo `discussao` foi removido nesta fase. Métricas e links relacionados foram desativados.


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

> Isso gerará o CSS final otimizado para produção em `static/tailwind.css`.

---

## 🧩 Convenção oficial de componentes de template

Para padronizar a organização dos templates reutilizáveis entre os apps, o
projeto adota o seguinte caminho como padrão:

- `templates/<nome_app>/componentes/`

### Regras de localização

- Todo componente compartilhável de um app deve ficar em
  `templates/<nome_app>/componentes/`.
- Templates de página completa continuam no diretório convencional do app
  (por exemplo, `templates/<nome_app>/`).
- Componentes globais (reutilizados por múltiplos apps) podem permanecer em
  diretórios globais já existentes, como `templates/_components/` e
  `templates/_partials/`.

### Regras de nomenclatura

- **Pastas**: usar `snake_case` e nomes curtos orientados ao domínio
  (ex.: `componentes/filtros/`, `componentes/cards/`).
- **Arquivos de componente**: usar `snake_case.html` e nomes descritivos
  (ex.: `cabecalho_lista.html`, `card_evento_resumo.html`).
- **JavaScript de dashboard** (em `dashboard/static/dashboard/js/`): usar
  `kebab-case.js` para scripts de página (ex.: `admin-dashboard.js`,
  `consultor-dashboard.js`) e evitar variações em `snake_case`.
- Evitar prefixos genéricos como `novo_`, `tmp_` ou `teste_` em componentes
  versionados.

### Exemplo de uso em templates

```django
{# componente do app eventos #}
{% include "eventos/componentes/cabecalho_lista.html" with titulo=_("Eventos") %}

{# componente do app feed #}
{% include "feed/componentes/card_post_resumo.html" with post=post %}
```

Para detalhes de estilo e estrutura frontend, consulte também
`docs/style_guide_frontend.md`.

---

## 🧭 Front-end Next.js (pasta `app/`)

Este repositório inclui um front-end Next.js (pastas `app/`, `components/`, `hooks/`, `lib/`)
além do backend Django. **Confirme com o time se essa camada está em uso nos ambientes
de desenvolvimento/produção** antes de removê-la ou migrá-la para outro repositório.

### Como executar o front-end

1. Instale as dependências:

```bash
npm install
```

2. Defina a base da API do Django (ex.: `http://localhost:8000`):

```bash
export NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

3. Rode o servidor de desenvolvimento:

```bash
npm run dev
```

### Build e execução em produção

```bash
npm run build
npm run start
```

### Integração com o backend Django

- O front-end consome endpoints REST do Django, como o de confirmação de e-mail em
  `/api/accounts/accounts/confirm-email/`, usando a base definida em
  `NEXT_PUBLIC_API_BASE_URL`.
- Garanta que o backend esteja acessível no host configurado e que CORS esteja habilitado
  para o domínio do front-end quando rodar em ambientes separados.

---

## 🆕 Novos Fluxos Implementados

### Convites e Tokens
- **Gerar Token de Convite**: admins podem gerar um código único válido por 30 dias (`/tokens/convites/gerar/`).
- **Códigos de Autenticação**: geração e validação de OTP numérico para ações sensíveis (`/tokens/codigo/gerar/`).
- **2FA (TOTP)**: ativação opcional via aplicativo autenticador; exibe URL `otpauth://` para configuração inicial.
- **Segredo TOTP**: armazenado cifrado no formato Base32 (sem hashing irreversível) para permitir geração e verificação dos códigos.

### Autenticação em Dois Fatores (2FA)
- **Ativar 2FA**: Gera um segredo TOTP e valida o código enviado.

### Feed e Discussões
- **Feed**: Suporte a tipos de feed (`global`, `usuario`, `nucleo`, `evento`).
- **Discussões**: Categorias e tópicos com respostas e interações.

### Núcleos: Convites, Suspensão e Feed
- **Lookup público por UUID**: os endpoints detalhados de núcleo passam a usar `public_id` (`/api/nucleos/<public_id>/...`) como identificador público.
- **Convites de Núcleo**: admins geram convites com `POST /api/nucleos/<public_id>/convites/` e revogam com `DELETE /api/nucleos/<public_id>/convites/<convite_id>/`, respeitando a quota diária.
- **Suspensão de Membros**: coordenadores podem suspender ou reativar participantes (`POST /api/nucleos/<public_id>/membros/<user_id>/suspender` / `.../reativar`).
- **Membro Status**: consulta de papel e suspensão em `GET /api/nucleos/<public_id>/membro-status/`.
- **Feed do Núcleo**: membros ativos podem publicar via `POST /api/nucleos/<public_id>/posts/`.
- **Janela de transição (`<id>` legado)**: durante a migração, URLs antigas com `<id>` continuam aceitas somente por compatibilidade. As respostas desses acessos retornam `Deprecation: true` e header `Warning: 299 - "Deprecated API usage: use /api/nucleos/<public_id>/ instead of /api/nucleos/<id>/"`. Planeje atualização dos clientes e remoção do formato legado na próxima versão de API.


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
User.objects.filter_current_org(request.user.organizacao)
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

As APIs de importação foram desativadas. O envio de arquivos CSV ou XLSX deve
ser feito diretamente para a equipe financeira, que processa os dados
manualmente e acompanha os registros pelo Django Admin.

### Cobranças Recorrentes

Lançamentos mensais são gerados automaticamente no primeiro dia de cada mês.
Os valores padrão ficam em `Hubx/settings.py` e podem ser ajustados:

- `MENSALIDADE_ASSOCIACAO`
- `MENSALIDADE_NUCLEO`
- `MENSALIDADE_VENCIMENTO_DIA`


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
