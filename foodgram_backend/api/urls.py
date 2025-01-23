from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import avatar


app_name = 'api'

# router = DefaultRouter()
# router.register('users', UserViewSet, basename='users')

auth_v1 = [
    path('avatar/', avatar),
]

urlpatterns = [
    path('', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),
    path('users/me/', include(auth_v1)),
]