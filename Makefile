LINT_EXCLUDE=.venv,migrations,static

.PHONY: format vet test security collectstatic all

# Executa tudo: formatadores, linters, testes, segurança e coleta de assets
all: format vet test security collectstatic

# Formata o código
format:
	ruff format .
	black .

# Analisa estilo e importações
vet:
	ruff check .
	isort .

# Executa os testes unitários (exceto lentos)
test:
	pytest -m "not slow"

# Verificação de segurança com Bandit
security:
        bandit -r . --exclude $(LINT_EXCLUDE) --severity-level medium -f short

.PHONY: openapi
openapi:
        python manage.py spectacular --file openapi-schema.yml

.PHONY: collectstatic
collectstatic:
	python manage.py collectstatic --noinput
