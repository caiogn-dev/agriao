from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import ProdutoMarmita, Carrinho, ItemCarrinho, Pedido, ItemPedido

User = get_user_model()

class ProdutoMarmitaSerializer(serializers.ModelSerializer):
    imagem_url = serializers.SerializerMethodField()

    class Meta:
        model = ProdutoMarmita
        fields = ('id', 'nome', 'descricao', 'kcal', 'proteinas', 'preco', 'data_criacao', 'ativo', 'imagem', 'imagem_url')
        read_only_fields = ('imagem_url',)

    def get_imagem_url(self, obj):
        request = self.context.get('request')
        if obj.imagem and hasattr(obj.imagem, 'url'):
            return request.build_absolute_uri(obj.imagem.url)
        return None

class ItemCarrinhoSerializer(serializers.ModelSerializer):
    produto = ProdutoMarmitaSerializer(read_only=True)
    
    class Meta:
        model = ItemCarrinho
        fields = ['id', 'produto', 'quantidade']

class CarrinhoSerializer(serializers.ModelSerializer):
    itens = ItemCarrinhoSerializer(many=True, read_only=True)
    total = serializers.DecimalField(max_digits=10, decimal_places=2, source='get_total', read_only=True)

    class Meta:
        model = Carrinho
        fields = ['id', 'usuario', 'criado_em', 'itens', 'total']
        read_only_fields = ['usuario', 'criado_em', 'itens', 'total']

class ItemPedidoSerializer(serializers.ModelSerializer):
    produto = ProdutoMarmitaSerializer(read_only=True)

    class Meta:
        model = ItemPedido
        fields = ['id', 'produto', 'quantidade', 'preco_unitario']

class PedidoSerializer(serializers.ModelSerializer):
    itens = ItemPedidoSerializer(many=True, read_only=True)

    class Meta:
        model = Pedido
        fields = ['id', 'usuario', 'criado_em', 'status', 'total', 'itens']
        read_only_fields = ['usuario', 'criado_em', 'total', 'itens']

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'password')

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Este email já está em uso.")
        return value

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)
