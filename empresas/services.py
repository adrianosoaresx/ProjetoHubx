"""Serviços auxiliares para o módulo de empresas.

Este arquivo contém funções de busca e registro de alterações. Ao manter a
lógica de busca isolada em um serviço garantimos melhor testabilidade e
manutenção das views.
"""

from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.db import connection
from django.db.models import Q, Count
from django.utils import timezone

from accounts.models import UserType

from .models import Empresa, EmpresaChangeLog, Tag
from .tasks import validar_cnpj_async
from services.cnpj_validator import CNPJValidationError, validar_cnpj


def search_empresas(user, params):
    """Aplica filtros a partir dos parâmetros de consulta.

    Parâmetros aceitos: ``nome``, ``municipio``, ``estado``, ``tags``,
    ``organizacao_id`` e ``q`` (busca textual). O parâmetro
    ``mostrar_excluidas`` só é respeitado para administradores,
    exibindo registros com ``deleted=True``.
    """

    mostrar_excluidas = params.get("mostrar_excluidas")
    if mostrar_excluidas == "1" and user.user_type == UserType.ADMIN:
        qs = Empresa.all_objects.select_related("organizacao", "usuario").prefetch_related("tags")
    else:
        qs = (
            Empresa.objects.select_related("organizacao", "usuario").prefetch_related("tags")
        )
        qs = qs.filter(deleted=False)

    if user.is_superuser:
        pass
    elif user.user_type == UserType.ADMIN:
        # Admins have visibility over all companies in their organization
        qs = qs.filter(organizacao=user.organizacao)
    elif user.user_type in {UserType.COORDENADOR, UserType.NUCLEADO}:
        # Coordinators and nucleados are limited to companies they created
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
        if not isinstance(tags, (list, tuple, set)):
            tags = [tags]
        qs = (
            qs.filter(tags__in=tags)
            .annotate(
                num_tags=Count("tags", filter=Q(tags__in=tags), distinct=True)
            )
            .filter(num_tags=len(tags))
            .distinct()
        )
    if q:
        if connection.vendor == "postgresql":
            vector = (
                SearchVector("nome", weight="A")
                + SearchVector("cnpj", weight="A")
                + SearchVector("descricao", weight="B")
                + SearchVector("palavras_chave", weight="B")
                + SearchVector("tags__nome", weight="C")
            )
            query = SearchQuery(q)
            qs = qs.annotate(rank=SearchRank(vector, query)).filter(rank__gt=0).order_by("-rank")
        else:
            qs = qs.filter(Q(search_vector__icontains=q) | Q(cnpj__icontains=q))
    return qs.distinct()


# Backwards compatibility ----------------------------------------------------
#
# ``filter_empresas`` era o nome antigo do serviço de busca. Mantemos um alias
# para evitar que importações existentes quebrem caso ainda utilizem esse nome.
filter_empresas = search_empresas


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
    "tags",
]


def registrar_alteracoes(usuario, empresa, old_data):
    """Registra alterações nos campos relevantes."""
    for campo in LOG_FIELDS:
        if campo == "tags":
            antigo = ", ".join(old_data.get("tags", []))
            novo_lista = list(empresa.tags.values_list("nome", flat=True))
            novo = ", ".join(novo_lista)
            if set(old_data.get("tags", [])) != set(novo_lista):
                EmpresaChangeLog.objects.create(
                    empresa=empresa,
                    usuario=usuario,
                    campo_alterado=campo,
                    valor_antigo=antigo,
                    valor_novo=novo,
                )
            continue
        antigo = old_data.get(campo)
        novo = getattr(empresa, campo)
        if antigo != novo:
            if campo == "cnpj":
                if antigo:
                    antigo = f"***{antigo[-4:]}"
                if novo:
                    novo = f"***{str(novo)[-4:]}"
            EmpresaChangeLog.objects.create(
                empresa=empresa,
                usuario=usuario,
                campo_alterado=campo,
                valor_antigo=antigo or "",
                valor_novo=novo or "",
            )


def verificar_cnpj(cnpj: str) -> dict:
    """Valida um CNPJ utilizando serviço externo.

    Em caso de indisponibilidade do serviço, a validação é enfileirada para
    execução assíncrona via Celery.
    """

    try:
        valido, fonte = validar_cnpj(cnpj)
    except CNPJValidationError:
        validar_cnpj_async.delay(cnpj)
        return {"valido": False, "fonte": "", "validado_em": None}
    return {"valido": valido, "fonte": fonte, "validado_em": timezone.now()}
