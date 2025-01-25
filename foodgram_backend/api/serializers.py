from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.serializers import SerializerMethodField
from djoser.serializers import UserCreateSerializer, UserSerializer, SetPasswordSerializer
from django.core.files.base import ContentFile
import base64
from django.contrib.auth.password_validation import validate_password
from recipes.models import Tag, RecipeIngredient, Recipe, Ingredient
from foodgram_backend.constants import MIN_INGREDIENTS, MIN_COOKING_TIME
from django.db.models import F



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
    

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug',)

class Ingredientserializer(serializers.ModelSerializer):
    """Сеарилизатор для ингредиентов."""
    class Meta:
        model = Ingredient
        fields = ('name', 'measurement_unit','amount')

class IngredientInRecipeSerializer(serializers.ModelSerializer):
    """Сеарилизатор для ингредиентов в рецептах."""
    id = serializers.ReadOnlyField(
        source='ingredient.id'
    )
    name = serializers.ReadOnlyField(
        source='ingredient.name'
    )
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'amount', 'name',
                  'measurement_unit')

        

class AddIngredientToRecipeSerializer(serializers.ModelSerializer):
    """Сеарилизатор для добавления ингредиента в рецепт."""
    id = serializers.IntegerField()
    amount = serializers.IntegerField()

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'amount')

    # def to_representation(self, value):

    #     return Ingredientserializer(value).data

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
    # is_favorited = serializers.SerializerMethodField()
    # is_in_shopping_cart = serializers.SerializerMethodField()

    # def get_is_favorited(self, obj):
    #     request = self.context.get('request')
    #     if (request is not None and request.user.is_authenticated):
    #         return obj.recipe_favorite.exists()
    #     return False

    # def get_is_in_shopping_cart(self, obj):
    #     request = self.context.get('request')
    #     if (request is not None and request.user.is_authenticated):
    #         return obj.recipe_shop_cart.exists()
    #     return False

     
    class Meta:
        model = Recipe
        fields = ('id', 'tags', 'ingredients', 'author',
                  'name', 'image', 'text', 'cooking_time')
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