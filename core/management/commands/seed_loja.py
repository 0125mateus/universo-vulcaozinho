from decimal import Decimal

from django.core.management.base import BaseCommand

from core.models import CategoriaProduto, ProdutoLoja

# Preços sugeridos — custo ~50% do preço (margem bruta ~50%)
PRECOS = {
    'Bolsinha de Braço': (39.90, 18.00),
    'Chapéu de Praia': (59.90, 28.00),
    'Bolsa de Praia': (89.90, 42.00),
    'Saída de Praia': (79.90, 38.00),
    'Toalha de Praia': (69.90, 32.00),
    'Necessaire': (49.90, 22.00),
    'Garrafa Térmica': (99.90, 48.00),
}
BONE_PRECO = (34.90, 15.00)


PRODUTOS = [
    {'nome': 'Bolsinha de Braço', 'descricao': 'Prática e estilosa para levar o essencial.', 'categoria': CategoriaProduto.ACESSORIO, 'ordem': 1},
    {'nome': 'Chapéu de Praia', 'descricao': 'Proteção com estilo Vulcãozinho.', 'categoria': CategoriaProduto.ACESSORIO, 'ordem': 2},
    {'nome': 'Bolsa de Praia', 'descricao': 'Espaçosa, com estampa tropical exclusiva.', 'categoria': CategoriaProduto.ACESSORIO, 'ordem': 3},
    {'nome': 'Saída de Praia', 'descricao': 'Leve e confortável para o pool.', 'categoria': CategoriaProduto.ACESSORIO, 'ordem': 4},
    {'nome': 'Toalha de Praia', 'descricao': 'Macia, com logo bordado.', 'categoria': CategoriaProduto.ACESSORIO, 'ordem': 5},
    {'nome': 'Necessaire', 'descricao': 'Organize seus itens com charme.', 'categoria': CategoriaProduto.ACESSORIO, 'ordem': 6},
    {'nome': 'Garrafa Térmica', 'descricao': 'Mantenha sua bebida na temperatura ideal.', 'categoria': CategoriaProduto.ACESSORIO, 'ordem': 7},
    {'nome': 'Boné Cores (Segunda)', 'descricao': 'Noite Temática — Cores.', 'categoria': CategoriaProduto.NOITE_TEMATICA, 'cor_tema': 'Cores', 'ordem': 10},
    {'nome': 'Boné Black (Terça)', 'descricao': 'Noite Temática — Black Night.', 'categoria': CategoriaProduto.NOITE_TEMATICA, 'cor_tema': 'Black', 'ordem': 11},
    {'nome': 'Boné Dourado (Quarta)', 'descricao': 'Noite Temática — Golden Night.', 'categoria': CategoriaProduto.NOITE_TEMATICA, 'cor_tema': 'Dourado', 'ordem': 12},
    {'nome': 'Boné Livre (Quinta)', 'descricao': 'Noite Temática — Brasilidades.', 'categoria': CategoriaProduto.NOITE_TEMATICA, 'cor_tema': 'Livre', 'ordem': 13},
    {'nome': 'Boné Moda de Viola (Sexta)', 'descricao': 'Noite Temática — Sertanejo.', 'categoria': CategoriaProduto.NOITE_TEMATICA, 'cor_tema': 'Moda de Viola', 'ordem': 14},
    {'nome': 'Boné Festa Neon (Sábado)', 'descricao': 'Noite Temática — Festa Neon.', 'categoria': CategoriaProduto.NOITE_TEMATICA, 'cor_tema': 'Festa Neon', 'ordem': 15},
    {'nome': 'Boné Branco (Domingo)', 'descricao': 'Noite Temática — White Family.', 'categoria': CategoriaProduto.NOITE_TEMATICA, 'cor_tema': 'Branco', 'ordem': 16},
]


class Command(BaseCommand):
    help = 'Cadastra produtos da Loja Oficial Vulcãozinho (rede).'

    def handle(self, *args, **options):
        for dados in PRODUTOS:
            nome = dados['nome']
            preco, custo = PRECOS.get(nome, BONE_PRECO)
            ProdutoLoja.objects.update_or_create(
                nome=nome,
                hotel=None,
                defaults={
                    **dados,
                    'preco': Decimal(str(preco)),
                    'custo': Decimal(str(custo)),
                    'estoque': dados.get('estoque', 20),
                },
            )
            self.stdout.write(self.style.SUCCESS(f'Sincronizado: {nome}'))

        for p in ProdutoLoja.objects.all():
            if not p.codigo_qr or p.estoque == 0:
                if p.estoque == 0:
                    p.estoque = 20
                p.save()
        self.stdout.write(self.style.SUCCESS('Seed loja concluída.'))
