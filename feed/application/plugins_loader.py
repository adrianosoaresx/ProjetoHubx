from __future__ import annotations

from importlib import import_module
from typing import Iterable, List, Tuple

import logging
from django.db import models

from feed.domain.plugins import FeedPlugin
from feed.models import FeedPluginConfig

logger = logging.getLogger(__name__)

def load_plugins_for(
    organizacao: models.Model,
    configs: Iterable[FeedPluginConfig] | None = None,
) -> Tuple[List[FeedPlugin], List[FeedPluginConfig]]:
    """Carrega instâncias de plugins registrados para uma organização.

    Aceita configurações previamente consultadas ou retorna-as junto com as
    instâncias carregadas.
    """

    if configs is None:
        configs_list = list(FeedPluginConfig.objects.filter(organizacao=organizacao))
    else:
        configs_list = list(configs)

    plugins: List[FeedPlugin] = []
    for config in configs_list:
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
    return plugins, configs_list
