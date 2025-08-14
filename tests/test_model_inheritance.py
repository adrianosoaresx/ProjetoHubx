import importlib

import pytest
from django.apps import apps
from django.db import models
from rest_framework.serializers import ModelSerializer

from core.models import SoftDeleteModel


@pytest.fixture(scope="module")
def serialized_models() -> set[type[models.Model]]:
    """Return models referenced by DRF ModelSerializers."""
    # Import serializers for all apps so subclasses are registered
    for app_config in apps.get_app_configs():
        try:
            importlib.import_module(f"{app_config.name}.serializers")
        except ModuleNotFoundError:
            pass

    def all_subclasses(cls: type) -> set[type]:
        return {
            subclass
            for subclass in cls.__subclasses__()
            for subclass in all_subclasses(subclass) | {subclass}
        }

    models_found: set[type[models.Model]] = set()
    for serializer in all_subclasses(ModelSerializer):
        model = getattr(getattr(serializer, "Meta", object), "model", None)
        if model is not None:
            models_found.add(model)
    return models_found


def test_models_use_timestamp_and_soft_delete(serialized_models: set[type[models.Model]]) -> None:
    """Ensure concrete models include TimeStampedModel and SoftDeleteModel when required."""
    for model in apps.get_models():
        if model._meta.abstract:
            continue
        if model.__module__.startswith(("django.", "rest_framework", "silk")):
            continue
        if model.__name__.startswith("Historical"):
            continue

        assert any(
            base.__name__ == "TimeStampedModel" for base in model.__mro__
        ), f"{model.__name__} must inherit TimeStampedModel"

        requires_soft_delete = False
        if model in serialized_models:
            for rel in model._meta.related_objects:
                if isinstance(rel, (models.ManyToOneRel, models.OneToOneRel)) and rel.related_model is not model:
                    if any(base.__name__ == "SoftDeleteModel" for base in rel.related_model.__mro__):
                        requires_soft_delete = True
                        break
        if requires_soft_delete:
            assert issubclass(
                model, SoftDeleteModel
            ), f"{model.__name__} must inherit SoftDeleteModel"
