"""Script utilitário para remover definitivamente leads de associação.

Este script localiza todos os usuários com ``user_type=UserType.CONVIDADO`` —
listados como "leads de associação" na página de membros — e realiza a exclusão
permanente desses registros para fins de testes manuais. Os relacionamentos
associados são limpos antes da remoção para evitar resíduos de dados.

Como executar:

```
python scripts/delete_leads.py
```
"""
from __future__ import annotations

from pathlib import Path
import sys

from scripts.delete_membros import hard_delete_queryset, purge_user, setup_django


def _ensure_scripts_on_path() -> None:
    """Garante que a pasta raiz do projeto esteja no ``sys.path``."""

    root_dir = Path(__file__).resolve().parents[1]
    if str(root_dir) not in sys.path:
        sys.path.append(str(root_dir))


def main() -> None:
    _ensure_scripts_on_path()
    setup_django()

    from django.contrib.auth import get_user_model
    from django.db import transaction

    from accounts.models import UserType

    User = get_user_model()
    leads_qs = User.all_objects.filter(user_type=UserType.CONVIDADO.value)
    total = leads_qs.count()
    print(f"Leads de associação (convidados) encontrados: {total}")

    if total == 0:
        return

    with transaction.atomic():
        for index, user in enumerate(leads_qs.iterator(), start=1):
            print(f"[{index}/{total}] Iniciando remoção definitiva de {user.email}")
            purge_user(user)
            hard_delete_queryset(User.all_objects.filter(pk=user.pk), "registro de usuário")
            print(f"Usuário {user.pk} removido definitivamente.\n")

    print("Processo concluído com sucesso.")


if __name__ == "__main__":
    main()
