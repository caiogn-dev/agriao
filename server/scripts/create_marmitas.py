import os
import sys
import django

# Adiciona o caminho da raiz do projeto ao sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/../')

# Configura o ambiente Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.settings')
django.setup()

# Importa o modelo
from api.models import ProdutoMarmita

# Marmitas
marmitas = [
    ("Strogonoff de Frango, arroz integral e batata rustica", "Strogonoff de Frango, arroz integral e batata rústica"),
    ("Filé de frango com creme de milho/arroz e legumes", "Filé de frango com creme de milho, arroz e legumes"),
    ("Kibe assado recheado com cream cheese e purê de batata", "Kibe assado recheado com cream cheese e purê de batata"),
    ("Macarrão ao pesto com frango desfiado", "Macarrão ao pesto com frango desfiado"),
    ("Panqueca de calabresa com queijo no molho branco (sem glúten)", "Panqueca de calabresa com queijo no molho branco (sem glúten)"),
    ("Panqueca de frango sem glúten", "Panqueca de frango sem glúten"),
    ("Kibe assado recheado, arroz integral e purê de abóbora", "Kibe assado recheado, arroz integral e purê de abóbora"),
    ("Lasanha de frango com abobrinha", "Lasanha de frango com abobrinha"),
    ("Feijoada light, arroz branco e farofa", "Feijoada light, arroz branco e farofa"),
    ("Linguiça assada com batatas, arroz branco e feijão", "Linguiça assada com batatas, arroz branco e feijão"),
    ("Parmegiana de frango, arroz integral e batata doce assada", "Parmegiana de frango, arroz integral e batata doce assada"),
    ("Carne moída, arroz branco e feijão", "Carne moída, arroz branco e feijão"),
    ("Sobrecoxa recheada com gratinado de couve flor", "Sobrecoxa recheada com gratinado de couve flor"),
    ("Bolo de carne recheado com abóbora assada", "Bolo de carne recheado com abóbora assada"),
    ("Filé ao creme de palmito, arroz integral e legumes", "Filé ao creme de palmito, arroz integral e legumes"),
    ("Sobrecoxa recheada, arroz branco e feijão", "Sobrecoxa recheada, arroz branco e feijão"),
    ("Strogonoff de carne, arroz integral e batata rústica", "Strogonoff de carne, arroz integral e batata rústica"),
    ("Almondegas de carne, arroz integral e purê de batata", "Almondegas de carne, arroz integral e purê de batata"),
    ("Escondidinho de frango com mandioquinha", "Escondidinho de frango com mandioquinha"),
    ("Panqueca de espinafre com ricota", "Panqueca de espinafre com ricota"),
]

# Cria os produtos
for nome, descricao in marmitas:
    produto, criado = ProdutoMarmita.objects.get_or_create(
        nome=nome,
        defaults={
            'descricao': descricao,
            'kcal': 400,
            'proteinas': 25.0,
            'preco': 22.90,
            'ativo': True
        }
    )
    if criado:
        print(f"✅ Criado: {nome}")
    else:
        print(f"ℹ️ Já existia: {nome}")