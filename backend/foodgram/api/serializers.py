from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.validators import UniqueTogetherValidator
from drf_extra_fields.fields import Base64ImageField
from djoser.serializers import UserSerializer, UserCreateSerializer

from users.models import Subscribe, User
from recipes.models import (Recipes,
                            Tag,
                            Favorite,
                            ShoppingList,
                            Ingredient,
                            IngredientsList)


class MyUserSerializer(UserSerializer):
    is_subscribed = serializers.SerializerMethodField(read_only=True)
    recipes = serializers.SerializerMethodField(read_only=True)
    recipes_count = serializers.SerializerMethodField(read_only=True)
    permission_classes = (IsAuthenticated, )

    class Meta:
        model = User
        fields = [
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'recipes',
            'recipes_count'
        ]

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        return Subscribe.objects.filter(
            user=request.user, author=obj
        ).exists()

    def get_recipes(self, current_user):
        request = self.context.get('request')
        return RecipeSerializer(
            current_user.recipes,
            many=True,
            context={'request': request}
        ).data

    def get_recipes_count(self, current_user):
        return current_user.recipes.count()


class CreateUserSerializer(UserCreateSerializer):
    class Meta:
        model = User
        fields = [
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'password'
        ]


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = '__all__'


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = '__all__'


class IngredientListSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='ingredients.id')
    name = serializers.ReadOnlyField(source='ingredients.name')
    unit_measure = serializers.ReadOnlyField(
        source='ingredients.unit_measure'
    )

    class Meta:
        model = IngredientsList
        fields = ['id', 'name', 'unit_measure', 'count']


class RecipeSerializer(serializers.ModelSerializer):
    author = MyUserSerializer(read_only=True)
    tags = TagSerializer(many=True)
    ingredients = serializers.SerializerMethodField()
    is_favorite = serializers.SerializerMethodField()
    is_shopping_list = serializers.SerializerMethodField()
    image = Base64ImageField()

    class Meta:
        model = Recipes
        fields = [
            'id',
            'author',
            'tags',
            'ingredients',
            'is_favorite',
            'is_shopping_list',
            'image',
            'title',
            'description',
            'time'
        ]

    def get_ingredients(self, obj):
        ingredients = IngredientsList.objects.filter(recipe=obj)
        return IngredientListSerializer(ingredients, many=True).data

    def get_is_favorite(self, obj):
        request = self.context.get('request')
        return Favorite.objects.filter(user=request.user, recipe=obj).exists()

    def get_is_shopping_list(self, obj):
        request = self.context.get('request')
        return ShoppingList.objects.filter(
            user=request.user, recipe=obj
        ).exists()


class AddingRecipeList(serializers.ModelSerializer):
    id = serializers.IntegerField()
    count = serializers.IntegerField()

    class Meta:
        model = IngredientsList
        fields = ['id', 'count']


class RecipeCreateSerializer(serializers.ModelSerializer):
    author = MyUserSerializer(read_only=True)
    ingredients = AddingRecipeList(many=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True
    )
    image = Base64ImageField()

    class Meta:
        model = Recipes
        fields = [
            'id',
            'author',
            'title',
            'description',
            'ingredients',
            'tags',
            'image',
            'time'
        ]

    def create_ingredient(self, ingredients_list, recipe):
        for i in ingredients_list:
            ingredient = Ingredient.objects.get(id=i['id'])
            IngredientsList.objects.create(
                ingredients=ingredient, recipe=recipe, count=i['count']
            )

    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        author = self.context.get('request').user
        recipe = Recipes.objects.create(author=author, **validated_data)
        self.create_ingredient(ingredients, recipe)
        recipe.tags.set(tags)
        return recipe

    def update(self, instance, validated_data):
        IngredientsList.objects.filter(recipe=instance).delete()
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        instance.tags.clear()
        instance.tags.set(tags)
        self.create_ingredient(ingredients, instance)
        instance.title = validated_data.pop('title')
        instance.description = validated_data.pop('description')
        if validated_data.get('image'):
            instance.image = validated_data.pop('image')
        instance.time = validated_data.pop('time')
        instance.save()
        return instance

    def to_representation(self, instance):
        return RecipeSerializer(instance, context={
            'request': self.context.get('request')
        }).data


class ShoppingListSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShoppingList
        fields = '__all__'
        validators = [
            UniqueTogetherValidator(
                queryset=ShoppingList.objects.all(),
                fields=('user', 'recipe'),
                message='Этот рецепт уже есть в списке покупок'
            )
        ]


class FavoriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Favorite
        fields = '__all__'
        validators = [
            UniqueTogetherValidator(
                queryset=Favorite.objects.all(),
                fields=('user', 'recipe'),
                message='Этот рецепт уже есть в избранном'
            )
        ]


class SubscribeSerializer(serializers.ModelSerializer):
    email = serializers.ReadOnlyField(source='author.email')
    id = serializers.ReadOnlyField(source='author.id')
    username = serializers.ReadOnlyField(source='author.username')
    first_name = serializers.ReadOnlyField(source='author.first_name')
    last_name = serializers.ReadOnlyField(source='author.last_name')
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.ReadOnlyField(source='author.recipes.count')
    is_subscribed = serializers.BooleanField(read_only=True)

    class Meta:
        model = Subscribe
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'recipes',
            'recipes_count',
        )

    def get_recipes(self, obj):
        request = self.context.get('request')
        recipes = obj.author.recipes.all()
        limit = request.query_params.get('recipes_limit')
        if limit:
            recipes = recipes[:int(limit)]
        serializer = RecipeSerializer(recipes, many=True)
        return serializer.data
