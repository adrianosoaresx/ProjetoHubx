from __future__ import annotations

from importlib import import_module
from typing import List

import logging
from django.db import models

from feed.domain.plugins import FeedPlugin
from feed.models import FeedPluginConfig

logger = logging.getLogger(__name__)


def load_plugins_for(organizacao: models.Model) -> List[FeedPlugin]:
    """Carrega instâncias de plugins registrados para uma organização."""
    plugins: List[FeedPlugin] = []
    for config in FeedPluginConfig.objects.filter(organizacao=organizacao):
        try:
            module_name, class_name = config.module_path.rsplit(".", 1)
            module = import_module(module_name)
            plugin_cls = getattr(module, class_name)
            plugin: FeedPlugin = plugin_cls()  # type: ignore[assignment]
            plugins.append(plugin)
        except Exception:
            # Falha ao carregar plugin não deve interromper feed
            logger.exception("Falha ao carregar plugin %s", config.module_path)
            continue
    return plugins
