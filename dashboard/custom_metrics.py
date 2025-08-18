from typing import Any, Dict

from django.db.models import Avg, Sum

from feed.models import Post


class DashboardCustomMetricService:
    SOURCES: Dict[str, tuple] = {
        "posts": (Post, {"id", "organizacao_id"}),
    }

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

