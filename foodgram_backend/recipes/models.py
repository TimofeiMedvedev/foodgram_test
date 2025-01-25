from django.contrib.auth import get_user_model
from django.db import models
from foodgram_backend.constants import MAX_LENGTH_NAME, MAX_LENGTH_SLUG, MAX_LENGTH_ING
from django.core.validators import MinValueValidator

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
        verbose_name = 'Инградиент'
        verbose_name_plural = "Инградиенты"

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
        max_length=MAX_LENGTH_NAME,
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
        constraints = [
            models.UniqueConstraint(name='unique_recipe_ingredient',
                                    fields=["recipe", "ingredient"])
        ]

    def __str__(self):
        return (
            f'{self.ingredient.name} - '
            f'{self.amount} - '
            f'{self.ingredient.measurement_unit} - '
        )