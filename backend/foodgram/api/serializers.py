import base64
from rest_framework import serializers, validators
from rest_framework.permissions import IsAuthenticated
from rest_framework.validators import UniqueTogetherValidator
from django.db import IntegrityError
from django.core.files.base import ContentFile
from django.core.validators import MinValueValidator
from django.shortcuts import get_object_or_404
from djoser.serializers import UserSerializer, UserCreateSerializer

from users.models import Subscribe, User
from recipes.models import (Recipes,
                            Tag,
                            Favorite,
                            ShoppingList,
                            Ingredient,
                            IngredientsList,
                            TagRecipe)


class MyUserSerializer(UserSerializer):
    is_subscribed = serializers.SerializerMethodField(read_only=True)
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
        ]

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Subscribe.objects.filter(
                user=request.user,
                author=obj
            ).exists()
        return False


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
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_list = serializers.SerializerMethodField()
    image = Base64ImageField()

    class Meta:
        model = Recipes
        fields = [
            'id',
            'tags',
            'author',
            'ingredients',
            'is_favorited',
            'is_in_shopping_list',
            'name',
            'image',
            'text',
            'cooking_time'
        ]

    def get_ingredients(self, obj):
        ingredients = IngredientsList.objects.filter(recipe=obj)
        serializer = IngredientListSerializer(ingredients, many=True)

        return serializer.data

    def get_is_favorited(self, obj):
        user = self.context.get('request').user
        if user.is_anonymous:
            return False
        return Favorite.objects.filter(user=user, recipe=obj).exists()

    def get_is_in_shopping_list(self, obj):
        user = self.context.get('request').user
        if user.is_anonymous:
            return False
        return ShoppingList.objects.filter(user=user, recipe=obj).exists()


class AddingRecipeList(serializers.ModelSerializer):
    """несколько тестов валятся из за этого. если убираю write_only, то выдает ошибку.
    а если оставляю, то неправильно отображается. Может создать отдельный сериализатор
    для отображения параметров рецепта"""
    id = serializers.IntegerField()
    amount = serializers.IntegerField(write_only=True)
        # validators=(
        #     MinValueValidator(
        #         1,
        #         message='Количество ингредиента должно быть 1 или более.'
        #     ),
        # )

    class Meta:
        model = IngredientsList
        fields = ['id', 'amount']

    def validate_amount(self, value):
        if value < 1 or value > 5000:
            raise serializers.ValidationError(
                'Нужно указать кол-во от 1 до 5000!'
            )
        return value


class RecipeCreateSerializer(serializers.ModelSerializer):
    # author = MyUserSerializer(read_only=True)
    ingredients = AddingRecipeList(many=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True, required=True
    )
    image = Base64ImageField(max_length=None, use_url=True)
    # cooking_time = serializers.IntegerField()

    class Meta:
        model = Recipes
        fields = [
            'ingredients',
            'tags',
            # 'id',
            'image',
            'name',
            # 'author',
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
            ing = get_object_or_404(Ingredient, id=ingredient.get('id'))
            if ing in unique_ings:
                raise serializers.ValidationError(
                    'Не стоит добавлять один и тот же ингредиент много раз!'
                )
            unique_ings.append(ing)
            """Не проходит проверка, есть ли ингредиент при update"""
        if not unique_ings:
            raise serializers.ValidationError('Нужно добавить ингредиент')
        return attrs

    def validate_tags(self, tags):
        unique_tags = []
        if not tags:
            raise serializers.ValidationError(
                'Нужно выбрать хотя бы 1 тег!'
            )
        for tag in tags:
            if tag in unique_tags:
                raise serializers.ValidationError(
                    'Не стоит добавлять один и тот же ингредиент много раз!'
                )
            unique_tags.append(tag)
        return tags

    def create_ingredient(self, ingredients_list, recipe):
        for i in ingredients_list:
            ingredient = Ingredient.objects.get(id=i['id'])
            IngredientsList.objects.create(
                ingredients=ingredient, recipe=recipe, amount=i['amount']
            )

    def create_tags_recipe(self, tags, recipe):
        for tag in tags:
            TagRecipe.objects.create(
                tag_id=tag.id,
                recipe=recipe
            )

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
        instance.tags.clear()
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        IngredientsList.objects.filter(recipe=instance).delete()
        self.create_ingredient(ingredients, instance)
        self.create_tags_recipe(tags, instance)
        super().update(instance, validated_data)
        return instance
    # def update(self, instance, validated_data):
    #     IngredientsList.objects.filter(recipe=instance).delete()
    #     ingredients = validated_data.pop('ingredients')
    #     tags = validated_data.pop('tags')
    #     instance.tags.clear()
    #     instance.tags.set(tags)
    #     self.create_ingredient(ingredients, instance)
    #     instance.name = validated_data.pop('name')
    #     instance.text = validated_data.pop('text')
    #     if validated_data.get('image'):
    #         instance.image = validated_data.pop('image')
    #     instance.cooking_time = validated_data.pop('cooking_time')
    #     instance.save()
    #     return instance

    # def to_representation(self, instance):
    #     return RecipeSerializer(instance, context={
    #         'request': self.context.get('request')
    #     }).data


class ShoppingListSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShoppingList
        fields = '__all__'
        validators = [
            validators.UniqueTogetherValidator(
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
            validators.UniqueTogetherValidator(
                queryset=Favorite.objects.all(),
                fields=('user', 'recipe'),
                message='Этот рецепт уже есть в избранном'
            )
        ]


class SubscribeSerializer(serializers.ModelSerializer):
    # email = serializers.ReadOnlyField(source='author.email')
    # id = serializers.ReadOnlyField(source='author.id')
    # username = serializers.ReadOnlyField(source='author.username')
    # first_name = serializers.ReadOnlyField(source='author.first_name')
    # last_name = serializers.ReadOnlyField(source='author.last_name')
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()
    is_subscribed = serializers.SerializerMethodField()

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

    def get_recipes(self, obj):
        recipes_limit = self.context.get('request').query_params.get(
            'recipes_limit'
        )
        recipes = obj.recipes.all()
        if recipes_limit:
            recipes = recipes[:int(recipes_limit)]
            return RecipeSerializer(recipes, many=True).data

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        return Subscribe.objects.filter(
            user=request.user.is_authenticated,
            author=obj
        ).exists()

    def get_recipes_count(self, obj):
        return obj.recipes.count()
