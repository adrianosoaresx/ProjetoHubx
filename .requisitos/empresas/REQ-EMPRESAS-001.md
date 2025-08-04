---
id: REQ-EMPRESAS-001
title: Requisitos Empresas Hubx
module: Empresas
status: Em vigor
version: '1.0'
authors: []
created: '2025-07-25'
updated: '2025-07-25'
source: Requisitos_Empresas_Hubx.pdf
---

## 1. Visão Geral

O App Empresas gerencia o cadastro, consulta, atualização e remoção de empresas vinculadas a organizações no sistema Hubx, permitindo pesquisa por tags, busca textual e controle de autoria.

## 2. Escopo
- **Inclui**:
  - Listagem e visualização de empresas com filtros por organização, município e tags.  
  - Cadastro de novas empresas (nome, CNPJ, tipo, localização, logo e descrição).  
  - Edição de dados cadastrais de empresas existentes.  
  - Exclusão de empresas pelo usuário responsável ou admin.  
  - Sistema de tags e palavras-chave para busca avançada.  
- **Exclui**:
  - Gerenciamento de usuários, órgãos governamentais ou processos externos.  
  - Integração com serviços de faturamento ou pagamento.

## 3. Requisitos Funcionais

- **RF‑01**
  - Descrição: Listar empresas com paginação e filtros por organização, município e tags.
  - Prioridade: Alta
  - Critérios de Aceite: Resposta paginada com parâmetros via `request.GET`.

- **RF‑02**
  - Descrição: Criar empresa com validação de CNPJ único.
  - Prioridade: Alta
  - Critérios de Aceite: Retorna erro 400 se CNPJ já existir.

- **RF‑03**
  - Descrição: Editar dados de uma empresa existente.
  - Prioridade: Média
  - Critérios de Aceite: Apenas campos permitidos são atualizados.

- **RF‑04**
  - Descrição: Excluir empresa pelo usuário proprietário ou admin.
  - Prioridade: Média
  - Critérios de Aceite: Soft delete marcado no banco e não aparece em listagens.

- **RF‑05**
  - Descrição: Pesquisar empresas por palavras-chave e tags.
  - Prioridade: Média
  - Critérios de Aceite: Busca retorna empresas cujo nome ou tags correspondem ao termo.

## 4. Requisitos Não‑Funcionais

- **RNF‑01**
  - Categoria: Desempenho
  - Descrição: Listagem de empresas com filtros deve responder em p95 ≤ 300 ms.
  - Métrica/Meta: 300 ms

- **RNF‑02**
  - Categoria: Segurança
  - Descrição: Garantir unicidade de CNPJ e controle de acesso.
  - Métrica/Meta: 0 entradas duplicadas em testes automatizados.

- **RNF‑03**
  - Categoria: Manutenibilidade
  - Descrição: Código modular e documentado para fácil extensão.
  - Métrica/Meta: Cobertura de testes ≥ 90 %.


- **RNF‑04**: Todos os modelos deste app devem herdar de `TimeStampedModel` para timestamps automáticos (`created` e `modified`), garantindo consistência e evitando campos manuais.
- **RNF‑05**: Quando houver necessidade de exclusão lógica, os modelos devem implementar `SoftDeleteModel` (ou mixin equivalente), evitando remoções físicas e padronizando os campos `deleted` e `deleted_at`.

## 5. Casos de Uso

### UC‑01 – Listar Empresas
1. Usuário acessa endpoint de listagem de empresas.  
2. Aplica filtros e ordenações.  
3. Sistema retorna página de resultados paginados.

### UC‑02 – Criar Empresa
1. Usuário preenche formulário com dados da empresa.  
2. Sistema valida campos e salva no banco.  
3. Retorna HTTP 201 com dados criados.

### UC‑03 – Editar Empresa
1. Usuário solicita edição de empresa existente.  
2. Sistema verifica permissões e atualiza campos.  
3. Retorna HTTP 200 com dados atualizados.

### UC‑04 – Excluir Empresa
1. Usuário solicita remoção de empresa.  
2. Sistema realiza soft delete e retorna HTTP 204.

### UC‑05 – Buscar Empresas
1. Usuário envia termo de busca e/ou tags.  
2. Sistema filtra empresas e retorna resultados.

## 6. Regras de Negócio
- CNPJ deve ser único em todo o sistema.  
- Empresa deve estar vinculada a uma organização.  
- Apenas usuário responsável ou admin pode editar/excluir.

## 7. Modelo de Dados
*Nota:* Todos os modelos herdam de `TimeStampedModel` (campos `created` e `modified`) e utilizam `SoftDeleteModel` para exclusão lógica quando necessário. Assim, campos de timestamp e exclusão lógica não são listados individualmente.

- **Empresa**  
  - id: UUID  
  - usuario: FK → User.id  
  - organizacao: FK → Organizacao.id  
  - nome: string  
  - cnpj: string (unique)  
  - tipo: string  
  - municipio: string  
  - estado: string  
  - logo: ImageField (opcional)  
  - descricao: TextField (opcional)  
  - palavras_chave: CharField  
  - tags: M2M → Tag  

- **Tag**  
  - id: UUID  
  - nome: string (unique)  
  - categoria: enum('prod','serv')  

## 8. Critérios de Aceite (Gherkin)
```gherkin
Feature: Gestão de Empresas
  Scenario: Cadastro de empresa com CNPJ único
    Given formulário válido e CNPJ não cadastrado
    When envia dados
    Then retorna HTTP 201 e empresa aparece na listagem

  Scenario: Busca por tag
    Given empresas com tag "serviço"
    When busca por "serviço"
    Then retorna lista contendo empresas com essa tag
```

## 9. Dependências / Integrações
- **App Accounts**: identificação do usuário responsável.  
- **App Organizações**: validação de organização vinculada.  
- **Search Engine**: Elasticsearch para busca avançada.  
- **Storage (S3)**: armazenamento de logos de empresa.  
- **Sentry**: monitoramento de erros.

## 10. Anexos e Referências
- Documento fonte: Requisitos_Empresas_Hubx.pdf

## 11. Melhorias e Extensões (Auditoria 2025‑07‑25)

### Requisitos Funcionais Adicionais
- **RF‑06** – Implementar histórico de alterações de dados (quem alterou, quando e quais campos).  
- **RF‑07** – Permitir avaliações e comentários sobre empresas (1–5 estrelas) para feedback.  

### Requisitos Não‑Funcionais Adicionais
- **RNF‑06** – O histórico deve estar disponível para consulta por admins e atender requisitos de LGPD.  

### Modelo de Dados Adicional
- Nova entidade `EmpresaChangeLog` com campos: id, empresa_id, usuario_id, campo_alterado, valor_antigo, valor_novo, alterado_em.  
- Nova entidade `AvaliacaoEmpresa` com campos: id, empresa_id, usuario_id, nota (1–5), comentario.  

### Regras de Negócio Adicionais
- Somente usuários autenticados podem avaliar empresas; um único usuário avalia uma empresa uma vez.  