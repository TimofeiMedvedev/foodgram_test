from django.contrib.auth import get_user_model
from rest_framework import filters, viewsets,  status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from recipes.models import Tag, Recipe, Ingredient


from .serializers import (CustomCreateUserSerializer, CustomUserSerializer, TagSerializer, RecipeReadSerializer, Ingredientserializer, RecipeCreateSerializer)


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
    permission_classes = (AllowAny, )
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

