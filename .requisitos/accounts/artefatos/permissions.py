from rest_framework.permissions import BasePermission

class IsRoot(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_superuser


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_staff and not request.user.is_associado


class IsAssociado(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_associado and not request.user.nucleos.exists()


class IsNucleado(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_associado and request.user.nucleos.exists()


class IsCoordenadorDoNucleo(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.participanucleo_set.filter(is_coordenador=True).exists()
        )
