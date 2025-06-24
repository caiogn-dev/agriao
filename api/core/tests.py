from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from .models import CustomUser

class RegisterViewTest(APITestCase):
    def test_register_success(self):
        url = reverse('register')
        data = {
            'username': 'testuser',
            'name': 'Test User',
            'email': 'test@example.com',
            'phone': '11999999999',
            'password': 'testpassword',
            'address': 'Rua Exemplo, 123',
            'city': 'Cidade',
            'zip': '12345-678'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('message', response.data)

    def test_register_invalid(self):
        url = reverse('register')
        data = {
            'username': '',
            'name': 'Te',  # nome muito curto
            'email': 'not-an-email',
            'password': '123',  # senha curta
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

class LoginViewTest(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='loginuser',
            name='Login User',
            email='login@example.com',
            password='loginpassword'
        )

    def test_login_success(self):
        url = reverse('login')
        data = {
            'email': 'login@example.com',
            'password': 'loginpassword'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)

    def test_login_invalid(self):
        url = reverse('login')
        data = {
            'email': 'login@example.com',
            'password': 'wrongpassword'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data)
