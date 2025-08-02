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
python manage.py migrate
```

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

---

## 📡 Chat (WebSocket)

O módulo de chat registra mensagens trocadas entre usuários. Acesse `/chat/` para ver os canais disponíveis agrupados por contexto (privado, núcleo, evento, organização). Cada item exibe o número de mensagens não lidas e o preview da última mensagem. Ao abrir um canal é possível visualizar mensagens fixadas, reagir com emojis e enviar anexos. A interface usa HTMX + WebSocket e possui *fallback* para quando o JavaScript está desabilitado.

### Moderação e exportação

Mensagens podem ser sinalizadas pelos participantes através do endpoint `POST /api/chat/channels/<canal>/messages/<id>/flag/` ou via WebSocket com `{"tipo": "flag"}`. Após três sinalizações a mensagem é ocultada automaticamente. Moderadores acessam `/chat/moderacao/` para revisar os conteúdos reportados e podem aprovar (`POST /api/chat/moderacao/messages/<id>/approve/`) ou remover (`POST /api/chat/moderacao/messages/<id>/remove/`) definitivamente.

Administradores dos canais podem exportar o histórico acessando o botão *Exportar histórico* na página do canal ou via API `GET /api/chat/channels/<id>/export/` com parâmetros `formato` (`json` ou `csv`), intervalo de datas (`inicio`/`fim`) e tipos de mensagem (`tipos`). O arquivo gerado fica disponível em `media/chat_exports/`.

O módulo expõe métricas Prometheus em `/metrics`, incluindo `chat_mensagens_sinalizadas_total`, `chat_mensagens_ocultadas_total` e `chat_exportacoes_total`.

![Demonstração do chat](docs/chat-demo.png)

Para que o WebSocket funcione:

1. Instale o pacote `daphne` (já listado em `requirements.txt`).
2. Rode o servidor com:

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

### Dashboard
- **Dashboard**: Estatísticas de eventos, inscrições e interações.

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
   celery -A Hubx worker --loglevel=info
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
├── requirements.txt
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

---

> Para mais informações, consulte o arquivo `AGENTS.md` e utilize agentes como `refactor_bot`, `test_guru`, `seed_bot` e `ux_polish` para acelerar o desenvolvimento.

# Qualidade de Código

make format    # corrige estilo automaticamente
make vet       # verifica padrões, imports, etc.
make test      # roda testes com pytest
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

