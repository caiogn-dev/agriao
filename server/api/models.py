from django.db import models
from django.contrib.auth.models import User

class ProdutoMarmita(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.TextField()
    kcal = models.PositiveIntegerField()
    proteinas = models.DecimalField(max_digits=6, decimal_places=2)
    preco = models.DecimalField(max_digits=8, decimal_places=2)
    data_criacao = models.DateTimeField(auto_now_add=True)
    ativo = models.BooleanField(default=True)
    imagem = models.ImageField(upload_to='produtos/', blank=True, null=True)

    def __str__(self):
        return self.nome

class Carrinho(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
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
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
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
