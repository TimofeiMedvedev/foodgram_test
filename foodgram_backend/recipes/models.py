import shortuuid
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models

from foodgram_backend.constants import (MAX_LENGTH_ING, MAX_LENGTH_NAME,
                                        MAX_LENGTH_RECIPE_NAME,
                                        MAX_LENGTH_SLUG, MIN_COOKING_TIME,
                                        MAX_COOKING_TIME, MIN_AMOUNT,
                                        MAX_AMOUNT)

User = get_user_model()

class Tag(models.Model):
    name = models.CharField(
        max_length=MAX_LENGTH_NAME, 
        unique=True,
        verbose_name='Название тэга',
    )
    slug = models.SlugField(
        max_length=MAX_LENGTH_SLUG, 
        unique=True,
        verbose_name='Слаг тэга'
    )

    class Meta:
        verbose_name = 'Тэг'
        verbose_name_plural = 'Тэги'
        ordering = ('name',)

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    name = models.CharField(
        max_length=MAX_LENGTH_ING,
        unique=True,
        verbose_name='Название ингредиента')
    measurement_unit = models.CharField(
        max_length=MAX_LENGTH_NAME,
        verbose_name='Единица измерения ингредиента')

    class Meta:
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'
        ordering = ('name',)
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'measurement_unit'], name='unique ingredient'
            )
        ]

    def __str__(self):
        return self.measurement_unit


class Recipe(models.Model):
    tags = models.ManyToManyField(
        Tag,
        related_name='recipes',
        verbose_name='Тэги',
        through='RecipeTag'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recipes',
        verbose_name='Автор',
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        related_name='recipes',
        verbose_name='Ингредиенты',
        through='RecipeIngredient',
    )
    name = models.CharField(
        max_length=MAX_LENGTH_RECIPE_NAME,
        verbose_name='Название рецепта',
    )
    image = models.ImageField(
        upload_to='recipes/',
        verbose_name='Изображение'
    )
    text = models.TextField(
        verbose_name='Описание рецепта'
    )
    cooking_time = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(MIN_COOKING_TIME),
            MaxValueValidator(MAX_COOKING_TIME)
        ],
        verbose_name='Время приготовления в минутах',
        help_text='мин'
    )
    short_link = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        unique=True,
        verbose_name='Короткая ссылка',
    )
    pub_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата публикации',
    )
    
    class Meta:
        verbose_name = 'рецепт'
        verbose_name_plural = 'Рецепты'
        ordering = ('-pub_date',)


    def __str__(self):
        return self.name


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт'
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        verbose_name='Ингредиент'
    )
    amount = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(MIN_AMOUNT),
            MaxValueValidator(MAX_AMOUNT)
        ],
        verbose_name='Количество'
    )

    class Meta:
        verbose_name = 'Ингредиент в рецепте'
        verbose_name_plural = 'Ингредиенты в рецептах'

    def __str__(self):
        return (
            f'{self.ingredient.name} - '
            f'{self.amount} - '
            f'{self.ingredient.measurement_unit} - '
        )
    
class RecipeTag(models.Model):

    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт'
    )

    tag = models.ForeignKey(
        Tag,
        on_delete=models.CASCADE,
        verbose_name='Тэг'
    )

    class Meta:
        verbose_name = 'Тэг в рецепте'
        verbose_name_plural = 'Тэги в рецептах'


class ShoppingCart(models.Model):

    user = models.ForeignKey(
        User,
        related_name='buyer',
        on_delete=models.CASCADE,
        verbose_name='Пользователь',
    )
    recipe = models.ForeignKey(
        Recipe,
        related_name='recipe_cart',
        on_delete=models.CASCADE,
        verbose_name='Рецепт',
    )

    class Meta:
        verbose_name = 'Список покупок'
        verbose_name_plural = 'Списки покупок'
        ordering = ('recipe',)
        constraints = [
            models.UniqueConstraint(
                name='unique_shop_user',
                fields=['user', 'recipe']
            )
        ]


class Favorite(models.Model):

    user = models.ForeignKey(
        User,
        related_name='favorites',
        on_delete=models.CASCADE,
        verbose_name='Пользователь',
    )
    recipe = models.ForeignKey(
        Recipe,
        related_name='favorites',
        on_delete=models.CASCADE,
        verbose_name='Рецепт',
    )

    class Meta:
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранное'
        ordering = ('recipe',)
        constraints = [
            models.UniqueConstraint(
                name='unique_favorite_user',
                fields=['user', 'recipe']
            )
        ]
