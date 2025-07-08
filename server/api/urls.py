from django.urls import path, include
from rest_framework.routers import DefaultRouter
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProdutoMarmitaViewSet, RegisterView, FinalizarPedidoView, CarrinhoAPIView, MeAPIView, PedidoAPIView
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

router = DefaultRouter()
router.register(r'produtos', ProdutoMarmitaViewSet, basename='produtomarmita')

urlpatterns = [
    path('', include(router.urls)),
    path('register/', RegisterView.as_view(), name='auth_register'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('me/', MeAPIView.as_view(), name='me_api'),
    path('carrinho/', CarrinhoAPIView.as_view(), name='carrinho_api'),
    path('pedidos/', PedidoAPIView.as_view(), name='pedidos_api'),
    path('finalizar-pedido/', FinalizarPedidoView.as_view(), name='finalizar_pedido-api'),
]
