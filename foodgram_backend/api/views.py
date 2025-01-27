from django.contrib.auth import get_user_model
from rest_framework import filters, viewsets,  status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from recipes.models import Tag, Recipe, Ingredient, RecipeIngredient, ShoppingCart, Favorite
from users.models import Follow
from .permissions import IsAuthorOrReadOnly
from django.shortcuts import get_object_or_404
from django.db.models import Sum
from django.http.response import HttpResponse


from .serializers import (CustomCreateUserSerializer, CustomUserSerializer, 
                          TagSerializer, RecipeReadSerializer, Ingredientserializer, 
                          RecipeCreateSerializer, RecipeMiniSerializer, FollowSerializer)


User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    """ViewSet модели User."""

    queryset = User.objects.all()
    permission_classes = None
    serializer_class = CustomUserSerializer
    filter_backends = (filters.SearchFilter,)
   
    def get_serializer_class(self):
        if self.request.method == 'POST':
           return CustomCreateUserSerializer
        
@api_view(('POST', 'DELETE'))
@permission_classes((IsAuthenticated,))
def follow(request, id):
    following = get_object_or_404(User, id=id)
    if request.method == 'POST':
        if Follow.objects.filter(user=request.user,
                                following=following).exists():
            return Response({'errors': 'Подписка уже оформлена!'},
                            status=status.HTTP_400_BAD_REQUEST)
        if request.user == following:
            return Response({'errors': 'Нельзя подписаться на себя!'},
                            status=status.HTTP_400_BAD_REQUEST)
        serializer = FollowSerializer(
            following,
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        Follow.objects.create(user=request.user,
                             following=following)
        return Response(serializer.data,
                        tatus=status.HTTP_201_CREATED)
    if request.method == 'DELETE':
        get_object_or_404(
            Follow, user=request.user, following=following
        ).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
        

   
@api_view(('PUT', 'DELETE'))
@permission_classes((IsAuthenticated,))

def avatar(request):
    user = request.user
    serializer = CustomUserSerializer(user, data=request.data,
                                      partial=True)

    if request.method == "DELETE":
        if user.avatar:
            user.avatar.delete(save=True)
            return Response(status=status.HTTP_204_NO_CONTENT)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response({'avatar': user.avatar.url},
                    status=status.HTTP_200_OK)
    

class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [AllowAny]
    pagination_class = None

class IngredientViewSet(viewsets.ModelViewSet):
    """Вьюсет для IngredientSerializer."""
    queryset = Ingredient.objects.all()
    serializer_class = Ingredientserializer
    permission_classes = (IsAuthorOrReadOnly,)
    pagination_class = None

class RecipeViewSet(viewsets.ModelViewSet):
    """Вьюсет для RecipeSerializer."""
    queryset = Recipe.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = RecipeReadSerializer

    def perform_create(self, serializer):
        return serializer.save(author=self.request.user)

    def get_serializer_class(self):
        if self.action in ['list', 'retrive']:
            return RecipeReadSerializer
        return RecipeCreateSerializer
    
    @action(detail=True, methods=['GET'], url_path='get-link')
    def get_short_link(self, request, pk=None):
        recipe = self.get_object()
        short_link = recipe.get_or_create_short_link()
        short_url = request.build_absolute_uri(f'/s/{short_link}')
        return Response({"short-link": short_url},
                        status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['POST', 'DELETE'],
        permission_classes=(IsAuthenticated,),
        pagination_class=None)
    def shopping_cart(self, request, pk=None):
        recipe = get_object_or_404(Recipe, id=pk)
        if request.method == 'POST':
            ShoppingCart.objects.create(user=request.user,
                                        recipe=recipe)
            serializer = RecipeMiniSerializer(recipe)
            return Response(serializer.data,
                            status=status.HTTP_201_CREATED)
        if request.method == 'DELETE':
            ShoppingCart.objects.filter(
                user=request.user,
                recipe=recipe
            ).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        
    @action(detail=False, methods=['GET'],
            url_path='download_shopping_cart',
            permission_classes=[IsAuthenticated, ])
    def download_cart(self, request):
        """Отправка файла со списком покупок."""
        user = request.user
        response = HttpResponse(content_type="text/plain")
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
    permission_classes=(IsAuthenticated,),
    pagination_class=None)
    
    def favorite(self, request, pk=None):
        recipe = get_object_or_404(Recipe, id=pk)
        if request.method == 'POST':
            Favorite.objects.create(user=request.user,
                                        recipe=recipe)
            serializer = RecipeMiniSerializer(recipe)
            return Response(serializer.data,
                            status=status.HTTP_201_CREATED)
        if request.method == 'DELETE':
            Favorite.objects.filter(
                user=request.user,
                recipe=recipe
            ).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
    
 
        
    
    

