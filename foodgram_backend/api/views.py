from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.http.response import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from recipes.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                            ShoppingCart, Tag)
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from users.models import Follow
from django.urls import reverse
from django.http import HttpResponseRedirect

from .filters import RecipeFilter
from .pagination import UserPagination
from .permissions import IsAuthorOrReadOnly
from .serializers import (CustomChangePasswordSerializer,
                          CustomCreateUserSerializer, CustomUserSerializer,
                          FollowSerializer, Ingredientserializer,
                          RecipeCreateSerializer, RecipeMiniSerializer,
                          RecipeReadSerializer, TagSerializer,
                          ShoppingCartSerializer, FavoriteSerializer)
from .countfile import counting_shop_list
from django.core.exceptions import ValidationError

User = get_user_model()

FAVORITE_SHOPPING = {
    'favorite': Favorite,
    'shopping_cart': ShoppingCart
}


class CustomUserViewSet(UserViewSet):

    queryset = User.objects.all()
    serializer_class = CustomUserSerializer
    filter_backends = (filters.SearchFilter,)
    pagination_class = UserPagination

    def get_permissions(self):
        if self.action in ["create", "list", "retrieve"]:
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == "create":
            return CustomCreateUserSerializer
        if self.action == "set_password":
            return CustomChangePasswordSerializer
        return CustomUserSerializer
    
    def get_serializer_context(self):
        """Метод для передачи контекста. """

        context = super().get_serializer_context()
        context.update({'request': self.request})
        return context


    @action(
        detail=True,
        methods=['POST', 'DELETE'],
        permission_classes=(IsAuthenticated,)
    )
    def subscribe(self, request, id):
        following = get_object_or_404(User, id=id)
        following_availability = Follow.objects.filter(
            user=request.user,
            following=following
        ).exists()
        if request.method == 'POST':
            if following_availability:
                return Response(
                    {'errors': 'Подписка на этого пользователя уже есть'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if request.user == following:
                return Response(
                    {'errors': 'Нельзя подписаться на самого себя!'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            serializer = FollowSerializer(
                following,
                data=request.data,
                context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            
            if Follow.objects.create(
                user=request.user,
                following=following
            ):
                recipes_limit = request.query_params.get('recipes_limit')
                serializer = FollowSerializer(
                    following,
                    context={
                        'request': request,
                        "recipes_limit": recipes_limit
                    }
                )
            serializer.save()
            return Response(serializer.data,
                            status=status.HTTP_201_CREATED)
        if request.method == 'DELETE':
            if not following_availability:
                return Response(
                    {'errors': 'Такого пользователя не существует'},
                    status=status.HTTP_400_BAD_REQUEST
                )
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
    filter_backends = (DjangoFilterBackend, )
    serializer_class = RecipeReadSerializer
    filterset_class = RecipeFilter
    pagination_class = UserPagination


    def get_queryset(self):
        return Recipe.objects.all().prefetch_related(
            'ingredients', 'tags'
        ).select_related(
            'author'
        ).all()

    def get_serializer_class(self):
        if self.action in ['list', 'retrive',]:
            return RecipeReadSerializer
        return RecipeCreateSerializer

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", 'destroy',
                           "favorite", "download_shopping_cart",
                           "shopping_cart",]:
            return [IsAuthenticated(), IsAuthorOrReadOnly()]
        return [AllowAny()]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True, methods=['GET'], url_path='get-link')
    def get_short_link(self, request, pk=None):
        url = reverse('api:recipes-detail', args={pk})
        return Response({'direct-link': url},
                        status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=['POST', 'DELETE'],
        url_path='shopping_cart',
        url_name='shopping_cart',
        permission_classes=(IsAuthenticated,),
    )
    def shopping_cart_create(self, request, pk=None):
        return self.shopping_favorite(
            request, ShoppingCart,
            ShoppingCartSerializer, pk=pk
        )
        # serializer = ShoppingCartSerializer(data={'recipe': pk},
        #                                     context={'request': request})
        # serializer.is_valid(raise_exception=True)
        # shopping_cart = serializer.save(user=request.user)
        # shopping_cart_data = RecipeMiniSerializer(
        #     shopping_cart.recipe,
        #     context={'request': request}).data

        # if request.method == 'DELETE':
        #     recipe = get_object_or_404(Recipe, id=pk)
        #     deleted, _ = ShoppingCart.objects.filter(
        #         user=request.user,
        #         recipe=recipe
        #         ).delete()
        #     if not deleted:
        #         raise ValidationError('Проблема с удалением рецепта.')
        # return Response(
        #     data=shopping_cart_data,
        #     status=status.HTTP_201_CREATED
        # )
    # def shopping_cart(self, request, pk=None):
    #     return self.favorite_shop(request, ShoppingCart, pk=pk)

    # @action(detail=False, methods=['GET'],
    #         url_path='download_shopping_cart',
    #         permission_classes=[IsAuthenticated, ])
    # def download_cart(self, request):
    #     user = request.user
    #     response = HttpResponse(content_type='text/plain')
    #     shopping_cart = ShoppingCart.objects.filter(user=user).values_list(
    #         "recipe", flat=True
    #     )
    #     ingredients = RecipeIngredient.objects.filter(
    #         recipe__in=shopping_cart,
    #         ).values(
    #         'ingredient__name',
    #         'ingredient__measurement_unit'
    #     ).annotate(
    #         amount=Sum('amount')
    #     )
    #     download_cart_list = ('customer order\n'
    #                           'Ингредиенты:\n')
    #     for ingredient in ingredients:
    #         download_cart_list += (
    #             f"{ingredient['ingredient__name']}  - "
    #             f"{ingredient['amount']}"
    #             f"{ingredient['ingredient__measurement_unit']}\n"
    #         )
    #     response = HttpResponse(download_cart_list, content_type='text/plain')
    #     response['Content-Disposition'] = \
    #         'attachment; filename="shopping_cart.txt"'
    #     return response
    
    @action(
        detail=False, 
        methods=['GET'],
        url_path='download_shopping_cart',
        permission_classes=[IsAuthenticated, ],
    )
    def download_cart(self, request):
        user = request.user
        response = HttpResponse(content_type='text/plain')
        shopping_cart = ShoppingCart.objects.filter(user=user)
        recipes = [item.recipe.id for item in shopping_cart]
        ingredients = RecipeIngredient.objects.filter(
            recipe__in=recipes,
        ).values(
            'ingredient',
        ).annotate(
            amount=Sum('amount')
        )

        response = HttpResponse(
            counting_shop_list(ingredients),
            content_type='text/plain'
        )
        response['Content-Disposition'] = \
            'attachment; filename="shopping_cart.txt"'
        return response

    @action(
        detail=True,
        methods=['POST', 'DELETE'],
        url_path='favorite',
        permission_classes=(IsAuthenticated,),
    )
    def favorite(self, request, pk=None):
        return self.favorite_shop(request, Favorite, FavoriteSerializer, pk=pk)

    def shopping_favorite(self, request, model, serializer_create, pk=None):
        serializer = serializer_create(
            data={'recipe': pk},
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        shopping_cart = serializer.save(user=request.user)
        shopping_cart_data = RecipeMiniSerializer(
            shopping_cart.recipe,
            context={'request': request}).data

        if request.method == 'DELETE':
            recipe = get_object_or_404(Recipe, id=pk)
            deleted, _ = model.objects.filter(
                user=request.user,
                recipe=recipe
                ).delete()
            if not deleted:
                raise ValidationError('Проблема с удалением.')
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            data=shopping_cart_data,
            status=status.HTTP_201_CREATED
        )

    # def favorite_shop(self, request, model, pk=None):
    #     recipe = get_object_or_404(Recipe, id=pk)
            
    #     if request.method == 'POST':
    #         if model.objects.filter(
    #             user=request.user,
    #             recipe=recipe
    #         ).exists():
    #             return Response(
    #                 {'errors': 'Этот рецепт уже есть!'},
    #                 status=status.HTTP_400_BAD_REQUEST
    #                 )
    #         model.objects.create(
    #             user=request.user,
    #             recipe=recipe
    #         )
            
    #         serializer = RecipeMiniSerializer(
    #             recipe,
    #             context={'request': request}).data
            
    #         serializer.is_valid(raise_exception=True)
    #         serializer.save()
    #         return Response(serializer.data,
    #                         status=status.HTTP_201_CREATED)

    #     if request.method == 'DELETE':
    #         favorite_object = model.objects.filter(
    #             user=request.user,
    #             recipe=recipe
    #         )
    #         if favorite_object.exists():
    #             favorite_object.delete()
    #             return Response(status=status.HTTP_204_NO_CONTENT)
    #         return Response(
    #             {'errors': 'Нельзя удалить рецепт которого нет в избранном!'},
    #             status=status.HTTP_400_BAD_REQUEST)
            # deleted, _ = model.objects.filter(...).delete()
            # if not deleted: raise ValidationError(проблема)


# @action(
#         detail=False,
#         methods=['GET'],
#         permission_classes=(IsAuthenticated,)
#     )
#     def download_shopping_cart(self, request):
#         shopping_cart = ShoppingCart.objects.filter(user=self.request.user)
#         recipes = [item.recipe.id for item in shopping_cart]
#         shop_list = IngredientDetale.objects.filter(
#             recipe__in=recipes
#         ).values(
#             'ingredient'
#         ).annotate(
#             amount=Sum('amount')
#         )
#         shop_list_text = 'Список покупок'
#         for item in shop_list:
#             ingredient = Ingredient.objects.get(pk=item['ingredient'])
#             amount = item['amount']
#             shop_list_text += (
#                 f'Наименование: {ingredient.name}, количество {amount} '
#                 f'{ingredient.measurement_unit}\n'
#             )

#         response = HttpResponse(shop_list_text, content_type='application/pdf')
#         response['Content-disposition'] = (
#             'attachment; filename=shopping-list.pdf'
#         )
#         return response


 