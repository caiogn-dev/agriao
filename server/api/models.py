

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin, User
from django.db import models
from django.conf import settings
from django.templatetags.static import static
import os

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("O email é obrigatório")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []  # Remova 'username'

    objects = CustomUserManager()

    def __str__(self):
        return self.email

class ProdutoMarmita(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.TextField()
    kcal = models.PositiveIntegerField()
    proteinas = models.DecimalField(max_digits=6, decimal_places=2)
    preco = models.DecimalField(max_digits=8, decimal_places=2)
    data_criacao = models.DateTimeField(auto_now_add=True)
    ativo = models.BooleanField(default=True)
    imagem = models.ImageField(upload_to='produtos/', blank=True, null=True)

    @property
    def imagem_url_segura(self):
        try:
            if self.imagem and os.path.exists(self.imagem.path):
                return self.imagem.url
        except Exception:
            pass
        return static('img/padrao.png')

    def __str__(self):
        return self.nome

class Carrinho(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Carrinho de {self.usuario.username}"

    @property
    def get_total(self):
        return sum(item.get_total for item in self.itens.all())

class ItemCarrinho(models.Model):
    carrinho = models.ForeignKey(Carrinho, on_delete=models.CASCADE, related_name='itens')
    produto = models.ForeignKey(ProdutoMarmita, on_delete=models.CASCADE)
    quantidade = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.quantidade}x {self.produto.nome} no carrinho de {self.carrinho.usuario.username}"

    @property
    def get_total(self):
        return self.produto.preco * self.quantidade

class Pedido(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    payment_id = models.CharField(max_length=100, blank=True, null=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='pendente')
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"Pedido #{self.id} de {self.usuario.username}"

class ItemPedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='itens')
    produto = models.ForeignKey(ProdutoMarmita, on_delete=models.CASCADE)
    quantidade = models.PositiveIntegerField(default=1)
    preco_unitario = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return f"{self.quantidade}x {self.produto.nome} no pedido #{self.pedido.id}"
