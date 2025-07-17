from rest_framework import viewsets, generics
from .models import ProdutoMarmita, Carrinho, Pedido, ItemPedido, ItemCarrinho, CustomUser
from .serializers import ProdutoMarmitaSerializer, CarrinhoSerializer, UserSerializer, PedidoSerializer
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated, AllowAny

class MeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

class RegisterView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = UserSerializer

class ProdutoMarmitaViewSet(viewsets.ModelViewSet):
    queryset = ProdutoMarmita.objects.all()
    serializer_class = ProdutoMarmitaSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_context(self):
        return {'request': self.request}

class CarrinhoAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        carrinho, _ = Carrinho.objects.get_or_create(usuario=request.user)
        serializer = CarrinhoSerializer(carrinho)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        produto_id = request.data.get('produto_id')
        quantidade = int(request.data.get('quantidade', 1))
        
        produto = get_object_or_404(ProdutoMarmita, id=produto_id)
        carrinho, _ = Carrinho.objects.get_or_create(usuario=request.user)
        
        item, created = ItemCarrinho.objects.get_or_create(carrinho=carrinho, produto=produto)
        
        if created:
            item.quantidade = quantidade
        else:
            item.quantidade += quantidade
        item.save()
        
        serializer = CarrinhoSerializer(carrinho)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, *args, **kwargs):
        item_id = request.data.get('item_id')
        quantidade = int(request.data.get('quantidade', 1))
        
        item = get_object_or_404(ItemCarrinho, id=item_id, carrinho__usuario=request.user)
        
        if quantidade > 0:
            item.quantidade = quantidade
            item.save()
        else:
            item.delete()
            
        carrinho = get_object_or_404(Carrinho, usuario=request.user)
        serializer = CarrinhoSerializer(carrinho)
        return Response(serializer.data)

    def delete(self, request, *args, **kwargs):
        item_id = request.data.get('item_id')
        item = get_object_or_404(ItemCarrinho, id=item_id, carrinho__usuario=request.user)
        item.delete()
        
        carrinho = get_object_or_404(Carrinho, usuario=request.user)
        serializer = CarrinhoSerializer(carrinho)
        return Response(serializer.data)


class PedidoAPIView(generics.ListAPIView):
    serializer_class = PedidoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Pedido.objects.filter(usuario=self.request.user).order_by('-criado_em')

class FinalizarPedidoView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        # Busca o carrinho do usuário autenticado
        carrinho = get_object_or_404(Carrinho, usuario=request.user)
        if not carrinho.itens.exists():
            return Response({'detail': 'Carrinho vazio.'}, status=status.HTTP_400_BAD_REQUEST)

        # Cria o pedido
        total = sum(item.produto.preco * item.quantidade for item in carrinho.itens.all())
        pedido = Pedido.objects.create(
            usuario=request.user,
            total=total
        )
        for item in carrinho.itens.all():
            ItemPedido.objects.create(
                pedido=pedido,
                produto=item.produto,
                quantidade=item.quantidade,
                preco_unitario=item.produto.preco
            )
        carrinho.itens.all().delete()  # Limpa o carrinho
        return Response({'detail': f'Pedido #{pedido.id} criado com sucesso!'}, status=status.HTTP_201_CREATED)
