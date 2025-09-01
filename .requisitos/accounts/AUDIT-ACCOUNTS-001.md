# AUT-ACCOUNTS

Auditoria do app **accounts** em 2024‑XX‑XX.

## Resumo
A maioria dos requisitos funcionais foi implementada. Foram identificadas quatro lacunas principais:

1. Validação de CPF opcional e formatos com pontuação.
2. Registro de tentativas de login durante bloqueio.
3. Sincronização de `is_active` na exclusão/cancelamento via API.
4. Remoção física de arquivos de mídia.

## Requisitos atendidos
RF‑01, RF‑02, RF‑03, RF‑04, RF‑05, RF‑06, RF‑09, RF‑10 (com ressalva de CPF), RF‑11, RF‑13, RF‑14, RF‑15.

## Requisitos parciais
RF‑07, RF‑08, RF‑12.

## Próximos passos
Concluir correções listadas e adicionar testes automatizados.
