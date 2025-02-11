import base64

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.files.base import ContentFile
from django.db.models import F
from django.shortcuts import get_object_or_404
from djoser.serializers import (SetPasswordSerializer, UserCreateSerializer,
                                UserSerializer)
from recipes.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                            ShoppingCart, Tag)
from rest_framework import serializers
from rest_framework.serializers import SerializerMethodField

from foodgram_backend.constants import MAX_INGREDIENTS, MIN_INGREDIENTS

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
        fields = (
            'username', 
            'id', 
            'email', 
            'first_name', 
            'last_name', 
            'is_subscribed', 
            'avatar'
        )

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if (request and request.user.is_authenticated):
            return obj.following.exists()
        return False
    
    
    def validate(self, attrs):
        request = self.context.get('request')
        if request and 'avatar' not in attrs or attrs.get('avatar') is None:
            raise serializers.ValidationError('Поле avatar отсутствует')
        return super().validate(attrs)

    def update(self, instance, validated_data):
        avatar = validated_data.get('avatar', None)
        if avatar:
            if instance.avatar:
                instance.avatar.delete()
            instance.avatar = avatar
        return super().update(instance, validated_data)
    
    
class CustomCreateUserSerializer(UserCreateSerializer):
    class Meta:
        model = User
        fields = (
            'id', 
            'email', 
            'username', 
            'first_name', 
            'last_name', 
            'password'
        )
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
    # image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = (
            'id',
            'name',
            'image',
            'cooking_time'
        )
        # read_only_fields = (
        #     'id',
        #     'name',
        #     'image',
        #     'cooking_time'
        # )

class FollowSerializer(serializers.ModelSerializer):
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
            "recipes_count",
            "recipes",
            'avatar'
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
        limit = self.context.get("recipes_limit")
        if limit:
            queryset = queryset[: int(limit)]
        return RecipeMiniSerializer(queryset, many=True).data

    def get_recipes_count(self, obj):
        return obj.recipes.count()
    
class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = (
            'id', 
            'name', 
            'slug',
        )

class Ingredientserializer(serializers.ModelSerializer):

    class Meta:
        model = Ingredient
        fields = (
            'id', 
            'name', 
            'measurement_unit',
        )


class RecipeIngredientSerializer(serializers.ModelSerializer):
    """ Сериализатор для модели IngredientRecipe при GET запросах. """

    id = serializers.IntegerField(source='ingredient.id')
    name = serializers.CharField(source='ingredient.name')
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = RecipeIngredient
        fields = (
            'id',
            'name',
            'measurement_unit',
            'amount'
        )     

class AddIngredientToRecipeSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField()
    # id = serializers.PrimaryKeyRelatedField(
    #     queryset=Ingredient.objects.all(),
    #     source="ingredient.id",
    #     error_messages={'does_not_exist': 'Ингредиента с таким значением id нет.'},
    # )
    amount = serializers.IntegerField()


    class Meta:
        model = RecipeIngredient
        fields = (
            'id', 
            'amount'
        )

    def validate_amount(self, amount):
        if amount < MIN_INGREDIENTS:

            raise serializers.ValidationError(

                'Сумма инградиентов не может быть меньше 1'

            )
        if amount > MAX_INGREDIENTS:
            raise serializers.ValidationError(
                'Количество не должно быть больше 10'
            )
        return amount


class RecipeReadSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True)
    ingredients = RecipeIngredientSerializer(
        many=True,
        source="recipeingredient_set",
    )
    author = CustomUserSerializer()
    image = Base64ImageField()
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id', 
            'tags', 
            'ingredients', 
            'author',
            'name', 
            'image', 
            'text', 
            'cooking_time',
            'is_in_shopping_cart',
            'is_favorited'
        )
        read_only_fields = ('author',)

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
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
     
    
    # def get_ingredients(self, obj):
    #     recipe = obj
    #     ingredients = recipe.ingredients.values(
    #         'id',
    #         'name',
    #         'measurement_unit',
    #         amount=F('recipeingredient__amount'),)
    #     return ingredients

