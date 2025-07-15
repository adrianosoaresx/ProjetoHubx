@echo off
echo Verificando segurança com Bandit...
bandit -r . ^
  --exclude .venv,*/migrations/*,static,media,__pycache__,tests ^
  -f txt ^
  -lll
pause
