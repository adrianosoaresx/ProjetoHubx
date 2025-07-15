import os
import django
import pytest
from django.conf import settings
from django.test.utils import get_runner, setup_test_environment, teardown_test_environment
import logging
import threading

# Configurar o Django antes de qualquer operação
if not django.apps.apps.ready:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Hubx.settings")
    django.setup()

# Configurar logging para depuração
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Variável global para controlar o estado do ambiente de teste
test_environment_setup = False

# Bloqueio para evitar execuções simultâneas
test_environment_lock = threading.Lock()

@pytest.fixture(scope="session", autouse=True)
def setup_django():
    """Configura o ambiente do Django para os testes."""
    global test_environment_setup
    with test_environment_lock:
        if not test_environment_setup:
            logger.debug("Iniciando configuração do ambiente de teste.")
            settings.DEBUG = False
            setup_test_environment()
            test_environment_setup = True
            logger.debug("Ambiente de teste configurado com sucesso.")
        else:
            logger.debug("Ambiente de teste já configurado.")
    yield
    with test_environment_lock:
        if test_environment_setup:
            logger.debug("Desmontando o ambiente de teste.")
            teardown_test_environment()
            test_environment_setup = False
            logger.debug("Ambiente de teste desmontado com sucesso.")

@pytest.fixture(scope="function", autouse=True)
def enable_db_access_for_all_tests(db):
    """Habilita o acesso ao banco de dados para todos os testes."""
    pass

def pytest_configure():
    """Configura o Django para os testes, garantindo inicialização única."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Hubx.settings")
    if not settings.configured:
        django.setup()
