from typing import Any, Dict, Iterable, Set, Type

from django.db.models import Avg, Model, Sum

from feed.models import Post


class DashboardCustomMetricService:
    SOURCES: Dict[str, tuple[Type[Model], Set[str]]] = {
        "posts": (Post, {"id", "organizacao_id"}),
    }

    @classmethod
    def register_source(
        cls, key: str, model: Type[Model], allowed_fields: Iterable[str]
    ) -> None:
        if key in cls.SOURCES:
            raise ValueError("Fonte já registrada")
        if not isinstance(model, type) or not issubclass(model, Model):
            raise TypeError("Model inválido")
        fields_set = set(allowed_fields)
        model_fields = {f.name for f in model._meta.get_fields()}
        invalid = fields_set - model_fields
        if invalid:
            raise ValueError(
                f"Campos inválidos: {', '.join(sorted(invalid))}"
            )
        cls.SOURCES[key] = (model, fields_set)

    AGGREGATIONS = {"count", "sum", "avg"}

    @classmethod
    def execute(cls, query_spec: Dict[str, Any], **params: Any) -> Any:
        source_key = query_spec.get("source")
        if source_key not in cls.SOURCES:
            raise ValueError("Fonte não permitida")
        model, fields = cls.SOURCES[source_key]
        qs = model.objects.all()
        for field, value in (query_spec.get("filters") or {}).items():
            if field not in fields:
                raise ValueError("Campo de filtro não permitido")
            if isinstance(value, str) and value.startswith("$"):
                param_name = value[1:]
                if param_name not in params:
                    raise ValueError(f"Parâmetro {param_name} ausente")
                value = params[param_name]
            qs = qs.filter(**{field: value})
        field = query_spec.get("field", "id")
        if field not in fields:
            raise ValueError("Campo não permitido")
        agg = query_spec.get("aggregation", "count")
        if agg not in cls.AGGREGATIONS:
            raise ValueError("Agregação inválida")
        if agg == "count":
            return qs.count()
        if agg == "sum":
            return qs.aggregate(total=Sum(field))["total"] or 0
        if agg == "avg":
            return qs.aggregate(total=Avg(field))["total"] or 0
        raise ValueError("Agregação inválida")


DEFAULT_ICON = "chart-bar"


def get_metrics_info(metrics: Iterable[Any]) -> Dict[str, Dict[str, str]]:
    info: Dict[str, Dict[str, str]] = {}
    for metric in metrics:
        query = metric.query_spec if isinstance(metric.query_spec, dict) else {}
        icon = query.get("icon", DEFAULT_ICON)
        info[metric.code] = {"label": metric.nome, "icon": icon}
    return info

