from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import TagViewSet, IngredientViewSet, RecipeViewSet, avatar, follow


app_name = 'api'

router_v1 = DefaultRouter()
router_v1.register("tags", TagViewSet, basename="tags")
router_v1.register('ingredients', IngredientViewSet, basename='ingredients')
router_v1.register('recipes', RecipeViewSet, basename='recipes')

avatar_v1 = [
    path('avatar/', avatar),
]
subscribe_v1 = [
    path('subscribe/', follow),
]
urlpatterns = [
    path('', include(router_v1.urls)),
    path('', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),
    path('users/me/', include(avatar_v1)),
    path('users/<int:id>/', include(subscribe_v1)),
]