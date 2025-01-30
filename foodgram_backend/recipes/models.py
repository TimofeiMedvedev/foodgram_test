from django.contrib.auth import get_user_model
from django.db import models
from foodgram_backend.constants import MAX_LENGTH_NAME, MAX_LENGTH_SLUG, MAX_LENGTH_ING, MAX_LENGTH_RECIPE_NAME
from django.core.validators import MinValueValidator
import shortuuid

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
        verbose_name = "Тэг"
        verbose_name_plural = "Тэги"
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
        verbose_name_plural = "Ингредиенты"

    def __str__(self):
        return self.name
    

class Recipe(models.Model):
    tags = models.ManyToManyField(
        Tag,
        related_name="recipes",
        verbose_name="Тэги",
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="recipes",
        verbose_name="Автор",
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
        verbose_name='Описание рецепта',
    )
    cooking_time = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        verbose_name='Время приготовления в минутах',
    )
    short_link = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        unique=True,
        verbose_name="Короткая ссылка",
    )
    def get_or_create_short_link(self):
        if not self.short_link:
            self.short_link = shortuuid.uuid()[:7]
            self.save(update_fields=["short_link"])
        return self.short_link
    
    class Meta:
        verbose_name = "рецепт"
        verbose_name_plural = "Рецепты"

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
    amount = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name="Количество"
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


class Favorite(models.Model):

    user = models.ForeignKey(
        User,
        related_name='favorite_user',
        on_delete=models.CASCADE,
        verbose_name='Пользователь',
    )
    recipe = models.ForeignKey(
        Recipe,
        related_name='favorite_recipe',
        on_delete=models.CASCADE,
        verbose_name='Рецепт',
    )

    class Meta:
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранное'