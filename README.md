# Hubx

**Projeto Django 5 que conecta comunidades e empresas**, com suporte a perfis de usuário, notificações, multi-organizações e chat em tempo real via WebSocket.  
Inclui também geração de dados de teste e suporte a interface moderna com Tailwind CSS, HTMX e Font Awesome 6.

---

## 🚀 Funcionalidades

- Autenticação com formulários padrão Django
- Onboarding automático em `/accounts/onboarding/`
- Perfis personalizados
- Fórum e Chat integrados
- Suporte WebSocket via `channels` e `daphne`
- Sistema multi-tenant por organização
- Geração automatizada de massa de dados para testes

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

Use o comando abaixo para popular o banco com usuários, organizações, núcleos, empresas e eventos fictícios:

```bash
python manage.py generate_test_data --format json > seed.json
```

Você pode gerar também em CSV e aplicar filtros conforme necessário.

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

O módulo de chat registra mensagens trocadas entre usuários.  
Ao abrir uma conversa, as últimas 20 mensagens são carregadas automaticamente do banco de dados (`Mensagem`), mantendo o histórico.

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

---

## 🛠️ Correção de tokens e usuários

Execute o comando abaixo para normalizar usuários legados e garantir que todos tenham `UserType` e token:

```bash
python manage.py corrigir_base_token
```

> Evita falhas com CSRF e registro incompleto.

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
- **Gerar Token de Convite**: Permite criar tokens associados a organizações e núcleos.
- **Validar Token de Convite**: Valida tokens e associa ao usuário.

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
