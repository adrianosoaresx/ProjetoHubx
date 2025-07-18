from datetime import datetime
from typing import Dict, Optional
from django.db.models import Count, Avg, Sum, Q
from accounts.models import User
from agenda.models import Evento, InscricaoEvento
from discussao.models import TopicoDiscussao, RespostaDiscussao
from feed.models import Post
from chat.models import ChatMessage

class DashboardService:
    @staticmethod
    def calcular_distribuicao_usuarios(tipo: Optional[str] = None, status: Optional[str] = None) -> Dict[str, int]:
        query = User.objects.all()
        if tipo:
            query = query.filter(tipo=tipo)
        if status:
            query = query.filter(is_active=(status == 'ativo'))
        return query.values('tipo').annotate(total=Count('id'))

    @staticmethod
    def calcular_eventos_por_status() -> Dict[str, int]:
        return Evento.objects.values('status').annotate(total=Count('id'))

    @staticmethod
    def calcular_inscricoes_eventos() -> Dict[str, Dict[str, float]]:
        inscricoes = InscricaoEvento.objects.aggregate(
            total=Count('id'),
            confirmados=Count('id', filter=Q(status='confirmada')),
            avaliacao_media=Avg('evento__feedbacknota__nota')
        )
        return inscricoes

    @staticmethod
    def calcular_topicos_respostas_forum() -> Dict[str, int]:
        topicos = TopicoDiscussao.objects.count()
        respostas = RespostaDiscussao.objects.count()
        return {'topicos': topicos, 'respostas': respostas}

    @staticmethod
    def calcular_posts_feed() -> int:
        return Post.objects.count()

    @staticmethod
    def calcular_mensagens_chat() -> int:
        return ChatMessage.objects.count()

    @staticmethod
    def calcular_valores_eventos() -> Dict[str, float]:
        valores = {
            'valor_arrecadado': InscricaoEvento.objects.aggregate(Sum('valor_pago'))['valor_pago__sum'],
            'valor_gasto': Evento.objects.aggregate(Sum('orcamento'))['orcamento__sum']
        }
        return valores

    @staticmethod
    def aplicar_filtros(queryset, data_inicio: Optional[datetime] = None, data_fim: Optional[datetime] = None, organizacao: Optional[int] = None, nucleo: Optional[int] = None):
        if data_inicio:
            queryset = queryset.filter(data__gte=data_inicio)
        if data_fim:
            queryset = queryset.filter(data__lte=data_fim)
        if organizacao:
            queryset = queryset.filter(organizacao_id=organizacao)
        if nucleo:
            queryset = queryset.filter(nucleo_id=nucleo)
        return queryset
