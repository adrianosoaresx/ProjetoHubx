from validate_docbr import CNPJ

from empresas.factories import EmpresaFactory
from empresas.models import EmpresaChangeLog


def test_mascaracao_cnpj_log(admin_user):
    empresa = EmpresaFactory(usuario=admin_user, organizacao=admin_user.organizacao)
    cnpj_gen = CNPJ()
    novo_cnpj = cnpj_gen.mask(cnpj_gen.generate())
    antigo = empresa.cnpj
    empresa.cnpj = novo_cnpj
    empresa.save()
    log = EmpresaChangeLog.objects.filter(empresa=empresa, campo_alterado="cnpj").first()
    assert log is not None
    assert log.valor_antigo == f"***{antigo[-4:]}"
    assert log.valor_novo == f"***{novo_cnpj[-4:]}"
