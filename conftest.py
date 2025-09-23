import os
import django
import pytest
from django.conf import settings
from django.core.files import storage as django_storage
from django.test.utils import get_runner, setup_test_environment, teardown_test_environment
from django.utils.module_loading import import_string
import logging
import threading


if not hasattr(django_storage, "get_storage_class"):
    def _get_storage_class(import_path: str):
        return import_string(import_path)

    django_storage.get_storage_class = _get_storage_class  # type: ignore[attr-defined]

# Configurar o Django antes de qualquer operação
if not django.apps.apps.ready:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Hubx.settings")
    django.setup()
    settings.ROOT_URLCONF = "tests.urls"
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True
    settings.MIGRATION_MODULES = {"feed": None}

# Configurar logging para depuração
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Variável global para controlar o estado do ambiente de teste
test_environment_setup = False

# Bloqueio para evitar execuções simultâneas
test_environment_lock = threading.Lock()


# Ajuste para evitar chamadas redundantes de setup_test_environment
@pytest.fixture(scope="session", autouse=True)
def setup_django():
    """Configura o ambiente do Django para os testes."""
    global test_environment_setup
    with test_environment_lock:
        if not test_environment_setup:
            logger.debug("Iniciando configuração do ambiente de teste.")
            settings.DEBUG = False
            try:
                setup_test_environment()
                test_environment_setup = True
                logger.debug("Ambiente de teste configurado com sucesso.")
            except RuntimeError as e:
                logger.error(f"Erro ao configurar o ambiente de teste: {e}")
        else:
            logger.debug("Ambiente de teste já configurado.")
    yield
    with test_environment_lock:
        if test_environment_setup:
            logger.debug("Desmontando o ambiente de teste.")
            try:
                teardown_test_environment()
                test_environment_setup = False
                logger.debug("Ambiente de teste desmontado com sucesso.")
            except RuntimeError as e:
                logger.error(f"Erro ao desmontar o ambiente de teste: {e}")


@pytest.fixture(scope="function", autouse=True)
def enable_db_access_for_all_tests(db):
    """Habilita o acesso ao banco de dados para todos os testes."""
    pass


@pytest.fixture
def admin_user(django_user_model):
    """Cria um superusuário compatível com o modelo customizado."""
    return django_user_model.objects.create_superuser(
        email="admin@example.com",
        username="admin",
        password="password",
    )


def pytest_configure():
    """Configura o Django para os testes, garantindo inicialização única."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Hubx.settings")
    if not settings.configured:
        django.setup()
