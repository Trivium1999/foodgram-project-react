import base64
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from django.db import IntegrityError
from django.core.files.base import ContentFile
from djoser.serializers import UserSerializer, UserCreateSerializer

from users.models import Subscribe, User
from recipes.models import (Recipes,
                            Tag,
                            Favorite,
                            ShoppingCart,
                            Ingredient,
                            IngredientsList)


class MyUserSerializer(UserSerializer):
    is_subscribed = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = [
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
        ]

    def get_is_subscribed(self, object):
        user = self.context.get('request').user
        if user.is_anonymous:
            return False
        return Subscribe.objects.filter(user=user, author=object.id).exists()


class ShortUserSerializer(MyUserSerializer):
    class Meta:
        model = User
        fields = [
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
        ]


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


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)
        return super().to_internal_value(data)


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = '__all__'


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit',)


class IngredientListSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='ingredients.id')
    name = serializers.ReadOnlyField(source='ingredients.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredients.measurement_unit'
    )
    amount = serializers.IntegerField()

    class Meta:
        model = IngredientsList
        fields = ['id', 'name', 'measurement_unit', 'amount']


class RecipeSerializer(serializers.ModelSerializer):
    author = MyUserSerializer(read_only=True)
    tags = TagSerializer(many=True)
    ingredients = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField(read_only=True)
    is_in_shopping_cart = serializers.SerializerMethodField(read_only=True)
    image = Base64ImageField()

    class Meta:
        model = Recipes
        fields = [
            'id',
            'tags',
            'author',
            'ingredients',
            'is_favorited',
            'is_in_shopping_cart',
            'name',
            'image',
            'text',
            'cooking_time'
        ]

    def get_ingredients(self, obj):
        ingredients = IngredientsList.objects.filter(recipe=obj)
        serializer = IngredientListSerializer(ingredients, many=True)

        return serializer.data

    def get_is_favorited(self, object):
        user = self.context.get('request').user
        if user.is_anonymous:
            return False
        return object.favorites.filter(user=user).exists()

    def get_is_in_shopping_cart(self, object):
        user = self.context.get('request').user
        if user.is_anonymous:
            return False
        return object.shopping_cart.filter(user=user).exists()


class AddingRecipeList(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())

    class Meta:
        model = IngredientsList
        fields = ['id', 'amount']


class RecipeInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipes
        fields = ('id', 'name', 'image', 'cooking_time')


class RecipeCreateSerializer(serializers.ModelSerializer):
    ingredients = AddingRecipeList(many=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True, required=True
    )
    image = Base64ImageField(max_length=None, use_url=True)

    class Meta:
        model = Recipes
        fields = [
            'ingredients',
            'tags',
            'image',
            'name',
            'text',
            'cooking_time'
        ]

    def validate_cooking_time(self, value):
        if value < 1 or value > 5000:
            raise serializers.ValidationError(
                'Пожалуйста, указывайте адекватное время готовки!'
            )
        return value

    def validate(self, attrs):
        ingredients = attrs.get('ingredients')
        if not ingredients:
            raise serializers.ValidationError(
                'Нужно выбрать хотя бы 1 ингредиент!'
            )
        unique_ings = []
        for ingredient in ingredients:
            ing = ingredient.get('id')
            if ing in unique_ings:
                raise serializers.ValidationError(
                    'Не стоит добавлять один и тот же ингредиент много раз!'
                )
            unique_ings.append(ing)
        if not unique_ings:
            raise serializers.ValidationError('Нужно добавить ингредиент')
        return attrs

    def validate_update_tags(self, data):
        unique_tags = self.initial_data.get('tag')
        if not unique_tags:
            raise ValidationError('Нужно выбрать хотя бы 1 тег!')
        data.update({'tags': unique_tags})
        return data

    def validate_tags(self, tags):
        unique_tags = []
        if not tags:
            raise serializers.ValidationError(
                'Нужно выбрать хотя бы 1 тег!'
            )
        for tag in tags:
            if tag in unique_tags:
                raise serializers.ValidationError(
                    'Не стоит добавлять один и тот же тег много раз!'
                )
            unique_tags.append(tag)
        return tags

    def create_ingredient(self, ingredients_list, recipe):
        for i in ingredients_list:
            ingredient = i['id']
            IngredientsList.objects.create(
                ingredients=ingredient, recipe=recipe, amount=i['amount']
            )

    # def create_tags_recipe(self, tags, recipe):
    #     for tag in tags:
    #         TagRecipe.objects.create(
    #             tag_id=tag.id,
    #             recipe=recipe
    #         )

    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        author = self.context.get('request').user
        try:
            recipe = Recipes.objects.create(author=author, **validated_data)
            recipe.tags.set(tags)
            self.create_ingredient(ingredients, recipe)
            return recipe
        except IntegrityError:
            raise serializers.ValidationError(
                'Такой рецепт уже существует!'
            )

    def update(self, instance, validated_data):
        # instance.tags.clear()
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        IngredientsList.objects.filter(recipe=instance).delete()
        instance.tags.set(tags)
        self.create_ingredient(ingredients, instance)
        # self.create_tags_recipe(tags, instance)
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        return RecipeSerializer(instance, context={
            'request': self.context.get('request')
        }).data


class FavoriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Favorite
        fields = ('user', 'recipe')

    def validate(self, data):
        user, recipe = data.get('user'), data.get('recipe')
        if self.Meta.model.objects.filter(user=user, recipe=recipe).exists():
            raise ValidationError(
                {'error': 'Этот рецепт уже добавлен'}
            )
        return data

    def to_representation(self, instance):
        context = {'request': self.context.get('request')}
        return RecipeInfoSerializer(instance.recipe, context=context).data


class ShoppingListSerializer(FavoriteSerializer):
    class Meta(FavoriteSerializer.Meta):
        model = ShoppingCart


class SubscribeSerializer(serializers.ModelSerializer):
    recipes = RecipeInfoSerializer(read_only=True, many=True)
    recipes_count = serializers.SerializerMethodField(read_only=True)
    is_subscribed = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
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

    def get_recipes(self, object):
        request = self.context.get('request')
        limit = request.GET.get('resipes_limit')
        queryset = Recipes.objects.filter(author=object.author)
        if limit:
            queryset = queryset[:int(limit)]
        return RecipeInfoSerializer(queryset, many=True).data

    def get_is_subscribed(self, object):
        user = self.context.get('request').user
        if user.is_anonymous:
            return False
        return Subscribe.objects.filter(user=user, author=object.id).exists()

    def get_recipes_count(self, obj):
        return obj.recipes.count()
