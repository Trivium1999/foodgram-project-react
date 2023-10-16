from django.contrib import admin

from .models import (Recipes,
                     Ingredient,
                     IngredientsList,
                     Tag,
                     Favorite,
                     ShoppingList)


admin.site.register(Recipes)
admin.site.register(Ingredient)
admin.site.register(IngredientsList)
admin.site.register(Tag)
admin.site.register(Favorite)
admin.site.register(ShoppingList)


class RecipeAdmin(admin.ModelAdmin):
    list_display = ('pk', 'title', 'description', 'author', 'ingredients', 'tegs', 'time', 'pub_date')
    list_editable = ('author',)
    search_fields = ('text',)
    list_filter = ('pub_date',)
    empty_value_display = '-пусто-'
