from django.db import migrations

TAGS_PRODUTOS = [
    "Loja de roupas femininas",
    "Loja de roupas on-line",
    "Showroom de semijoias",
    "F\u00e1brica e e-commerce de semijoias",
    "Venda de bolsas",
    "Venda e montagem de acess\u00f3rios femininos",
    "\u00d3tica",
    "Make, dermocosm\u00e9ticos, perfumaria",
    "Produtos de cuidados pessoais e sa\u00fade",
    "Produtos de limpeza de piscina",
]

TAGS_SERVICOS = [
    "Est\u00e9tica",
    "Est\u00e9tica e sa\u00fade do corpo e da mente",
    "Beleza, sa\u00fade e bem estar",
    "\u00c1rea da beleza, sa\u00fade e bem estar",
    "Fisioterapia",
    "Cl\u00ednica M\u00e9dica",
    "M\u00e9dica Dermatologista",
    "Cl\u00ednica Odontol\u00f3gica",
    "Nail designer",
    "Massoterapia",
    "Sal\u00e3o de beleza",
    "Consultora de Imagem",
    "Mentoria/Consultoria em RH e Gest\u00e3o de Pessoas",
    "Mentoria, treinamento e consultoria",
    "Mentora, terapeuta e coach de relacionamentos",
    "Coach e terapeuta",
    "Recursos Humanos \u2013 mentoria e assessment",
    "Consultoria/Mentoria sist\u00eamica",
    "Consultoria de RH",
    "Consultora em Neg\u00f3cios de Alimenta\u00e7\u00e3o",
    "Mentora de neg\u00f3cios sist\u00eamicos",
    "Consultoria e terceiriza\u00e7\u00e3o do financeiro",
    "Desenvolvimento de posicionamento de marcas",
    "Advocacia",
    "Advogada especialista em Direito Trabalhista",
    "Escrit\u00f3rio de contabilidade",
    "Contabilidade especializada em sa\u00fade e INSS",
    "Servi\u00e7os de corretora de seguros",
    "Secret\u00e1ria Virtual",
    "CEO",
    "Marketing",
    "Gest\u00e3o de redes sociais",
    "Estrat\u00e9gia de marca e personal branding",
    "Fotografia profissional",
    "Limpeza de piscina",
    "Manuten\u00e7\u00e3o de piscinas",
    "Eventos, alimenta\u00e7\u00e3o e bebidas",
    "Servi\u00e7o de est\u00e1gio e jovem aprendiz",
    "Lazer e Turismo",
    "Networking e impacto social",
]


def create_tags(apps, schema_editor):
    Tag = apps.get_model("empresas", "Tag")
    for nome in TAGS_PRODUTOS + TAGS_SERVICOS:
        Tag.objects.get_or_create(nome=nome)


def reverse_func(apps, schema_editor):
    Tag = apps.get_model("empresas", "Tag")
    for nome in TAGS_PRODUTOS + TAGS_SERVICOS:
        Tag.objects.filter(nome=nome).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("empresas", "0001_initial"),
    ]

    operations = [migrations.RunPython(create_tags, reverse_func)]
