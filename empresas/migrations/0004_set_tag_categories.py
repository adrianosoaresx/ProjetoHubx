from django.db import migrations

TAGS_PRODUTOS = [
    "Loja de roupas femininas",
    "Loja de roupas on-line",
    "Showroom de semijoias",
    "Fábrica e e-commerce de semijoias",
    "Venda de bolsas",
    "Venda e montagem de acessórios femininos",
    "Ótica",
    "Make, dermocosméticos, perfumaria",
    "Produtos de cuidados pessoais e saúde",
    "Produtos de limpeza de piscina",
]

TAGS_SERVICOS = [
    "Estética",
    "Estética e saúde do corpo e da mente",
    "Beleza, saúde e bem estar",
    "Área da beleza, saúde e bem estar",
    "Fisioterapia",
    "Clínica Médica",
    "Médica Dermatologista",
    "Clínica Odontológica",
    "Nail designer",
    "Massoterapia",
    "Salão de beleza",
    "Consultora de Imagem",
    "Mentoria/Consultoria em RH e Gestão de Pessoas",
    "Mentoria, treinamento e consultoria",
    "Mentora, terapeuta e coach de relacionamentos",
    "Coach e terapeuta",
    "Recursos Humanos – mentoria e assessment",
    "Consultoria/Mentoria sistêmica",
    "Consultoria de RH",
    "Consultora em Negócios de Alimentação",
    "Mentora de negócios sistêmicos",
    "Consultoria e terceirização do financeiro",
    "Desenvolvimento de posicionamento de marcas",
    "Advocacia",
    "Advogada especialista em Direito Trabalhista",
    "Escritório de contabilidade",
    "Contabilidade especializada em saúde e INSS",
    "Serviços de corretora de seguros",
    "Secretária Virtual",
    "CEO",
    "Marketing",
    "Gestão de redes sociais",
    "Estratégia de marca e personal branding",
    "Fotografia profissional",
    "Limpeza de piscina",
    "Manutenção de piscinas",
    "Eventos, alimentação e bebidas",
    "Serviço de estágio e jovem aprendiz",
    "Lazer e Turismo",
    "Networking e impacto social",
]


def set_categories(apps, schema_editor):
    Tag = apps.get_model("empresas", "Tag")
    Tag.objects.filter(nome__in=TAGS_PRODUTOS).update(categoria="prod")
    Tag.objects.filter(nome__in=TAGS_SERVICOS).update(categoria="serv")


def reverse_func(apps, schema_editor):
    Tag = apps.get_model("empresas", "Tag")
    Tag.objects.filter(nome__in=TAGS_PRODUTOS + TAGS_SERVICOS).update(categoria="prod")


class Migration(migrations.Migration):
    dependencies = [
        ("empresas", "0003_add_tag_categoria"),
    ]

    operations = [
        migrations.RunPython(set_categories, reverse_func),
    ]
