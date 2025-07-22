from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, FormView, TemplateView, View
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from api.forms import UserLoginForm, UserRegisterForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from api.models import ProdutoMarmita, Carrinho, ItemCarrinho, Pedido, ItemPedido
from django.conf import settings
import mercadopago
import json
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from urllib.parse import quote
from django.db import models  # Adicione esta linha no início do arquivo 
from datetime import datetime, timedelta, timezone
import os
from django.conf import settings
from django.http import FileResponse, Http404, JsonResponse, HttpResponse
from django.utils.encoding import smart_str
from django.http import FileResponse
import mimetypes
from django.utils.timezone import now




class MediaListView(View):
    def get(self, request, path=''):
        abs_path = os.path.join(settings.MEDIA_ROOT, path)
        if not os.path.exists(abs_path):
            # Se for o diretório raiz e não existir, cria para evitar erro
            if path == '' and not os.path.exists(settings.MEDIA_ROOT):
                os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
                files = []
            else:
                raise Http404("Arquivo ou diretório não encontrado.")
        else:
            if os.path.isfile(abs_path):
                # Serve o arquivo de mídia
                mime_type, _ = mimetypes.guess_type(abs_path)
                response = FileResponse(open(abs_path, 'rb'), content_type=mime_type or 'application/octet-stream')
                return response
            files = os.listdir(abs_path)
        if not files:
            return HttpResponse(f'<h2>Sem arquivos em /imagens/{path}</h2>')
        links = []
        for f in files:
            url = request.path.rstrip('/') + '/' + f
            links.append(f'<li><a href="{url}">{f}</a></li>')
        return HttpResponse(f'<h2>Arquivos em /imagens/{path}</h2><ul>{''.join(links)}</ul>')

class CriarPagamentoView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        carrinho = get_object_or_404(Carrinho, usuario=request.user)
        if not carrinho.itens.exists():
            return redirect('carrinho')

        total = float(carrinho.get_total)

        # Cria o pedido
        pedido = Pedido.objects.create(
            usuario=request.user,
            total=total,
            status='pendente'
        )
        for item in carrinho.itens.all():
            ItemPedido.objects.create(
                pedido=pedido,
                produto=item.produto,
                quantidade=item.quantidade,
                preco_unitario=item.produto.preco
            )
        carrinho.itens.all().delete()

        sdk = mercadopago.SDK(settings.MERCADO_PAGO_ACCESS_TOKEN)

        offset = timezone(timedelta(hours=-3))
        expiration_time = datetime.now(offset) + timedelta(minutes=30)

        # Formato EXATO exigido: '2025-07-08T17:45:00.000-03:00'
        expiration_time_str = expiration_time.strftime("%Y-%m-%dT%H:%M:%S.000-03:00")
        # Dados do pagamento PIX
        payment_data = {
            "transaction_amount": total,
            "description": f"Pedido #{pedido.id}",
            "payment_method_id": "pix",
            "date_of_expiration": expiration_time_str,
            "payer": {
                "email": request.user.email,
                "first_name": request.user.first_name,
                "last_name": request.user.last_name,
            },
            "notification_url": request.build_absolute_uri(reverse_lazy('webhook_mercadopago')),
        }

        payment_response = sdk.payment().create(payment_data)
        payment = payment_response.get("response", {})

        if payment_response.get("status") != 201 or 'point_of_interaction' not in payment:
            pedido.status = 'falhou'
            pedido.save()
            error_message = payment.get('message', 'Erro ao criar pagamento PIX.')
            return render(request, 'web/pagamento_erro.html', {'error': error_message})

        try:
            qr_data = payment['point_of_interaction']['transaction_data']
            qr_code_base64 = qr_data['qr_code_base64']
            qr_code = qr_data['qr_code']
        except KeyError as e:
            pedido.status = 'falhou'
            pedido.save()
            return render(request, 'web/pagamento_erro.html', {
                'error': f'Dados PIX incompletos: {str(e)}'
            })

        pedido.payment_id = payment['id']
        pedido.save()

        context = {
            'pedido_id': pedido.id,
            'qr_code_base64': qr_code_base64,
            'qr_code': qr_code,
            'expiration_time': expiration_time.isoformat(),
        }
        return render(request, 'web/pagamento.html', context)


class ProdutoDetailView(DetailView):
    model = ProdutoMarmita
    template_name = 'web/produto_detail.html'
    context_object_name = 'produto'

class UserLoginView(FormView):
    template_name = 'web/login.html'
    form_class = UserLoginForm
    success_url = reverse_lazy('home')

    def form_valid(self, form):
        login(self.request, form.get_user())
        return super().form_valid(form)

class UserLogoutView(LogoutView):
    next_page = reverse_lazy('home')

class UserRegisterView(FormView):
    template_name = 'web/register.html'
    form_class = UserRegisterForm
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
    template_name = 'web/pedido_whatsapp.html'

    def get(self, request, *args, **kwargs):
        pedido_id = kwargs.get('pedido_id')
        pedido = get_object_or_404(Pedido, id=pedido_id, usuario=request.user)

        if pedido.status != 'pago':
            # Optional: Add a message to inform the user
            return redirect('home')

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

class VerificarStatusPedidoView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        pedido_id = kwargs.get('pedido_id')
        pedido = get_object_or_404(Pedido, id=pedido_id, usuario=request.user)
        return JsonResponse({'status': pedido.status})

@method_decorator(csrf_exempt, name='dispatch')
class MercadoPagoWebhookView(View):
    def post(self, request, *args, **kwargs):
        try:
            notification = json.loads(request.body)
            if notification.get('type') == 'payment':
                payment_id = notification['data']['id']
                sdk = mercadopago.SDK(settings.MERCADO_PAGO_ACCESS_TOKEN)
                payment_info = sdk.payment().get(payment_id)
                payment = payment_info["response"]

                if payment['status'] == 'approved':
                    try:
                        description = payment.get('description', '')
                        if description.startswith('Pedido #'):
                            pedido_id = int(description.split('#')[1])
                            pedido = Pedido.objects.get(id=pedido_id)
                            pedido.status = 'pago'
                            pedido.payment_id = payment_id
                            pedido.save()
                    except (Pedido.DoesNotExist, ValueError, IndexError):
                        pass
            return HttpResponse("OK", status=200)
        except Exception as e:
            # Log o erro se quiser
            return HttpResponse("Erro no processamento", status=200)




## PESQUISAR MARMITAS VIEW ## 
class BuscaMarmitasView(ListView):
    model = ProdutoMarmita
    template_name = 'web/home.html'
    context_object_name = 'produtos'
    paginate_by = 8

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.GET.get('q')
        
        if query:
            return queryset.filter(
                models.Q(nome__icontains=query) | 
                models.Q(descricao__icontains=query),
                ativo=True
            ).order_by('-id')
        return queryset.filter(ativo=True).order_by('-id')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        return context



## HOME VIEW ## 
@method_decorator(csrf_exempt, name='dispatch')
class ProdutoListView(BuscaMarmitasView):
    model = ProdutoMarmita
    template_name = 'web/home.html'
    context_object_name = 'produtos'
    paginate_by = 5
    queryset = ProdutoMarmita.objects.filter(ativo=True).order_by('-id')
    
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