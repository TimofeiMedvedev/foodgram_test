from django.contrib.auth import get_user_model
from rest_framework import filters, viewsets,  status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from recipes.models import Tag, Recipe, Ingredient, RecipeIngredient, ShoppingCart, Favorite
from users.models import Follow
from .permissions import IsAuthorOrReadOnly
from django.shortcuts import get_object_or_404
from django.http.response import HttpResponse
from djoser.views import UserViewSet
from .pagination import UserPagination
from django_filters.rest_framework import DjangoFilterBackend
from .filters import RecipeFilter
from django.db.models import Sum
from rest_framework.views import exception_handler
from rest_framework.exceptions import APIException
from rest_framework import filters

class No(APIException):
    status_code = status.HTTP_404_NOT_FOUND

from .serializers import (
    CustomCreateUserSerializer, 
    CustomUserSerializer, 
    TagSerializer, 
    RecipeReadSerializer, 
    Ingredientserializer, 
    RecipeCreateSerializer, 
    RecipeMiniSerializer, 
    FollowSerializer,
    CustomChangePasswordSerializer
)


User = get_user_model()

class CustomUserViewSet(UserViewSet):

    queryset = User.objects.all()
    serializer_class = CustomUserSerializer
    filter_backends = (filters.SearchFilter,)
    pagination_class = UserPagination

    def get_permissions(self):
        if self.action in ["create", "list", "retrieve"]:
            return [AllowAny()]
        return [IsAuthenticated()]
   
    # def get_serializer_class(self):
    #     if self.request.method == 'GET':
    #         return CustomUserSerializer
    #     return CustomCreateUserSerializer
    
    def get_serializer_class(self):
        if self.action == "create":
            return CustomCreateUserSerializer
        if self.action == "set_password":
            return CustomChangePasswordSerializer
        return CustomUserSerializer

    @action(
        detail=True,
        methods=['POST', 'DELETE'],
        permission_classes=(IsAuthenticated,)
    )
    def subscribe(self, request, id):
        following = get_object_or_404(User, id=id)
        following_availability = Follow.objects.filter(user=request.user, following=following).exists()
        if request.method == 'POST':
            if following_availability == True:
                return Response({'errors': 'Подписка на этого пользователя уже есть'},
                                status=status.HTTP_400_BAD_REQUEST)
            
            if request.user == following:
                return Response({'errors': 'Нельзя подписаться на самого себя!'},
                                status=status.HTTP_400_BAD_REQUEST)
            serializer = FollowSerializer(
                following,
                data=request.data,
                context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
        
            if Follow.objects.create(user=request.user,
                                  following=following):
                recipes_limit = request.query_params.get('recipes_limit')
                serializer = FollowSerializer(
                following, context={'request': request,
                                 "recipes_limit": recipes_limit}
            )
            return Response(serializer.data,
                            status=status.HTTP_201_CREATED)
        if request.method == 'DELETE':
            if following_availability == False:
                return Response({'errors': 'Такого пользователя не существует'},
                                status=status.HTTP_400_BAD_REQUEST)
            get_object_or_404(
                Follow, user=request.user, following=following
            ).delete()
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
    queryset = Recipe.objects.all()
    filter_backends = (DjangoFilterBackend, )
    serializer_class = RecipeReadSerializer
    filterset_class = RecipeFilter
    pagination_class = UserPagination

    def get_serializer_class(self):
        if self.action in ['list', 'retrive',]:
            return RecipeReadSerializer
        return RecipeCreateSerializer
    
    # def get_serializer_context(self):
    #     """Метод для передачи контекста. """

    #     context = super().get_serializer_context()
    #     context.update({'request': self.request})
    #     return context


    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", 'destroy',
                           "favorite", "download_shopping_cart",
                           "shopping_cart",]:
            return [IsAuthenticated(), IsAuthorOrReadOnly()]
        return [AllowAny()]
   
    def perform_create(self, serializer):
        if self.request.user.is_authenticated:
            serializer.save(author=self.request.user)
    
    
    @action(detail=True, methods=['GET'], url_path='get-link')
    def get_short_link(self, request, pk=None):
        recipe = self.get_object()
        short_link = recipe.get_or_create_short_link()
        short_url = request.build_absolute_uri(f'/s/{short_link}')
        return Response({"short-link": short_url},
                        status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['POST', 'DELETE'],
        url_path='shopping_cart',
        url_name='shopping_cart',
        permission_classes=(IsAuthenticated,),
    )

    def shopping_cart(self, request, pk=None):
        recipe = get_object_or_404(Recipe,id=pk)
        cart_availability = ShoppingCart.objects.filter(user=request.user, recipe=recipe).exists()
        if request.method == 'POST':
            if cart_availability == True:
                return Response({'errors': 'Рецепт уже есть в корзине!'},
                                status=status.HTTP_400_BAD_REQUEST)
            
            ShoppingCart.objects.create(user=request.user,
                                        recipe=recipe)
            serializer = RecipeMiniSerializer(recipe)
            return Response(serializer.data,
                            status=status.HTTP_201_CREATED)
       
        if request.method == 'DELETE':
            shop_object = ShoppingCart.objects.filter(user=request.user, recipe__id=pk)
            if shop_object.exists():
                shop_object.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            return Response(
                {'errors': f'Нельзя удалить рецепт которого нет в списке покупок '},
                status=status.HTTP_400_BAD_REQUEST
            )
        
    @action(detail=False, methods=['GET'],
            url_path='download_shopping_cart',
            permission_classes=[IsAuthenticated, ])
    def download_cart(self, request):
        user = request.user
        response = HttpResponse(content_type='text/plain')
        shopping_cart = ShoppingCart.objects.filter(user=user).values_list(
            "recipe", flat=True
        )
        ingredients = RecipeIngredient.objects.filter(
            recipe__in=shopping_cart,
            ).values(
            'ingredient__name', 
            'ingredient__measurement_unit'
        ).annotate(
            amount=Sum('amount')
        )
        download_cart_list = ('customer order\n'
                              'Ингредиенты:\n')
        for ingredient in ingredients:
            download_cart_list += (
                f"{ingredient['ingredient__name']}  - "
                f"{ingredient['amount']}"
                f"{ingredient['ingredient__measurement_unit']}\n"
            )
        response = HttpResponse(download_cart_list, content_type='text/plain')
        response['Content-Disposition'] = \
            'attachment; filename="shopping_cart.txt"'
        return response
    

    @action(detail=True, methods=['POST', 'DELETE'],
    url_path='favorite',
    permission_classes=(IsAuthenticated,),
    )
    
    def favorite(self, request, pk=None):
        recipe = get_object_or_404(Recipe, id=pk)
        if request.method == 'POST':
            if Favorite.objects.filter(user=request.user,
                                           recipe=recipe).exists():
                return Response({'errors': 'Этот рецепт уже есть в избранном!'},
                                status=status.HTTP_400_BAD_REQUEST)
            Favorite.objects.create(user=request.user,
                                        recipe=recipe)
            serializer = RecipeMiniSerializer(recipe)
            return Response(serializer.data,
                            status=status.HTTP_201_CREATED)
       
        
        if request.method == 'DELETE':
            favorite_object = Favorite.objects.filter(user=request.user, recipe=recipe)
            if favorite_object.exists():
                favorite_object.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            return Response(
                {'errors': f'Нельзя удалить рецепт которого нет в избранном!'},
                status=status.HTTP_400_BAD_REQUEST)
    
        # if request.method == 'DELETE':
        #     Favorite.objects.filter(
        #         user=request.user,
        #         recipe=recipe
        #     ).delete()
        #     return Response(status=status.HTTP_204_NO_CONTENT)
    
    
 
        
    
    

