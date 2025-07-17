from enum import Enum

class TipoUsuario(Enum):
    ROOT = "root"
    ADMIN = "admin"
    ASSOCIADO = "associado"
    NUCLEADO = "nucleado"
    COORDENADOR = "coordenador"
    CONVIDADO = "convidado"

    def label(self):
        return {
            "root": "Superusuário",
            "admin": "Administrador",
            "associado": "Associado",
            "nucleado": "Membro de Núcleo",
            "coordenador": "Coordenador",
            "convidado": "Convidado",
        }[self.value]
