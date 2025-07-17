from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from .models import CustomUser, ProdutoMarmita, Carrinho, ItemCarrinho, Pedido, ItemPedido
from .forms import UserRegisterForm, UserChangeForm

class CustomUserAdmin(BaseUserAdmin):
    add_form = UserRegisterForm
    form = UserChangeForm
    model = CustomUser

    list_display = ('email', 'first_name', 'last_name', 'is_staff', 'is_superuser')
    list_filter = ('is_staff', 'is_superuser', 'is_active')

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Informações pessoais', {'fields': ('first_name', 'last_name')}),
        ('Permissões', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'password1', 'password2', 'is_staff', 'is_superuser')}
        ),
    )

    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)
    filter_horizontal = ('groups', 'user_permissions',)


# Registro de outros modelos
@admin.register(ProdutoMarmita)
class ProdutoMarmitaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'kcal', 'preco', 'ativo')
    list_filter = ('ativo',)
    search_fields = ('nome',)


@admin.register(Carrinho)
class CarrinhoAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'criado_em')
    search_fields = ('usuario__email',)


@admin.register(ItemCarrinho)
class ItemCarrinhoAdmin(admin.ModelAdmin):
    list_display = ('carrinho', 'produto', 'quantidade')
    search_fields = ('carrinho__usuario__email', 'produto__nome')


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ('id', 'usuario', 'status', 'total', 'criado_em')
    list_filter = ('status',)
    search_fields = ('usuario__email', 'id')


@admin.register(ItemPedido)
class ItemPedidoAdmin(admin.ModelAdmin):
    list_display = ('pedido', 'produto', 'quantidade', 'preco_unitario')
    search_fields = ('pedido__usuario__email', 'produto__nome')


# Registrar CustomUser no admin
admin.site.register(CustomUser, CustomUserAdmin)
