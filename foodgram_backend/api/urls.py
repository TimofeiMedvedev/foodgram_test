from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (UserViewSet)

app_name = 'api'


router_v1 = DefaultRouter()
# router_v1.register(r'users', UserViewSet, basename='users')

urlpatterns = [
    # path('', include(router_v1.urls), name='api-root'),
    path('', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),
]