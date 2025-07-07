from django.contrib import admin
from .models import ProdutoMarmita, Carrinho, ItemCarrinho

@admin.register(ProdutoMarmita)
class ProdutoMarmitaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'kcal', 'proteinas', 'preco', 'ativo', 'data_criacao', 'imagem')
    search_fields = ('nome', 'descricao')
    list_filter = ('ativo',)
    ordering = ('-data_criacao',)

@admin.register(Carrinho)
class CarrinhoAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'criado_em')
    search_fields = ('usuario__username',)
    ordering = ('-criado_em',)

@admin.register(ItemCarrinho)
class ItemCarrinhoAdmin(admin.ModelAdmin):
    list_display = ('carrinho', 'produto', 'quantidade')
    search_fields = ('carrinho__usuario__username', 'produto__nome')
    ordering = ('carrinho',)