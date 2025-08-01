from django.db.models import Q

from accounts.models import UserType
from .models import Empresa, Tag, EmpresaChangeLog


FILTRO_CAMPOS_Q = [
    "nome__icontains",
    "descricao__icontains",
    "cnpj__icontains",
    "municipio__icontains",
    "estado__icontains",
    "tipo__icontains",
    "tags__nome__icontains",
    "palavras_chave__icontains",
]


def filter_empresas(user, params):
    qs = (
        Empresa.objects.select_related("organizacao", "usuario")
        .prefetch_related("tags")
        .filter(deleted=False)
    )

    if user.is_superuser:
        pass
    elif user.user_type == UserType.ADMIN:
        qs = qs.filter(organizacao=user.organizacao)
    elif user.user_type in {UserType.COORDENADOR, UserType.NUCLEADO}:
        qs = qs.filter(usuario=user)
    else:
        return Empresa.objects.none()

    nome = params.get("nome")
    municipio = params.get("municipio")
    estado = params.get("estado")
    organizacao_id = params.get("organizacao_id")
    palavras = params.get("palavras_chave")
    tags = params.getlist("tags") if hasattr(params, "getlist") else params.get("tags")
    q = params.get("q")

    if nome:
        qs = qs.filter(nome__icontains=nome)
    if municipio:
        qs = qs.filter(municipio__icontains=municipio)
    if estado:
        qs = qs.filter(estado__iexact=estado)
    if organizacao_id:
        qs = qs.filter(organizacao_id=organizacao_id)
    if palavras:
        qs = qs.filter(palavras_chave__icontains=palavras)
    if tags:
        qs = qs.filter(tags__in=tags)
    if q:
        palavras_busca = [p.strip() for p in q.split() if p.strip()]
        for palavra in palavras_busca:
            q_obj = Q()
            for campo in FILTRO_CAMPOS_Q:
                q_obj |= Q(**{campo: palavra})
            qs = qs.filter(q_obj)
    return qs.distinct()


def list_all_tags():
    return Tag.objects.all()


LOG_FIELDS = [
    "nome",
    "cnpj",
    "tipo",
    "municipio",
    "estado",
    "descricao",
    "palavras_chave",
    "logo",
]


def registrar_alteracoes(usuario, empresa, old_data):
    """Registra alterações nos campos relevantes."""
    for campo in LOG_FIELDS:
        antigo = old_data.get(campo)
        novo = getattr(empresa, campo)
        if antigo != novo:
            if campo == "cnpj" and antigo:
                antigo = f"***{antigo[-4:]}"
            EmpresaChangeLog.objects.create(
                empresa=empresa,
                usuario=usuario,
                campo_alterado=campo,
                valor_antigo=antigo or "",
                valor_novo=novo or "",
            )
