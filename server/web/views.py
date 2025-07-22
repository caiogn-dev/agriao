from django.urls import reverse, reverse_lazy
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
import logging
from django.contrib import messages


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


logger = logging.getLogger(__name__)

class CriarPagamentoView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        try:
            # 1. Validação do carrinho
            carrinho = get_object_or_404(Carrinho, usuario=request.user)
            if not carrinho.itens.exists():
                messages.warning(request, "Seu carrinho está vazio")
                return redirect('carrinho')

            # 2. Criação do pedido
            total = float(carrinho.get_total)
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

            # 3. Configuração do Mercado Pago
            sdk = mercadopago.SDK(settings.MERCADO_PAGO_ACCESS_TOKEN)
            
            # Construção das URLs
            base_url = request.build_absolute_uri('/')  # mantém a barra no final
            base_url = base_url.rstrip('/')
            success_url = f"{base_url}{reverse('pagamento_sucesso')}"
            failure_url = f"{base_url}{reverse('pagamento_falha')}"
            pending_url = f"{base_url}{reverse('pagamento_pendente')}"
            notification_url = f"{base_url}{reverse('webhook_mercadopago')}"

            # 4. Itens do pedido
            items = [{
                "id": str(item.produto.id),
                "title": item.produto.nome[:127],
                "quantity": int(item.quantidade),
                "currency_id": "BRL",
                "unit_price": float(item.produto.preco)
            } for item in pedido.itens.all()]

            # 5. Dados da preferência
            preference_data = {
                "items": items,
                "payer": {
                    "email": request.user.email,
                    "name": request.user.first_name[:127],
                    "surname": request.user.last_name[:127],
                },
                "back_urls": {
                    "success": success_url,
                    "failure": failure_url,
                    "pending": pending_url
                },
                "auto_return": "approved", 
                "external_reference": str(pedido.id),
                "notification_url": notification_url,
                "binary_mode": True,
            }

            # 6. Criação da preferência
            preference_response = sdk.preference().create(preference_data)
            
            if preference_response['status'] not in [200, 201]:
                error_msg = preference_response.get('response', {}).get('message', 'Erro no Mercado Pago')
                logger.error(f"Erro MP: {error_msg}")
                raise Exception(error_msg)

            preference = preference_response['response']
            pedido.preference_id = preference['id']
            pedido.save()

            # 7. Redirecionamento
            init_point = preference.get('sandbox_init_point' if settings.DEBUG else 'init_point')
            if not init_point:
                raise Exception("URL de pagamento não gerada")

            return redirect(init_point)

        except Exception as e:
            logger.error(f"Erro no pagamento: {str(e)}", exc_info=True)
            
            if 'pedido' in locals():
                pedido.status = 'falhou'
                pedido.save()
            
            messages.error(request, f"Erro ao processar pagamento: {str(e)}")
            return render(request, 'web/pagamento_erro.html', {
                'error': str(e),
                'pedido_id': pedido.id if 'pedido' in locals() else None
            })


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
    


class PagamentoSucessoView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        # O external_reference é geralmente passado como parâmetro na URL de retorno
        pedido_id = request.GET.get('external_reference')
        if not pedido_id:
            return redirect('home')
        
        pedido = get_object_or_404(Pedido, id=pedido_id, usuario=request.user)
        
        # Atualiza o status do pedido se necessário
        if pedido.status == 'pendente':
            pedido.status = 'aprovado'
            pedido.save()
        
        return render(request, 'web/pagamento_sucesso.html', {'pedido': pedido})

class PagamentoFalhaView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        pedido_id = request.GET.get('external_reference')
        if not pedido_id:
            return redirect('home')
        
        pedido = get_object_or_404(Pedido, id=pedido_id, usuario=request.user)
        
        # Atualiza o status do pedido
        if pedido.status == 'pendente':
            pedido.status = 'falhou'
            pedido.save()
        
        return render(request, 'web/pagamento_falha.html', {'pedido': pedido})

class PagamentoPendenteView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        pedido_id = request.GET.get('external_reference')
        if not pedido_id:
            return redirect('home')
        
        pedido = get_object_or_404(Pedido, id=pedido_id, usuario=request.user)
        
        # Mantém como pendente (ou pode criar um status específico)
        if pedido.status == 'pendente':
            pedido.save()
        
        return render(request, 'web/pagamento_pendente.html', {'pedido': pedido})


@csrf_exempt
def webhook_mercadopago(request):
    if request.method != 'POST':
        return HttpResponse(status=405)  # Method Not Allowed
    
    try:
        data = json.loads(request.body)
        payment_id = data.get('data', {}).get('id')
        
        if not payment_id:
            return HttpResponse(status=400)  # Bad Request
        
        # Aqui você deve buscar a preferência/pagamento na API do Mercado Pago
        # para verificar os dados reais e atualizar seu sistema
        sdk = mercadopago.SDK(settings.MERCADO_PAGO_ACCESS_TOKEN)
        payment_info = sdk.payment().get(payment_id)
        
        if payment_info['status'] != 200:
            return HttpResponse(status=400)
        
        payment = payment_info['response']
        pedido_id = payment.get('external_reference')
        
        if not pedido_id:
            return HttpResponse(status=400)
        
        pedido = Pedido.objects.get(id=pedido_id)
        
        # Atualiza o status do pedido baseado no status do pagamento
        status_map = {
            'approved': 'aprovado',
            'pending': 'pendente',
            'in_process': 'processando',
            'rejected': 'falhou',
            'refunded': 'reembolsado',
            'cancelled': 'cancelado',
            'in_mediation': 'em_mediacao',
            'charged_back': 'estornado'
        }
        
        new_status = status_map.get(payment['status'], 'pendente')
        pedido.status = new_status
        pedido.payment_id = payment_id
        pedido.data_atualizacao = datetime.now()
        pedido.save()
        
        return HttpResponse(status=200)
    
    except Exception as e:
        # Logar o erro para debug
        print(f"Erro no webhook: {str(e)}")
        return HttpResponse(status=500)