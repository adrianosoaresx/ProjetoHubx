import logging

def atualizar_cobranca(nucleo_id, user_id, status):
    logging.getLogger(__name__).info(
        "atualizar_cobranca", extra={"nucleo_id": nucleo_id, "user_id": user_id, "status": status}
    )
