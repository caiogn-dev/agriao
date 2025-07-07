from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, FormView, TemplateView, View
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from api.models import ProdutoMarmita, Carrinho, ItemCarrinho, Pedido, ItemPedido
from django.conf import settings
import mercadopago
import json
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from urllib.parse import quote

from datetime import datetime, timedelta

class CriarPagamentoView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        carrinho = get_object_or_404(Carrinho, usuario=request.user)
        if not carrinho.itens.exists():
            return redirect('carrinho')

        total = float(carrinho.get_total)

        sdk = mercadopago.SDK(settings.MERCADO_PAGO_ACCESS_TOKEN)

        expiration_time = datetime.now() + timedelta(minutes=30)
        expiration_time_str = expiration_time.strftime("%Y-%m-%dT%H:%M:%S.000-03:00")

        payment_data = {
            "transaction_amount": total,
            "description": "Pedido de Marmitas",
            "payment_method_id": "pix",
            "date_of_expiration": expiration_time_str,
            "payer": {
                "email": request.user.email,
                "first_name": request.user.first_name,
                "last_name": request.user.last_name,
            }
        }

        payment_response = sdk.payment().create(payment_data)
        payment = payment_response["response"]

        if 'point_of_interaction' not in payment:
            # Handle error, maybe the access token is wrong
            error_message = payment.get('message', 'Erro desconhecido ao criar pagamento.')
            return render(request, 'web/pagamento_erro.html', {'error': error_message})

        context = {
            'qr_code_base64': payment['point_of_interaction']['transaction_data']['qr_code_base64'],
            'qr_code': payment['point_of_interaction']['transaction_data']['qr_code'],
            'expiration_time': expiration_time_str
        }
        
        # Store the pending order details in the session
        request.session['pending_pedido'] = {
            'payment_id': payment['id'],
            'total': total,
            'itens': [{
                'produto_id': item.produto.id,
                'quantidade': item.quantidade,
                'preco_unitario': float(item.produto.preco)
            } for item in carrinho.itens.all()]
        }

        return render(request, 'web/pagamento.html', context)

@method_decorator(csrf_exempt, name='dispatch')
class ProdutoListView(ListView):
    model = ProdutoMarmita
    template_name = 'web/home.html'
    context_object_name = 'produtos'
    queryset = ProdutoMarmita.objects.filter(ativo=True)

    def post(self, request, *args, **kwargs):
        # This is a workaround for the webhook being sent to the wrong URL.
        # The ideal solution is to configure the correct webhook URL in Mercado Pago.
        try:
            notification = json.loads(request.body)
            if notification.get('type') == 'payment':
                payment_id = notification['data']['id']
                
                sdk = mercadopago.SDK(settings.MERCADO_PAGO_ACCESS_TOKEN)
                payment_info = sdk.payment().get(payment_id)
                payment = payment_info["response"]

                if payment.get('status') == 'approved':
                    try:
                        pedido = Pedido.objects.get(payment_id=payment_id)
                        pedido.status = 'pago'
                        pedido.save()
                    except Pedido.DoesNotExist:
                        # This can happen if the webhook arrives before the user is redirected
                        # from the payment page and the Pedido is created.
                        pass
        except (json.JSONDecodeError, KeyError):
            # Not a valid webhook notification, ignore it.
            pass

        return HttpResponse(status=200)

class ProdutoDetailView(DetailView):
    model = ProdutoMarmita
    template_name = 'web/produto_detail.html'
    context_object_name = 'produto'

class UserLoginView(LoginView):
    template_name = 'web/login.html'

class UserLogoutView(LogoutView):
    next_page = reverse_lazy('home')

class UserRegisterView(FormView):
    template_name = 'web/register.html'
    form_class = UserCreationForm
    success_url = reverse_lazy('login')

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)

class CarrinhoView(LoginRequiredMixin, TemplateView):
    template_name = 'web/carrinho.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        carrinho, _ = Carrinho.objects.get_or_create(usuario=self.request.user)
        context['carrinho'] = carrinho
        return context

