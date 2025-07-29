# Cobranças Recorrentes

O módulo Financeiro gera automaticamente cobranças mensais de associação e de núcleos.
A tarefa `gerar_cobrancas_mensais` é executada via Celery Beat no primeiro dia de
cada mês.

Valores padrão utilizados:

- `MENSALIDADE_ASSOCIACAO`: R$50,00
- `MENSALIDADE_NUCLEO`: R$30,00
- `MENSALIDADE_VENCIMENTO_DIA`: 10

Para cada associado ativo é criado um lançamento pendente em seu respectivo centro
de custo. Caso ele participe de núcleos aprovados, é gerada também a cobrança de
mensalidade de cada núcleo correspondente. Após a criação, o sistema envia
notificações por e-mail e no aplicativo.

