from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.serializers import SerializerMethodField
from djoser.serializers import UserCreateSerializer, UserSerializer, SetPasswordSerializer
from django.core.files.base import ContentFile
import base64
from django.contrib.auth.password_validation import validate_password
from recipes.models import Tag, RecipeIngredient, Recipe, Ingredient, ShoppingCart, Favorite
from foodgram_backend.constants import MIN_INGREDIENTS, MIN_COOKING_TIME
from django.db.models import F
from rest_framework.validators import UniqueTogetherValidator



User = get_user_model()


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]

            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)

        return super().to_internal_value(data)

class CustomUserSerializer(UserSerializer):

    is_subscribed = SerializerMethodField()
    avatar = Base64ImageField(required=False, allow_null=True)


    class Meta:
        model = User
        fields = ('username', 'id', 'email', 'first_name', 'last_name', 'is_subscribed', 'avatar')

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if (request and request.user.is_authenticated):
            return obj.following.exists()
        return False
    
    
    def update(self, instance, validated_data):
        instance.avatar = validated_data.get('avatar', instance.avatar)
        instance.save()
        return instance
    
    
class CustomCreateUserSerializer(UserCreateSerializer):
    class Meta:
        model = User
        fields = ('email', 'username', 'first_name', 'last_name', 'password')
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        user = User(
            email=validated_data['email'],
            username=validated_data['username'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
        )
        user.set_password(validated_data['password'])
        user.save()
        return user

class CustomChangePasswordSerializer(SetPasswordSerializer):

    current_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)

    def validate_new_password(self, value):
        validate_password(value)
        return value
    
    
class RecipeMiniSerializer(serializers.ModelSerializer):
    """Сериализатор для отображения краткой информации о рецепте."""
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')

class FollowSerializer(serializers.ModelSerializer):
    """Сеарилизатор для подписок."""
    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        model = User
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "is_subscribed",
            "avatar",
            "recipes_count",
            "recipes",
        )
        read_only_fields = (
            'username',
            'first_name', 
            'last_name',
            'email'
        )
        
    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if (request and request.user.is_authenticated):
            return obj.following.exists()
        return False

    def get_recipes(self, obj):
        queryset = obj.recipes.all()
        limit = self.context.get('recipes_limit')
        if limit:
            queryset = queryset[: int(limit)]
        return RecipeMiniSerializer(queryset, many=True).data

    def get_recipes_count(self, obj):
        return obj.recipes.count()
    
class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug',)

class Ingredientserializer(serializers.ModelSerializer):
    """Сеарилизатор для ингредиентов."""
    class Meta:
        model = Ingredient
        fields = ('name', 'measurement_unit',)
        

class AddIngredientToRecipeSerializer(serializers.ModelSerializer):
    """Сеарилизатор для добавления ингредиента в рецепт."""
    id = serializers.IntegerField()
    amount = serializers.IntegerField()

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'amount')

    def validate_amount(self, amount):
        if amount < MIN_INGREDIENTS:
            raise serializers.ValidationError(
                'Сумма инградиентов не может быть меньше 1'
            )
        return amount


class RecipeReadSerializer(serializers.ModelSerializer):
    """Сеарилизатор для показа рецепта."""
    tags = TagSerializer(many=True)
    ingredients = SerializerMethodField()
    author = CustomUserSerializer()
    image = Base64ImageField()
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if (request is not None and request.user.is_authenticated):
            return Favorite.objects.filter(
                user=request.user,
                recipe=obj
            ).exists()
        return False

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return ShoppingCart.objects.filter(
                user=request.user,
                recipe=obj
            ).exists()
        return False

     
    class Meta:
        model = Recipe
        fields = ('id', 'tags', 'ingredients', 'author',
                  'name', 'image', 'text', 'cooking_time',
                  'is_in_shopping_cart', 'is_favorited')
        read_only_fields = ('author',)
        
    def get_ingredients(self, obj):
        recipe = obj
        ingredients = recipe.ingredients.values(
            'id',
            'name',
            'measurement_unit',
            amount=F('recipeingredient__amount'),)
        return ingredients

class RecipeCreateSerializer(serializers.ModelSerializer):
    """Сеарилизатор для создания рецепта."""
    tags = serializers.SlugRelatedField(
        slug_field='slug',
        queryset=Tag.objects.all(),
    )
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True
    )
    ingredients = AddIngredientToRecipeSerializer(many=True)
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ('name', 'author', 'tags', 'ingredients', 'image', 'text', 'cooking_time')
        read_only_fields = ('author',)

    def to_representation(self, instance):
        serializer = RecipeReadSerializer(
            instance,
            context={
                'request': self.context.get('request')
            }
        )
        return serializer.data
    
    def validate(self, data):
        ingredients = data['ingredients']
        ing_list = []
        for ingredient in ingredients:
            if ingredient['id'] in ing_list:
                raise serializers.ValidationError(
                    'Такой инградиент уже есть'
                )
            ing_list.append(ingredient['id'])
        return data

    def tags_and_ingredient_obj(self, recipe, ingredients, tags,):
        recipe.tags.set(tags)
        for ingredient in ingredients:
            amount = ingredient['amount']
            current_ingredient = Ingredient.objects.get(id=ingredient['id'])
            RecipeIngredient.objects.create(
                recipe=recipe,
                ingredient=current_ingredient,
                amount=amount,
            )
    def create(self, validated_data):
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')
        recipe = Recipe.objects.create(**validated_data)
        self.tags_and_ingredient_obj(recipe, ingredients, tags,)
        return recipe
    
    def update(self, instance, validated_data):
        instance.ingredients.clear()
        instance.tags.clear()
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        instance.image = validated_data.get('image', instance.image)
        instance.name = validated_data.get('name', instance.name)
        instance.text = validated_data.get('text', instance.text)
        instance.cooking_time = validated_data.get(
            'cooking_time', instance.cooking_time
        )
        self.tags_and_ingredient_obj(instance, ingredients, tags,)
        instance.save()   
        return instance


class ShoppingCartSerializer(serializers.ModelSerializer):
    """Сериализатор для корзины."""
    user = UserSerializer()
    recipe = RecipeReadSerializer(many=True)

    class Meta:
        model = ShoppingCart
        fields = ('user', 'recipe')
        validators = [
            UniqueTogetherValidator(
                queryset=ShoppingCart.objects.all(),
                fields=('user', 'recipe'),
                message='Данный рецепт уже есть в корзине!'
            )
        ]


    def to_representation(self, instance):
        request = self.context.get('request')
        return RecipeMiniSerializer(
            instance.recipe,
            context={'request': request}
        ).data
    

class FavoriteSerializer(serializers.ModelSerializer):
    """Сериализатор для избранного."""
    user = UserSerializer()
    recipe = RecipeReadSerializer(many=True)

    class Meta:
        model = Favorite
        fields = ('user', 'recipe')
        validators = [
            UniqueTogetherValidator(
                queryset=Favorite.objects.all(),
                fields=('user', 'recipe'),
                message='Данный рецепт уже есть в избранном!'
            )
        ]

    def to_representation(self, instance):
        request = self.context.get('request')
        return RecipeMiniSerializer(
            instance.recipe,
            context={'request': request}
        ).data