class RecipeCreateSerializer(serializers.ModelSerializer):
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True
    )
    ingredients = AddIngredientToRecipeSerializer(many=True, )
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = (
            'name', 
            'author', 
            'tags', 
            'ingredients', 
            'image', 
            'text',
            'cooking_time'
        )
        read_only_fields = ('author',)

    def to_representation(self, instance):
        serializer = RecipeReadSerializer(
            instance,
            context={
                'request': self.context.get('request')
            }
        )
        return serializer.data
    
    def validate_ingredients(self, value):
        if not value:
            raise serializers.ValidationError('Нужно добавить ингредиенты.')
        ingredient_ids = set()
        for ingredient_item in value:
            ingredient = get_object_or_404(Ingredient,
                                           id=ingredient_item['id'])
            if ingredient_item['id'] in ingredient_ids:
                raise serializers.ValidationError(
                    'Такой ингредиент уже есть.')
            ingredient_ids.add(ingredient)
        return value

    # def validate_ingredients(self, data):
    #     ingredients = self.initial_data.get('ingredients')
    #     if not ingredients:
    #         raise serializers.ValidationError({
    #             'ingredients': 'Нужен хоть один ингридиент для рецепта'})

    #     ingredient_list = []
    #     for ingredient_item in ingredients:
    #         ingredient = get_object_or_404(Ingredient,
    #                                        id=ingredient_item['id'])
    #         if ingredient in ingredient_list:
    #             raise serializers.ValidationError('Ингридиенты должны '
    #                                               'быть уникальными')
    #         ingredient_list.append(ingredient)

    #         data['ingredients'] = ingredients
    #     return data
    
    def validate_tags(self, value):
        if not value:
            raise serializers.ValidationError('Добавьте тэг.')
        tags = set()
        for tag in value:
            if tag in tags:
                raise serializers.ValidationError(
                    'Такой тэг уже есть.'
                )
            tags.add(tag)
        return value


    def tags_and_ingredient_obj(self, recipe, ingredients, tags):

        recipe.tags.set(tags) 
        for ingredient_item in ingredients:
            RecipeIngredient.objects.bulk_create(
                [RecipeIngredient(
                    ingredient_id=ingredient_item['id'],
                    recipe=recipe,
                    amount=ingredient_item['amount']
                )]
            )
    
   
    def create(self, validated_data):
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')
        recipe = Recipe.objects.create(**validated_data)
        self.tags_and_ingredient_obj(recipe, ingredients, tags,)
        return recipe
    
    def update(self, instance, validated_data):
        if 'tags' not in validated_data:
            raise serializers.ValidationError('Нужно добавить тэги')
        if 'ingredients' not in validated_data:
            raise serializers.ValidationError('Нужно добавить ингредиенты.')
        instance.ingredients.clear()
        tags = validated_data.pop('tags')
        instance.tags.set(tags)
        ingredients = validated_data.pop('ingredients',)
        # tags = validated_data.pop('tags')
        # instance.image = validated_data.get('image', instance.image)
        # instance.name = validated_data.get('name', instance.name)
        # instance.text = validated_data.get('text', instance.text)
        # instance.cooking_time = validated_data.get(
        #     'cooking_time', instance.cooking_time
        # )
        self.tags_and_ingredient_obj(instance, ingredients, tags,)
        # instance.save()   
        # return instance
        return super().update(instance, validated_data)

    

class ShoppingCartSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    recipe = serializers.PrimaryKeyRelatedField(queryset=Recipe.objects.all())

    class Meta:
        model = ShoppingCart
        fields = ('user', 'recipe')

    def validate(self, attrs):
        user = self.context['request'].user
        recipe = attrs['recipe']

        if self.context['request'].method == 'POST':
            if ShoppingCart.objects.filter(user=user, recipe=recipe).exists():
                raise serializers.ValidationError(
                    'Этот рецепт уже есть')
        elif self.context['request'].method == 'DELETE':
            if not ShoppingCart.objects.filter(user=user,
                                               recipe=recipe).exists():
                raise serializers.ValidationError(
                    'Рецепт не найден в корзине')
        return attrs

    def create(self, validated_data):
        return ShoppingCart.objects.create(**validated_data)

class FavoriteSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    recipe = serializers.PrimaryKeyRelatedField(queryset=Recipe.objects.all())

    class Meta:
        model = Favorite
        fields = ('user', 'recipe')

    def validate(self, attrs):
        user = self.context['request'].user
        recipe = attrs['recipe']
        if self.context['request'].method == 'POST':
            if ShoppingCart.objects.filter(user=user, recipe=recipe).exists():
                raise serializers.ValidationError(
                    'Этот рецепт уже есть'
                )
