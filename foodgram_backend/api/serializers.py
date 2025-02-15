from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.shortcuts import get_object_or_404
from djoser.serializers import (SetPasswordSerializer, UserCreateSerializer,
                                UserSerializer)
from rest_framework import serializers
from rest_framework.serializers import SerializerMethodField

from foodgram_backend.constants import MAX_INGREDIENTS, MIN_INGREDIENTS
from recipes.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                            ShoppingCart, Tag)
from users.models import Follow

from .fields import Base64ImageField

User = get_user_model()


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

    class Meta:
        model = Recipe
        fields = (
            'id',
            'name',
            'image',
            'cooking_time'
        )


class FollowSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        model = User
        fields = (
            'id',
            'username',
            'first_name',
            'last_name',
            'email',
            'is_subscribed',
            'recipes_count',
            'recipes',
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
        limit = self.context.get('recipes_limit')
        if limit:
            queryset = queryset[: int(limit)]
        return RecipeMiniSerializer(queryset, many=True).data

    def get_recipes_count(self, obj):
        return obj.recipes.count()
    

class FollowCreateSerializer(serializers.Serializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    following = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all()
    )

    class Meta:
        model = Follow
        fields = ('user', 'following')

    def validate(self, attrs):
        user = self.context['request'].user
        following = attrs['following']
        if self.context['request'].method == 'POST':
            if user == following:
                raise serializers.ValidationError(
                    'Невозможно подписаться на самого себя'
                )
        return attrs

    def create(self, validated_data):
        return Follow.objects.create(**validated_data)



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
    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(),
        source='ingredient',
        error_messages={
            'does_not_exist': 'Ингредиента с таким значением id нет.'
        },
    )
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
                f'Сумма инградиентов не может быть меньше {MIN_INGREDIENTS}'

            )
        if amount > MAX_INGREDIENTS:
            raise serializers.ValidationError(
                f'Количество не должно быть больше {MAX_INGREDIENTS}'
            )
        return amount


class RecipeReadSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True)
    ingredients = RecipeIngredientSerializer(
        many=True,
        source='recipeingredient_set',
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
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return ShoppingCart.objects.filter(
                user=request.user,
                recipe=obj
            ).exists()
        return False


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

    # def validate_ingredients(self, ingredients):
    #     ingredients_set = set(ingredients)
    #     if not ingredients:
    #         raise serializers.ValidationError(
    #             'Поле ингредиентов не может быть пустым')
    #     if 
    #     return ingredients
    def validate_ingredients(self, value):
        if not value:
            raise serializers.ValidationError('Нужно добавить ингредиенты.')
        ingredients_data = set()
        for ingredient_item in value:
            ingredient_id = ingredient_item['ingredient']
            if ingredient_id in ingredients_data:
                raise serializers.ValidationError(
                    'Ингредиенты не должны повторяться.'
                )
            ingredients_data.add(ingredient_id)
        return value

    def tags_and_ingredient_obj(self, recipe, ingredients, tags):
        recipe.tags.set(tags)
        recipe_ingredients = [
            RecipeIngredient(
                recipe=recipe,
                ingredient=ingredient_data['ingredient'],
                amount=ingredient_data['amount']
            )
            for ingredient_data in ingredients
        ]
        RecipeIngredient.objects.bulk_create(recipe_ingredients)
        # for ing_item in ingredients:
        #     RecipeIngredient.objects.create(
        #         ingredient=ing_item['ingredient'],
        #         recipe=recipe,
        #         amount=ing_item['amount']
        #     )


    def create(self, validated_data):
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')
        recipe = Recipe.objects.create(**validated_data)
        self.tags_and_ingredient_obj(recipe, ingredients, tags)
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

        self.tags_and_ingredient_obj(instance, ingredients, tags)

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
            if Favorite.objects.filter(user=user, recipe=recipe).exists():
                raise serializers.ValidationError(
                    'Этот рецепт уже есть')
        return attrs
    