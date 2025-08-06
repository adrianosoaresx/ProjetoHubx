LINT_EXCLUDE=.venv,migrations,static

.PHONY: format vet test security all

# Executa tudo: formatadores, linters, testes e segurança
all: format vet test security

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
