from django.urls import path
from django.conf import settings
from .views import *
from django.conf.urls.static import static
from django.views.static import serve
from django.urls import re_path

urlpatterns = [
    path('', ProdutoListView.as_view(), name='home'),
    path('produto/<int:pk>/', ProdutoDetailView.as_view(), name='produto_detail'),

    path('login/', UserLoginView.as_view(), name='login'),
    path('logout/', UserLogoutView.as_view(), name='logout'),
    path('register/', UserRegisterView.as_view(), name='register'),

    path('carrinho/', CarrinhoView.as_view(), name='carrinho'),
    path('carrinho/adicionar/<int:produto_id>/', AdicionarAoCarrinhoView.as_view(), name='adicionar_ao_carrinho'),
    path('carrinho/remover/<int:item_id>/', RemoverDoCarrinhoView.as_view(), name='remover_do_carrinho'),
    path('carrinho/atualizar/<int:item_id>/', AtualizarCarrinhoView.as_view(), name='atualizar_carrinho'),
    
    path('pagamento/', CriarPagamentoView.as_view(), name='criar-pagamento'),
    path('finalizar-pedido/<int:pedido_id>/', FinalizarPedidoView.as_view(), name='finalizar_pedido'),
    path('verificar-status/<int:pedido_id>/', VerificarStatusPedidoView.as_view(), name='verificar_status_pedido'),
    path('webhook/mercadopago/', MercadoPagoWebhookView.as_view(), name='webhook_mercadopago'),

    path('meus-pedidos/', MeusPedidosView.as_view(), name='meus_pedidos'),
    
    re_path(r'^imagens/(?P<path>.*)$', MediaListView.as_view(), name='media_list'),
    path('imagens/<path:path>', serve, {'document_root': settings.MEDIA_ROOT}),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)