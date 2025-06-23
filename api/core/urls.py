from rest_framework import routers
from .views import UserViewSet, RegisterView
from django.urls import path, include
from .auth_views import LoginView

router = routers.DefaultRouter()
router.register(r'users', UserViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('login/', LoginView.as_view(), name='login'),
    path('register/', RegisterView.as_view(), name='register'),
]
