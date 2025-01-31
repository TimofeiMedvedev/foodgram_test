from django.contrib import admin
from django.db import models

from recipes.models import Tag, Ingredient, Recipe, RecipeIngredient, ShoppingCart, Favorite

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'slug')
    search_fields = ('name',)
    list_filter = ('name',)

@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'measurement_unit')
    search_fields = ('name',)
  

class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 0

@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'author',
    )
    search_fields = (
        "author__username",
        "name",
    )
    readonly_fields = ('favorite_count',)
    list_filter = [
        "tags",
    ]
    inlines = [RecipeIngredientInline]

    def tags(self, row):
        return ','.join([x.name for x in row.tags.all()])
    
    def favorite_count(self, obj):
        return Favorite.objects.filter(recipe=obj).count()
    favorite_count.short_description = 'Кол-во добавлений в избранное'

@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe')
    search_fields = ('user',)
    list_filter = ('user',)


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe')
    search_fields = ('user',)
    list_filter = ('user',)
