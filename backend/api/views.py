from django.shortcuts import HttpResponse, get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from django.db.models import Sum
# from django.http import FileResponse
from recipes.models import Ingredient, IngredientsList, Recipes, Tag
# from reportlab.pdfbase import pdfmetrics, ttfonts
# from reportlab.pdfgen import canvas
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import (IsAuthenticated)
from rest_framework.response import Response

from users.models import Subscribe, User

from .filters import IngredientFilter, RecipeFilter
from .pagination import RecipePagination
from .permissios import IsAuthorOrReadOnly
from .serializers import (FavoriteSerializer, IngredientSerializer,
                          MyUserSerializer, RecipeCreateSerializer,
                          RecipeSerializer, ShoppingListSerializer,
                          SubscribeSerializer, TagSerializer)


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None


class RecipesViewSet(viewsets.ModelViewSet):
    queryset = Recipes.objects.all()
    serializer_class = RecipeSerializer
    permission_classes = (IsAuthorOrReadOnly, )
    pagination_class = RecipePagination
    filter_backends = (DjangoFilterBackend, )
    filterset_class = RecipeFilter

    def create(self, request):
        if request.user.is_anonymous:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        serializer = RecipeCreateSerializer(
            data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        recipe = serializer.save()
        return Response(
            RecipeSerializer(
                recipe, context={'request': request}
            ).data, status=status.HTTP_201_CREATED
        )

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return RecipeSerializer
        return RecipeCreateSerializer

    def creating_and_deleting(self, pk, ser_class):
        user = self.request.user
        recipe = get_object_or_404(Recipes, pk=pk)
        object = ser_class.Meta.model.objects.filter(
            user=user, recipe=recipe
        )
        if self.request.method == 'POST':
            serializer = ser_class(
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

    @action(
        methods=['POST', 'DELETE'],
        detail=True,
        permission_classes=(permissions.IsAuthenticated,),
    )
    def favorite(self, request, pk):
        return self.creating_and_deleting(pk, FavoriteSerializer)

    @action(methods=['POST', 'DELETE'], detail=True,
            permission_classes=(permissions.IsAuthenticatedOrReadOnly,))
    def shopping_cart(self, request, pk):
        if request.user.is_anonymous:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        return self.creating_and_deleting(pk, ShoppingListSerializer)

    @action(
        methods=['GET'],
        detail=False,
        permission_classes=(IsAuthenticated,)
    )
    def download_shopping_cart(self, request):
        if request.user.is_anonymous:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        ingredients = (IngredientsList.objects.filter(
            recipe__shopping_cart__user=request.user
        ).order_by('ingredients__name').values(
            'ingredients__name', 'ingredients__measurement_unit'
        ).annotate(amount=Sum('amount')))
        ingr_list = []
        for ingredient in ingredients:
            ingr_list += (
                f'\n{ingredient.get("ingredients__name").title()}:  '
                f'{ingredient.get("amount") }'
                f'({ingredient.get("ingredients__measurement_unit")}) '
            )
        response = HttpResponse(ingr_list, content_type='text/plain')
        response['Content-Disposition'] = (
            'attachment; filename=Shopping_List.txt'
        )
        return response
        # response = HttpResponse(content_type='application/pdf')
        # response['Content-Disposition'] = (
        #     "attachment; filename='shopping_cart.pdf'"
        # )
        # pdfmetrics.registerFont(ttfonts.TTFont('Arial', 'data/arial.ttf'))
        # canvas.Canvas(response).setFont('Arial', 14)
        # canvas.Canvas(response).drawString(100, 750, 'Список покупок')
        # height = 700
        # for i in ingr_list:
        #     canvas.Canvas(response).drawString(80, height, f"{i}.")
        #     height -= 25
        # for i, (name, data) in enumerate(ingr_list.items(), start=1):
        #     canvas.Canvas(response).drawString(
        #         80, height,
        #         f"{i}. {name} – {data['amount']} {data['unit']}")
        #     height -= 25
        # canvas.Canvas(response).showPage()
        # canvas.Canvas(response).save()
        # ingredients = IngredientsList.objects.filter(
        #     recipe__shopping_cart__user=request.user).values_list(
        #     'ingredients__name', 'amount', 'ingredients__measurement_unit')
        # ingr_list = {}
        # for name, amount, unit in ingredients:
        #     if name not in ingr_list:
        #         ingr_list[name] = {'amount': amount, 'unit': unit}
        #     else:
        #         ingr_list[name]['amount'] += amount
        # return response


class SubscribeViewSet(UserViewSet):
    queryset = User.objects.all()
    serializer_class = MyUserSerializer
    pagination_class = RecipePagination
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)

    @action(
        detail=True,
        methods=['POST', 'DELETE']
    )
    def subscribe(self, request, id):
        user = request.user
        author = get_object_or_404(User, id=id)
        subscription = Subscribe.objects.filter(
            user=user,
            author=author
        )
        if request.method == 'POST':
            if subscription.exists():
                return Response({'error': 'Вы уже подписаны'},
                                status=status.HTTP_400_BAD_REQUEST)
            if user == author:
                return Response({'error': 'Невозможно подписаться на себя'},
                                status=status.HTTP_400_BAD_REQUEST)
            serializer = SubscribeSerializer(
                author, context={'request': request}
            )
            Subscribe.objects.create(user=user, author=author)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == 'DELETE':
            if subscription.exists():
                subscription.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            return Response({'error': 'Вы не подписаны на этого пользователя'},
                            status=status.HTTP_400_BAD_REQUEST)

    @action(
        detail=False,
        methods=['GET'],
        url_path='subscriptions',
        url_name='subscriptions',
        permission_classes=(permissions.IsAuthenticated,),
    )
    def subscriptions(self, request):
        queryset = User.objects.filter(followers__user=request.user)
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
