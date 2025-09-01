# AUDIT-DISCUSSAO-001

Data: 2025-08-13

## Cobertura de Requisitos

Requisito	Situação	Evidências
RF‑04 – slug atualizado automaticamente	Parcial. Slug só é gerado se estiver vazio.	TopicoDiscussao.savenão recalcula ao editar
RF‑05/RF‑10 – edição/remoção limitada a 15 min	Parcial. Edição respeita o limite; deleção não.	TopicoDeleteView e RespostaDeleteView sem checagem de tempo
RF‑06/RF‑13 – notificação ao resolver tópico	Parcial. Apenas o autor da melhor resposta é avisado.	TopicoMarkResolvedViewchama somentenotificar_melhor_resposta
RF‑07 – ordenação por score	Não atendido. Apenas “recentes” e “comentados”.	TopicoListView.get_querysetignora ordenação por votos
RF‑11 – exibir score e nº de votos	Parcial. Propriedades existem, mas não são serializadas.	TopicoDiscussaoSerializernão inclui campos de votos
RF‑12 – denúncias e moderação	Parcial. Modelo existe; faltam endpoints/views.	Router da API não registra denúncias
RF‑14 – API para categorias, votos e denúncias	Não atendido. API cobre apenas tags, tópicos e respostas.	Ausência de CategoryViewSet e ações de voto/denúncia
RNF‑04 – logs de notificações	Não atendido. Tasks não registram envio.	tasks.pyenvia notificações sem log persistido

## Observações