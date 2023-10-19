from rest_framework import serializers

from users.models import Subscribe, User
from recipes.models import (Recipes,
                            Tag,
                            Favorite,
                            ShoppingList,
                            Ingredient,
                            IngredientsList,
                            TagRecipe)


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name', 'color', 'slug']


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ['id', 'name', 'unit_measure']


class IngredientListSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='ingredients.id')
    name = serializers.ReadOnlyField(source='ingredients.name')
    unit_measure = serializers.ReadOnlyField(
        source='ingredients.unit_measure'
    )
    
    class Meta:
        model = IngredientsList
        fields = ['id', 'name', 'unit_measure', 'count']

