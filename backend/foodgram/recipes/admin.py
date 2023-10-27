from django.contrib import admin
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet

from .models import (Recipes,
                     Ingredient,
                     IngredientsList,
                     Tag,
                     Favorite,
                     ShoppingList)


class IngredientRecipeForm(BaseInlineFormSet):

    def clean(self):
        super(IngredientRecipeForm, self).clean()
        for form in self.forms:
            if not hasattr(form, 'cleaned_data'):
                continue
            data = form.cleaned_data
            if data.get('DELETE'):
                raise ValidationError(
                    'Нельзя удалять все ингредиенты из рецепта даже в админке!'
                )


class IngredientRecipeInLine(admin.TabularInline):
    model = IngredientsList
    min_num = 1
    formset = IngredientRecipeForm


class RecipeAdmin(admin.ModelAdmin):
    list_display = (
        'pk',
        'name',
        'text',
        'author',
        'cooking_time',
        'pub_date'
    )
    list_editable = ('author', 'name', 'text')
    search_fields = ('name', 'author')
    inlines = (IngredientRecipeInLine,)
    empty_value_display = '-пусто-'


class IngredientAdmin(admin.ModelAdmin):
    list_display = ('pk', 'name', 'measurement_unit')
    list_editable = ('name', 'measurement_unit')
    search_fields = ('name', 'measurement_unit')
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
