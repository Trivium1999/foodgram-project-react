from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, RegexValidator

User = get_user_model()


class Recipes(models.Model):
    title = models.CharField('Название рецепта', max_length=250)
    description = models.TextField('Описание', max_length=500)
    author = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='recipes',
        verbose_name='Автор'
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        related_name='recipes',
        through='recipes.IngredientList',
        verbose_name='Ингредиенты'
    )
    image = models.ImageField(upload_to='image/', null=True, blank=True)
    tags = models.ManyToManyField(Tag, related_name='recipes')
    time = models.PositiveSmallIntegerField(validators=[MinValueValidator(1),])
    pub_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Рецепт'
        ordering = ('-pub_date')


class Ingredient(models.Model):
    name = models.CharField('Название', max_length=60)
    unit_measure = models.CharField(max_length=20)

    class Meta:
        ordering = ('name',)
        verbose_name = 'Ингредиент'

    def __str__(self):
        return f'{self.name}, {self.unit_measure}'


class IngredientsList(models.Model):
    recipe = models.ForeignKey(
        Recipes,
        on_delete=models.CASCADE,
        related_name='ingredient'
    )
    ingredients = models.ForeignKey(
        Ingredient,
        related_name='recipe',
        on_delete=models.CASCADE
    )
    count = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1),
        ]
    )

    class Meta:
        ordering = ('recipe__name',)

    def __str__(self):
        return f'{self.recipe}, {self.ingredients}, {self.count}'


class Tag(models.Model):
    name = models.CharField(
        max_length=50,
        unique=True
    )
    color = models.CharField(
        max_length=7,
        validators=[
            RegexValidator(regex=r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$',
                           message='Цвет должен быть в формате HEX')
        ],
    )
    slug = models.SlugField(unique=True)

    class Meta:
        unique_together = ('name', 'slug')

    def __str__(self):
        return f'{self.name}, {self.slug}'


class TagRecipe(models.Model):
    tag = models.ForeignKey(
        Tag,
        on_delete=models.CASCADE
    )
    recipe = models.ForeignKey(
        Recipes,
        on_delete=models.CASCADE
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['tag', 'recipe'],
                                    name='unique_tag'),
        ]

    def __str__(self):
        return f'{self.tag} {self.recipe}'


class Favorite(models.Model):
    user = models.ForeignKey(
        User,
        related_name='favorites',
        on_delete=models.CASCADE
    )
    recipe = models.ForeignKey(
        Recipes,
        related_name='favorites',
        on_delete=models.CASCADE
    )

    def __str__(self):
        return f'{self.user} / {self.recipe}'


class ShoppingList(models.Model):
    user = models.ForeignKey(
        User,
        related_name='shopping_list',
        on_delete=models.CASCADE
    )
    recipe = models.ForeignKey(
        Recipes,
        related_name='shopping_list',
        on_delete=models.CASCADE
    )

    def __str__(self):
        return f'{self.user} / {self.recipe}'
