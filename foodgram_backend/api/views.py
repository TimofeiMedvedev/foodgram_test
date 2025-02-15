from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.http.response import HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from recipes.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                            ShoppingCart, Tag)
from users.models import Follow

from .addition import counting_shop_list
from .filters import RecipeFilter
from .pagination import UserPagination
from .permissions import IsAuthorOrReadOnly
from .serializers import (CustomChangePasswordSerializer,
                          CustomCreateUserSerializer, CustomUserSerializer,
                          FavoriteSerializer, FollowCreateSerializer,
                          FollowSerializer, Ingredientserializer,
                          RecipeCreateSerializer, RecipeMiniSerializer,
                          RecipeReadSerializer, ShoppingCartSerializer,
                          TagSerializer)

User = get_user_model()

# FAVORITE_SHOPPING = {
#     'favorite': Favorite,
#     'shopping_cart': ShoppingCart
# }


class CustomUserViewSet(UserViewSet):

    queryset = User.objects.all()
    serializer_class = CustomUserSerializer
    filter_backends = (filters.SearchFilter,)
    pagination_class = UserPagination

    def get_permissions(self):
        if self.action in ['create', 'list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == 'create':
            return CustomCreateUserSerializer
        if self.action == 'set_password':
            return CustomChangePasswordSerializer
        return CustomUserSerializer

    # def get_serializer_context(self): 
    #     context = super().get_serializer_context() 
    #     context.update({'request': self.request}) 
    #     return context 

    @action(
        detail=True,
        methods=['POST', 'DELETE'],
        url_path='subscribe',
        permission_classes=(IsAuthenticated,)
    )
    def subscribe(self, request, id):
        if request.method == 'POST':
            serializer = FollowCreateSerializer(
                data={
                        'following': id,
                        'recipes_limit': request.query_params.get(
                            'recipes_limit'
                        )
                     },
                context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            user_following = serializer.save(user=request.user)
            user_following_data = FollowSerializer(
                user_following.following,
                context={'request': request}).data
            return Response(
                user_following_data,
                status=status.HTTP_201_CREATED
            )
        if request.method == 'DELETE':
            following = get_object_or_404(User, id=id)
        deleted, _ = Follow.objects.filter(
            user=request.user,
            following=following
        ).delete()
        if not deleted:
            raise ValidationError('Проблема с удалением.')
        return Response(status=status.HTTP_204_NO_CONTENT)
           

    @action(detail=False, methods=['GET'],
            permission_classes=(AllowAny,))
    def subscriptions(self, request):
        user = request.user
        queryset = User.objects.filter(following__user=user)
        recipes_limit = request.query_params.get('recipes_limit')

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = FollowSerializer(
                page,
                many=True,
                context={'request': request, 'recipes_limit': recipes_limit},
            )
            return self.get_paginated_response(serializer.data)
        serializer = FollowSerializer(
            queryset,
            many=True,
            context={'request': request, 'recipes_limit': recipes_limit},
        )
        return Response(serializer.data)

    @action(
        detail=False,
        methods=['PUT', 'DELETE'],
        permission_classes=[IsAuthenticated],
        url_path='me/avatar',
    )
    def avatar(self, request):
        user = request.user
        serializer = CustomUserSerializer(user, data=request.data,
                                          partial=True)

        if request.method == 'DELETE':
            if user.avatar:
                user.avatar.delete(save=True)
                return Response(status=status.HTTP_204_NO_CONTENT)
            return Response('Аватар не найден',
                            status=status.HTTP_404_NOT_FOUND)

        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'avatar': user.avatar.url},
                        status=status.HTTP_200_OK)


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [AllowAny]
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = Ingredientserializer
    pagination_class = None
    filter_backends = (filters.SearchFilter,)
    search_fields = ('^name',)
    name = search_fields


class RecipeViewSet(viewsets.ModelViewSet):
    filter_backends = (DjangoFilterBackend, )
    serializer_class = RecipeReadSerializer
    filterset_class = RecipeFilter
    pagination_class = UserPagination


    def get_queryset(self):
        return Recipe.objects.prefetch_related(
            'ingredients', 'tags'
        ).select_related(
            'author'
        ).order_by('name')

    def get_serializer_class(self):
        if self.action in ['list', 'retrive',]:
            return RecipeReadSerializer
        return RecipeCreateSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy',
                           'favorite', 'download_shopping_cart',
                           'shopping_cart',]:
            return [IsAuthenticated(), IsAuthorOrReadOnly()]
        return [AllowAny()]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True, methods=['GET'], url_path='get-link')
    def get_short_link(self, request, pk=None):
        url = request.build_absolute_uri(
            reverse('api:recipes-detail', args={pk}))
        clear_url = url.replace('api/', '')

        return Response(
            {'short-link': clear_url},
            status=status.HTTP_200_OK
        )


    @action(
        detail=True,
        methods=['POST', 'DELETE'],
        url_path='shopping_cart',
        url_name='shopping_cart',
        permission_classes=(IsAuthenticated,),
    )
    def shopping_cart(self, request, pk=None):
        if request.method == 'POST':
            return self.shopping_favorite_create(
                request,
                ShoppingCartSerializer,
                pk=pk
            )
        if request.method == 'DELETE':
            return self.shopping_favorite_delete(
                request,
                ShoppingCart,
                pk=pk
            )

    @action(
        detail=False,
        methods=['GET'],
        url_path='download_shopping_cart',
        permission_classes=[IsAuthenticated, ],
    )
    def download_cart(self, request):
        user = request.user
        response = HttpResponse(content_type="text/plain")
        ingredients = RecipeIngredient.objects.filter(
            recipe__recipe_cart__user=user
        ).values(
            'ingredient__name',
            'ingredient__measurement_unit').annotate(amount=Sum('amount'))
        response = HttpResponse(
            counting_shop_list(ingredients), 
            content_type='text/plain')
        response['Content-Disposition'] = (
            'attachment; filename="shopping_cart.txt"'
        )
        return response 
    
    @action(
        detail=True,
        methods=['POST', 'DELETE'],
        url_path='favorite',
        permission_classes=(IsAuthenticated,),
    )
    def favorite(self, request, pk=None):
        if request.method == 'POST':
            return self.shopping_favorite_create(
                request,
                FavoriteSerializer,
                pk=pk
            )
        if request.method == 'DELETE':
            return self.shopping_favorite_delete(
                request,
                Favorite,
                pk=pk
            )

    def shopping_favorite_create(self, request, serializer_create, pk=None):
        serializer = serializer_create(
            data={'recipe': pk},
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        shop_favorite = serializer.save(user=request.user)
        shop_favorite_data = RecipeMiniSerializer(
            shop_favorite.recipe,
            context={'request': request}).data
        return Response(
            data=shop_favorite_data,
            status=status.HTTP_201_CREATED
        )
    
    def shopping_favorite_delete(self, request, model, pk=None):

        recipe = get_object_or_404(Recipe, id=pk)
        deleted, _ = model.objects.filter(
            user=request.user,
            recipe=recipe
        ).delete()
        if not deleted:
            raise ValidationError('Проблема с удалением.')
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    
