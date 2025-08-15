# Nome do Aplicativo: discussao

## O que este app faz (em palavras simples)
- Permite criar categorias, abrir tópicos e responder como em um fórum.
- Usuários podem votar, marcar melhor resposta e denunciar conteúdos.
- Notificações avisam quando há novas respostas ou resolução de tópico.

## Para quem é
- Integrantes da organização que precisam discutir temas e tirar dúvidas.

## Como usar (passo a passo rápido)
1. Acesse **Menu → Discussão**.
2. Escolha uma categoria ou crie uma nova (se for administrador).
3. Para abrir um tópico: clique em **Novo Tópico**, preencha título, descrição e tags.
4. Para responder: na página do tópico, use o campo **Comentar**.
5. Use os botões ▲ ▼ para votar e o link **Marcar como resolvido** para indicar a melhor resposta.

## Principais telas e onde encontrar
- Lista de categorias: rota `discussao/`.
- Lista de tópicos de uma categoria: `discussao/<categoria>/`.
- Detalhe do tópico com respostas: `discussao/<categoria>/<topico>/`.

## O que você precisa saber
- Apenas administradores podem criar categorias ou reabrir tópicos fechados.
- Arquivos anexados não têm validação de tipo; envie apenas formatos confiáveis.
- Dependência de Redis pode impedir algumas ações em ambientes sem o serviço.

## Suporte
- Contato/Canal: suporte@hubx.space
