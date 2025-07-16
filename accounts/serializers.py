from rest_framework import serializers
from .models import User

class UserSerializer(serializers.ModelSerializer):
    tipo_usuario = serializers.CharField(source='get_tipo_usuario', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'is_associado', 'is_coordenador',
            'nucleo_id', 'organizacao_id', 'tipo_usuario'
        ]
