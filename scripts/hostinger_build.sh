#!/usr/bin/env bash
set -euo pipefail

# 1) Dependências Python
pip install -r requirements.txt

# 2) Binários do gettext exigidos pelo compilemessages
for bin in msgfmt msgmerge xgettext; do
  if ! command -v "$bin" >/dev/null 2>&1; then
    echo "Erro: binário '$bin' não encontrado. Instale gettext no ambiente de build." >&2
    exit 1
  fi
done

# 3) Compilação de traduções (deve ocorrer antes do startup)
python manage.py compilemessages

# 4) Garante que o artefato tenha .mo esperados
if ! find . -type f -path "*/locale/*/LC_MESSAGES/django.mo" -print -quit | grep -q .; then
  echo "Erro: nenhum arquivo django.mo foi gerado em */locale/*/LC_MESSAGES/." >&2
  exit 1
fi

# 5) Assets estáticos
python manage.py collectstatic --noinput
