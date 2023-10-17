from django.contrib import admin

from .models import (Recipes,
                     Ingredient,
                     Tag,
                     Favorite,
                     ShoppingList)


class RecipeAdmin(admin.ModelAdmin):
    list_display = (
        'pk',
        'title',
        'description',
        'author',
        'time',
        'pub_date'
    )
    list_editable = ('author', 'title', 'description')
    search_fields = ('title', 'author')
    empty_value_display = '-пусто-'


class IngredientAdmin(admin.ModelAdmin):
    list_display = ('pk', 'name', 'unit_measure')
    list_editable = ('name', 'unit_measure')
    search_fields = ('name', 'unit_measure')
    empty_value_display = '-пусто-'


class TagAdmin(admin.ModelAdmin):
    list_display = ('pk', 'name', 'color', 'slug')
    list_editable = ('name', 'color', 'slug')
    search_fields = ('name', 'slug')
    empty_value_display = '-пусто-'


class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('pk', 'user', 'recipe')
    list_editable = ('user', 'recipe')
    search_fields = ('user', 'recipe')
    empty_value_display = '-пусто-'


class ShoppingListAdmin(admin.ModelAdmin):
    list_display = ('pk', 'user', 'recipe')
    list_editable = ('user', 'recipe')
    search_fields = ('user', 'recipe')
    empty_value_display = '-пусто-'


admin.site.register(Recipes, RecipeAdmin)
admin.site.register(Ingredient, IngredientAdmin)
admin.site.register(Tag, TagAdmin)
admin.site.register(Favorite, FavoriteAdmin)
admin.site.register(ShoppingList, ShoppingListAdmin)
