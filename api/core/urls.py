from rest_framework import routers
from .views import UserViewSet, RegisterView, LoginView, LogoutView, MeView
from django.urls import path, include

router = routers.DefaultRouter()
router.register(r'users', UserViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('register/', RegisterView.as_view(), name='register'),
    path('users/me', MeView.as_view(), name='me'),
]
