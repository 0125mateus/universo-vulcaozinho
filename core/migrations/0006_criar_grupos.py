from django.db import migrations


APP = 'core'

MODELOS_OPERACIONAIS = [
    'hotel',
    'hospede',
    'recreador',
    'localatividade',
    'categoriaprogramacao',
    'atividade',
    'programacaodiaria',
    'inscricaoatividade',
    'presencaregistro',
    'noitetematica',
    'passeio',
    'produtoloja',
    'passaportehospede',
    'carimbopassaporte',
    'salareuniao',
    'mensagemreuniao',
]

ACOES_CRUD = ('add', 'change', 'delete', 'view')
ACOES_ESCRITA = ('add', 'change', 'view')
ACOES_LEITURA = ('view',)


def _codenames(model, acoes):
    return [f'{acao}_{model}' for acao in acoes]


def _buscar_permissoes(Permission, modelos, acoes):
    codenames = []
    for model in modelos:
        codenames.extend(_codenames(model, acoes))
    return Permission.objects.filter(
        content_type__app_label=APP,
        codename__in=codenames,
    )


def _criar_grupo(Group, Permission, nome, permissoes):
    grupo, _ = Group.objects.get_or_create(name=nome)
    grupo.permissions.set(permissoes)
    return grupo


def criar_grupos(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')

    todos_crud = _buscar_permissoes(Permission, MODELOS_OPERACIONAIS, ACOES_CRUD)
    perfil_perms = _buscar_permissoes(Permission, ['perfilusuario'], ACOES_CRUD)

    _criar_grupo(
        Group, Permission, 'vulcaozinho_ADMIN',
        list(todos_crud) + list(perfil_perms),
    )

    _criar_grupo(
        Group, Permission, 'vulcaozinho_DIRETOR',
        list(todos_crud) + list(_buscar_permissoes(Permission, ['perfilusuario'], ACOES_ESCRITA)),
    )

    gerente_modelos = MODELOS_OPERACIONAIS
    _criar_grupo(
        Group, Permission, 'vulcaozinho_GERENTE',
        list(_buscar_permissoes(Permission, gerente_modelos, ACOES_ESCRITA))
        + list(_buscar_permissoes(Permission, ['hotel'], ACOES_LEITURA)),
    )

    supervisor_modelos = [
        'hospede', 'recreador', 'atividade', 'programacaodiaria',
        'inscricaoatividade', 'presencaregistro', 'noitetematica', 'localatividade',
    ]
    _criar_grupo(
        Group, Permission, 'vulcaozinho_SUPERVISOR',
        list(_buscar_permissoes(Permission, supervisor_modelos, ACOES_ESCRITA))
        + list(_buscar_permissoes(Permission, ['hotel', 'categoriaprogramacao'], ACOES_LEITURA)),
    )

    recreador_modelos = [
        'atividade', 'programacaodiaria', 'presencaregistro',
        'inscricaoatividade', 'localatividade', 'hospede',
    ]
    _criar_grupo(
        Group, Permission, 'vulcaozinho_RECREADOR',
        list(_buscar_permissoes(Permission, recreador_modelos, ACOES_ESCRITA))
        + list(_buscar_permissoes(Permission, ['noitetematica', 'recreador'], ACOES_LEITURA)),
    )

    recepcao_modelos = ['hospede', 'presencaregistro', 'inscricaoatividade', 'passaportehospede']
    _criar_grupo(
        Group, Permission, 'vulcaozinho_RECEPCAO',
        list(_buscar_permissoes(Permission, recepcao_modelos, ACOES_ESCRITA))
        + list(_buscar_permissoes(
            Permission,
            ['hotel', 'programacaodiaria', 'atividade', 'noitetematica'],
            ACOES_LEITURA,
        )),
    )

    _criar_grupo(
        Group, Permission, 'vulcaozinho_RESTAURANTE',
        list(_buscar_permissoes(
            Permission,
            ['hospede', 'programacaodiaria', 'noitetematica', 'presencaregistro'],
            ACOES_LEITURA,
        )),
    )

    _criar_grupo(
        Group, Permission, 'vulcaozinho_LOJA',
        list(_buscar_permissoes(Permission, ['produtoloja', 'passaportehospede', 'carimbopassaporte'], ACOES_ESCRITA))
        + list(_buscar_permissoes(Permission, ['hospede', 'hotel'], ACOES_LEITURA)),
    )


def remover_grupos(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name__startswith='vulcaozinho_').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_perfilusuario'),
    ]

    operations = [
        migrations.RunPython(criar_grupos, remover_grupos),
    ]
