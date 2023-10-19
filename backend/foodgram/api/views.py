from django.shortcuts import render
from rest_framework import viewsets

from users.models import Subscribe, User
from recipes.models import (Recipes,
                            Tag,
                            Favorite,
                            ShoppingList,
                            Ingredient,
                            IngredientsList,
                            TagRecipe)


class TagViewSet(viewsets.ReadOnlyVeiwSet):
    queryset = Tag.objects.all()
    serialiser_class = TagSerializer
    # permission_classes =
    # pagination_class =


class RecipesViewSet(viewsets.ModelViewSet):
    queryset = Recipes.objects.all()
    # permission_classes = 
    # pagination_class = 


class Ingredient(viewsets.ReadOnlyViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    # permission_classes = 
    # pagination_class = 


# class SubscribeViewSet()


# class FavoriteViewSet(viewsets.)
