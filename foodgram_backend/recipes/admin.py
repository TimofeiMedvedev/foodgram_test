from django.contrib import admin
from django.db import models

from recipes.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                            ShoppingCart, Tag)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'slug')
    search_fields = ('name',)
    list_filter = ('name',)


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'measurement_unit')
    list_filter = ('measurement_unit',)
    search_fields = ('name', 'measurement_unit',)


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 0


class RecipeTagInLine(admin.TabularInline):
    model = Recipe.tags.through
    # autocomplete_fields = ('tag',)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'author',
        'get_tags',
        'favorite_count',
        'cooking_time',
    )

    search_fields = (
        'author__username',
        'name',
        'tags__name',
    )

    readonly_fields = ('favorite_count',)
    list_filter = [
        'tags',
        'author',
    ]
    inlines = [
        RecipeIngredientInline,
        RecipeTagInLine,
    ]
  
    
    @admin.display(description='Теги в рецептах')
    def get_tags(self, obj):
        return ','.join([tag.name for tag in obj.tags.all()])
    
    # @admin.display(description='Ингредиенты в рецептах')
    # def get_ingredients(self, obj):
    #     return ','.join([ingredient.name for ingredient in obj.ingredients.all()])
    
    @admin.display(description='Количество добавлений в избранное')
    def favorite_count(self, obj):
        return Favorite.objects.filter(recipe=obj).count()


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe')
    search_fields = (
        'user__username',
        'recipe__name',
    )
    list_filter = ('user',)


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe')
    search_fields = (
        'user__username',
        'recipe__name',
    )
    list_filter = ('user',)
