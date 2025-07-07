from rest_framework import serializers
from .models import ProdutoMarmita, Carrinho, ItemCarrinho, Pedido, ItemPedido
from django.contrib.auth.models import User

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
    email = serializers.EmailField(required=True)
    
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password')
        extra_kwargs = {'password': {'write_only': True}}

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Este email já está em uso.")
        return value

    def create(self, validated_data):
        # We need to ensure the username is unique. Let's use the email as username for simplicity
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        return user
