# Fluxo de convites, usuários e tokens

O diagrama abaixo resume como os convites são gerados, enviados e consumidos, destacando a relação entre o token, o e-mail do convidado e o evento associado.

```mermaid
flowchart TD
    A[Operador cria convite \n e define evento/organização] --> B[Serviço gera token único \n (código secreto + hash no banco)]
    B --> C[Token é exibido uma única vez \n para ser enviado ao convidado]
    C --> D[Convidado recebe e-mail/mensagem \n contendo link ou código do token]

    D --> E[Convidado acessa página pública \n e informa e-mail + token]
    E --> F{Token existe, está NOVO \n e não expirou?}
    F -- não --> F1[Erro: token inválido/expirado]
    F -- sim --> G{E-mail pertence à mesma \n organização do token?}
    G -- não --> G1[Erro: domínio/usuário \n não autorizado]

    G -- sim --> H{Token ligado a evento \n compatível?}
    H -- não --> H1[Erro: convite não \n corresponde ao evento]

    H -- sim --> I{Usuário já existe \n na organização?}
    I -- sim --> J[Direciona para login/inscrição \n do evento com sessão do token]
    I -- não --> K[Fluxo de cadastro do convidado \n aceita termos do evento]

    J --> L[Inscrição confirmada]
    K --> L
    L --> M[Token marcado como USADO \n e vinculado ao usuário]
    M --> N[Logs e auditoria \n registram consumo]
```

**Notas importantes**
- Cada token é de uso único: ao ser consumido, muda de `NOVO` para `USADO` e não pode ser reaplicado.
- O código completo do token não é armazenado; apenas seu hash e um _preview_ seguro ficam no banco.
- As verificações de organização, evento e estado do token impedem que convites sejam usados fora do público-alvo previsto.
- O fluxo de validação e consumo também está disponível via API, respeitando limites de uso e registrando logs para auditoria.
