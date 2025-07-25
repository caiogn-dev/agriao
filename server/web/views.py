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
                    "success": "https://agriao.shop/pagamento/sucesso/",
                    "failure": "https://agriao.shop/pagamento/falha/",
                    "pending": "https://agriao.shop/pagamento/pendente/",
                },
                "auto_return": "approved",  # Corrigido aqui
                "external_reference": str(pedido.id),
                "notification_url": request.build_absolute_uri(reverse('webhook_mercadopago')),
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


class MeusPedidosView(LoginRequiredMixin, ListView):
    model = Pedido
    template_name = 'web/meus_pedidos.html'
    context_object_name = 'pedidos'

    def get(self, request, *args, **kwargs):
        try:
            return super().get(request, *args, **kwargs)
        except Exception as e:
            logger.exception("Erro ao listar pedidos para o usuário %s", request.user)
            messages.error(request, "Ocorreu um erro ao carregar seus pedidos. Tente novamente mais tarde.")
            return redirect('home')

    def get_queryset(self):
        # Garante que o campo existe
        if not hasattr(Pedido, 'criado_em'):
            raise AttributeError("O modelo Pedido não possui o campo 'criado_em'")
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
def mercado_pago_webhook(request):
    # 1) Handshake: aceita GET para validação
    if request.method in ("GET", "HEAD"):
        return HttpResponse("OK", status=200)

    if request.method != "POST":
        return HttpResponse(status=405)

    try:
        # 2) Parse do JSON
        payload = json.loads(request.body.decode('utf-8'))
        logger.info("MP Webhook payload: %s", payload)

        # 3) Identifica evento e recurso
        action = payload.get('action') or payload.get('topic') or payload.get('type')
        resource_id = payload.get('data', {}).get('id')

        # 4) Instancia SDK (token já vem de settings)
        sdk = mercadopago.SDK(settings.MERCADO_PAGO_ACCESS_TOKEN)

        # 5) Trata pagamento (PIX, cartão etc)
        if action and 'payment' in action:
            resp = sdk.payment().get(resource_id)
            payment = resp.get('response', {})
            pedido_id = payment.get('external_reference')
            if pedido_id:
                pedido = Pedido.objects.filter(id=pedido_id).first()
                if pedido:
                    status_map = {
                        'approved': 'aprovado',
                        'pending': 'pendente',
                        'in_process': 'processando',
                        'rejected': 'falhou',
                        'refunded': 'reembolsado',
                        'cancelled': 'cancelado',
                        'in_mediation': 'em_mediacao',
                        'charged_back': 'estornado',
                    }
                    novo = status_map.get(payment.get('status'), pedido.status)
                    pedido.status = novo
                    pedido.payment_id = resource_id
                    pedido.data_atualizacao = now()
                    pedido.save()

        # 6) Trata merchant_order (caso precise consolidar vários pagamentos)
        elif action and 'merchant_order' in action:
            resp = sdk.merchant_order().get(resource_id)
            mo = resp.get('response', {})
            for pay in mo.get('payments', []):
                ref = pay.get('external_reference')
                pedido = Pedido.objects.filter(id=ref).first()
                if pedido and pay.get('status') == 'approved':
                    pedido.status = 'aprovado'
                    pedido.payment_id = pay.get('id')
                    pedido.data_atualizacao = now()
                    pedido.save()

    except Exception:
        logger.exception("Erro ao processar webhook do Mercado Pago")
    finally:
        # 7) Sempre responde 200 para não ficar em loop de tentativas
        return HttpResponse("OK", status=200)
    

## VIEW PARA PEDIDOS DETALHADOS ## 
class DetalhesPedidoView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        pedido_id = kwargs.get('pedido_id')
        pedido = get_object_or_404(Pedido, id=pedido_id, usuario=request.user)

        # 1) Se estiver pendente, manda pra página de pendente
        if pedido.status == 'pendente':
            url = reverse('pagamento_pendente')
            return redirect(f"{url}?external_reference={pedido.id}")

        # 2) Se aprovado ou pago, mostra o template de WhatsApp
        if pedido.status in ('aprovado', 'pago'):
            itens_str = "\n".join(
                f"- {item.quantidade}x {item.produto.nome}" for item in pedido.itens.all()
            )
            raw_message = (
                f"Olá! Gostaria de confirmar meu pedido #{pedido.id}:\n\n"
                f"{itens_str}\n\nTotal: R$ {pedido.total}"
            )
            context = {
                'pedido': pedido,
                'whatsapp_url': (
                    f"https://wa.me/{settings.MERCADO_PAGO_WHATSAPP_NUMBER}"
                    f"?text={quote(raw_message)}"
                )
            }
            return render(request, 'web/pedido_whatsapp.html', context)

        # 3) Falha
        if pedido.status in ('falhou', 'rejected', 'cancelado'):
            url = reverse('pagamento_falha')
            return redirect(f"{url}?external_reference={pedido.id}")

        # 4) Qualquer outro status (p.ex. em_mediacao)
        messages.info(request, f"Status do pedido: {pedido.status}.")
        return render(request, 'web/pedido_status.html', {'pedido': pedido})