class AdicionarAoCarrinhoView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        produto = get_object_or_404(ProdutoMarmita, pk=kwargs['produto_id'])
        carrinho, _ = Carrinho.objects.get_or_create(usuario=request.user)
        quantidade = int(request.POST.get('quantidade', 1))
        
        item, created = ItemCarrinho.objects.get_or_create(carrinho=carrinho, produto=produto)
        
        if created:
            item.quantidade = quantidade
        else:
            item.quantidade += quantidade
        item.save()
        
        return redirect('carrinho')

class FinalizarPedidoView(LoginRequiredMixin, TemplateView):
    template_name = 'web/pedido_whatsapp.html' # Changed to the new template

    def get(self, request, *args, **kwargs):
        pending_pedido = request.session.get('pending_pedido')
        if not pending_pedido:
            return redirect('carrinho')

        pedido = Pedido.objects.create(
            usuario=request.user, 
            total=pending_pedido['total'],
            payment_id=pending_pedido['payment_id']
        )
        for item_data in pending_pedido['itens']:
            produto = get_object_or_404(ProdutoMarmita, id=item_data['produto_id'])
            ItemPedido.objects.create(
                pedido=pedido,
                produto=produto,
                quantidade=item_data['quantidade'],
                preco_unitario=item_data['preco_unitario']
            )
        
        # Clear the cart and the session data
        carrinho = get_object_or_404(Carrinho, usuario=request.user)
        carrinho.itens.all().delete()
        del request.session['pending_pedido']

        # Prepare WhatsApp message
        itens_str = "\n".join([f"- {item.quantidade}x {item.produto.nome}" for item in pedido.itens.all()])
        raw_message = f"Olá! Gostaria de confirmar meu pedido #{pedido.id}:\n\n{itens_str}\n\nTotal: R$ {pedido.total}"
        whatsapp_message = quote(raw_message)
        
        context = {
            'pedido': pedido,
            'whatsapp_url': f"https://wa.me/{settings.MERCADO_PAGO_WHATSAPP_NUMBER}?text={whatsapp_message}"
        }
        return self.render_to_response(context)

class MeusPedidosView(LoginRequiredMixin, ListView):
    model = Pedido
    template_name = 'web/meus_pedidos.html'
    context_object_name = 'pedidos'

    def get_queryset(self):
        return Pedido.objects.filter(usuario=self.request.user).order_by('-criado_em')

class RemoverDoCarrinhoView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        item_id = kwargs.get('item_id')
        item = get_object_or_404(ItemCarrinho, id=item_id, carrinho__usuario=request.user)
        item.delete()
        return redirect('carrinho')

class AtualizarCarrinhoView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        item_id = kwargs.get('item_id')
        item = get_object_or_404(ItemCarrinho, id=item_id, carrinho__usuario=request.user)
        
        quantidade = int(request.POST.get('quantidade', 1))

        if quantidade > 0:
            item.quantidade = quantidade
            item.save()
        else:
            item.delete()
        
        return redirect('carrinho')

@method_decorator(csrf_exempt, name='dispatch')
class MercadoPagoWebhookView(View):
    def post(self, request, *args, **kwargs):
        notification = json.loads(request.body)
        
        if notification['type'] == 'payment':
            payment_id = notification['data']['id']
            
            sdk = mercadopago.SDK(settings.MERCADO_PAGO_ACCESS_TOKEN)
            payment_info = sdk.payment().get(payment_id)
            payment = payment_info["response"]

            if payment['status'] == 'approved':
                try:
                    pedido = Pedido.objects.get(payment_id=payment_id)
                    pedido.status = 'pago'
                    pedido.save()
                    # You can add more logic here, like sending a confirmation email
                except Pedido.DoesNotExist:
                    # Handle the case where the order is not found
                    pass

        return HttpResponse(status=200)
