# Senhas configuradas pelo script `setup_cdl_mulher`

Este documento descreve as credenciais iniciais geradas pelo script
[`scripts/setup_cdl_mulher.py`](./setup_cdl_mulher.py).

| Usuário / Grupo                            | Identificação                          | Senha configurada            | Observações |
|--------------------------------------------|----------------------------------------|------------------------------|-------------|
| Superusuário do sistema                    | `root` / `root@hubx.local`             | `J0529*435`                  | Sempre recriado com os privilégios de superusuário. |
| Administrador da organização CDL Mulher    | `cdladmin` / `cdladmin@hubx.local`     | `pionera`                    | Associado à organização e ao núcleo como administrador. |
| Membros importados do núcleo               | e-mail individual do integrante        | Valor da opção `--member-password` (padrão `Hubx123!`) | Aplicado a todos os usuários importados do arquivo JSON. Pode ser substituído pela variável de ambiente `CDL_MULHER_MEMBER_PASSWORD`. |

> **Importante:** Após a execução do script recomenda-se solicitar que os
> usuários alterem suas senhas no primeiro acesso.
