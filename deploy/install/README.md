# Pacote de instalação do Hubx

Este diretório reúne arquivos auxiliares para gerar um pacote de implantação e automatizar a configuração do Hubx em um servidor Linux.

## 1. Preparar variáveis de ambiente

1. Copie `deploy/install/env.production.example` para `.env` na raiz do projeto.
2. Ajuste as variáveis conforme sua infraestrutura (PostgreSQL, Redis, credenciais de APIs, etc.).

As variáveis são carregadas automaticamente pelo Django, pelo Celery e pelos processos ASGI/WSGI através do arquivo `.env`.

## 2. Gerar o pacote de instalação

Execute no ambiente de desenvolvimento:

```bash
bash scripts/build_install_package.sh
```

O comando gera um arquivo `dist/hubx-<timestamp>-<commit>.tar.gz` pronto para ser enviado ao servidor. O script usa `git archive`, portanto apenas arquivos versionados são incluídos.

## 3. Instalar no servidor

1. Copie o arquivo `.tar.gz` e o `.env` configurado para o servidor (ex.: `/opt/hubx`).
2. Extraia o pacote: `tar -xzf hubx-*.tar.gz`.
3. Dentro da pasta extraída, execute:

```bash
bash deploy/install/install.sh
```

O script cria o ambiente virtual, instala as dependências Python e Node, aplica migrações e coleta os arquivos estáticos.

## 4. Publicar o serviço

Após o setup:

- Inicie um servidor ASGI (ex.: `uvicorn Hubx.asgi:application --host 0.0.0.0 --port 8000`).
- Configure um *process manager* (systemd, supervisord) e agende o worker Celery usando as variáveis `CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND`.
- Garanta que o serviço de Redis e o banco de dados estejam acessíveis.

Consulte também o `README.md` principal para detalhes adicionais (FFmpeg, notificações, etc.).
