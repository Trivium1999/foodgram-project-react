import io
from django.shortcuts import HttpResponse, get_object_or_404
from django.db.models import Sum
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from rest_framework import viewsets, status, permissions, exceptions
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from .pagination import RecipePagination
from .filters import IngredientFilter, RecipeFilter
from users.models import Subscribe, User
from recipes.models import (Recipes,
                            Tag,
                            Favorite,
                            ShoppingCart,
                            Ingredient,
                            IngredientsList)
from .serializers import (TagSerializer,
                          IngredientSerializer,
                          RecipeSerializer,
                          RecipeCreateSerializer,
                          MyUserSerializer,
                          FavoriteSerializer,
                          SubscribeSerializer,
                          ShoppingListSerializer)
from .permissios import IsAdminOrAuthorOrReadOnly, IsAuthorOrReadOnly


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter
    # search_fields = ['^name', ]


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None


class RecipesViewSet(viewsets.ModelViewSet):
    queryset = Recipes.objects.all()
    serializer_class = RecipeSerializer
    permission_classes = [IsAuthorOrReadOnly,]
    pagination_class = RecipePagination
    filter_backends = (DjangoFilterBackend, )
    filterset_class = RecipeFilter

    def create(self, request):
        serializer = RecipeCreateSerializer(
            data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        recipe = serializer.save()
        return Response(
            RecipeSerializer(
                recipe, context={'request': request}
            ).data,  status=status.HTTP_201_CREATED
        )

    def get_serializer_class(self):
        """Можно ли валидацию update перенести сюда?"""
        if self.request.method == 'GET':
            return RecipeSerializer
        return RecipeCreateSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({'request': self.request})
        return context

    def create_recipe(class_object, user, recipe, serializer):
        already_existed, created = class_object.objects.get_or_create(
            user=user,
            recipe=recipe
        )
        if not created:
            return Response(
                {'errors': 'Нельзя создать запись'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            serializer(recipe).data,
            status=status.HTTP_201_CREATED
        )

    def delete_recipe(class_object, user, recipe):
        try:
            del_recipe = class_object.objects.get(user=user, recipe=recipe)
        except class_object.DoesNotExist:
            return Response(
                {'errors': 'Невозможно удалить'},
                status=status.HTTP_400_BAD_REQUEST
            )
        del_recipe.delete()
        return Response(
            {'detail': 'Удаление прошло успешно'},
            status=status.HTTP_204_NO_CONTENT
        )

    @action(
            methods=['POST', 'DELETE'],
            detail=True,
            url_path='favorite',
            url_name='favorite',
            permission_classes=(permissions.IsAuthenticated,),
        )
    def favorite(self, request, pk):
        user = self.request.user
        recipe = get_object_or_404(Recipes, pk=pk)
        object = FavoriteSerializer.Meta.model.objects.filter(
            user=user, recipe=recipe
        )
        if request.method == 'POST':
            serializer = FavoriteSerializer(
                data={'user': user.id, 'recipe': pk},
                context={'request': self.request}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        if self.request.method == 'DELETE':
            if object.exists():
                object.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            return Response({'error': 'Этого рецепта нет в списке'},
                            status=status.HTTP_400_BAD_REQUEST)

    def get_shopping_cart(self, request, pk):
        recipe = get_object_or_404(Recipes, pk=pk)
        if request.method == 'POST':
            serializer = ShoppingListSerializer(
                data={'user': request.user.id, 'recipe': recipe.id}
            )
            serializer.is_valid(raise_exeption=True)
            serializer.save()
            shopping_cart_serializer = RecipeSerializer(recipe)
            return Response(
                shopping_cart_serializer.data, status=status.HTTP_201_CREATED
            )
        shopping_cart_serializer = get_object_or_404(
            ShoppingCart, user=request.user, recipe=recipe
        )
        shopping_cart_serializer.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def create_shopping_cart(ingredients_list):
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = (
            "attachment; filename='shopping_cart.pdf'"
        )
        pdfmetrics.registerFont(
            TTFont('Arial', 'data/arial.ttf', 'UTF-8')
        )
        buffer = io.BytesIO()
        pdf_file = canvas.Canvas(buffer)
        pdf_file.setFont('Arial', 24)
        pdf_file.drawString(200, 800, 'Список покупок')
        pdf_file.setFont('Arial', 14)
        from_bottom = 750
        for number, ingredient in enumerate(ingredients_list, start=1):
            pdf_file.drawString(
                50,
                from_bottom,
                f"{number}. {ingredient['ingredient__name']}: "
                f"{ingredient['ingredient_value']} "
                f"{ingredient['ingredient__measurement_unit']}.",
            )
            from_bottom -= 20
        if from_bottom <= 50:
            from_bottom = 800
            pdf_file.showPage()
            pdf_file.setFont('Arial', 14)
        pdf_file.showPage()
        pdf_file.save()
        pdf = buffer.getvalue()
        buffer.close()
        response.write(pdf)
        return response

    @action(
        detail=False,
        methods=['GET'],
        url_path='download_shopping_cart',
        url_name='download_shopping_cart',
        permission_classes=(permissions.IsAuthenticated,)
    )
    def download_shopping_cart(self, request):
        ingredients_list = (
            IngredientsList.objects.filter(
                recipe__shopping_cart__user=request.user
            ).values(
                'ingredient__name',
                'ingredient__measurement_unit'
            ).order_by(
                'ingredient__name'
            ).annotate(ingredient_value=Sum('amount'))
        )
        return self.create_shopping_cart(ingredients_list)


class SubscribeViewSet(UserViewSet):
    queryset = User.objects.all()
    serializer_class = MyUserSerializer
    pagination_class = RecipePagination
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)

    @action(
        detail=True,
        methods=['POST', 'DELETE'],
        url_path='subscribe',
        url_name='subscribe',
        permission_classes=(permissions.IsAuthenticated,),
    )
    def subscribe(self, request, **kwargs):
        author = get_object_or_404(User, id=self.kwargs.get('id'))
        subscription, created = Subscribe.objects.get_or_create(
            user=request.user,
            author=author
        )
        if request.method == 'POST' and not created:
            raise exceptions.ValidationError(
                detail='Вы уже подписались на данного автора!'
            )
        if request.method == 'POST':
            serializer = SubscribeSerializer(
                author,
                context={'request': request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        subscription.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=['GET'],
        url_path='subscriptions',
        url_name='subscriptions',
        permission_classes=(permissions.IsAuthenticated,),
    )
    def subscriptions(self, request):
        queryset = User.objects.filter(authors__user=self.request.user)
        serializer = SubscribeSerializer(
            self.paginate_queryset(queryset),
            context={'request': request},
            many=True
        )
        return self.get_paginated_response(serializer.data)

    def get_permissions(self):
        if self.action == 'me':
            self.permission_classes = (IsAuthenticated,)
        return super().get_permissions()
