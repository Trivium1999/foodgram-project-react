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
from users.models import Subscribe, User
from recipes.models import (Recipes,
                            Tag,
                            Favorite,
                            ShoppingList,
                            Ingredient,
                            IngredientsList)
from .serializers import (TagSerializer,
                          IngredientSerializer,
                          RecipeSerializer,
                          RecipeCreateSerializer,
                          MyUserSerializer,
                          SubscribeSerializer,
                          ShoppingListSerializer)
from .permissios import IsAdminOrAuthorOrReadOnly


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None


class RecipesViewSet(viewsets.ModelViewSet):
    queryset = Recipes.objects.all()
    serializer_class = RecipeSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly,
                          IsAdminOrAuthorOrReadOnly, ]
    pagination_class = RecipePagination
    filter_backends = (DjangoFilterBackend, )
    # filterset_class = 

    # def get_queryset(self):
    #     return Recipes.objects.prefetch_related(
    #         'ingredient__recipe',
    #         'tags',
    #         'author'
    #     ).all()

    def get_serializer_class(self):
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

    def add_remove_recipe(self, request, id, model):
        recipe = get_object_or_404(Recipes, id=id)
        obj, created = model.objects.select_related(
            'user', 'recipe'
        ).get_or_create(user=request.user, recipe=recipe)
        if request.method == 'POST' and created:
            serializer = RecipeSerializer(
                recipe,
                context={'request': request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        if request.method == 'DELETE' and obj:
            obj.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        raise exceptions.ValidationError(
            detail='Вы уже совершили это действие!'
        )
    # def delete_recipe(class_object, user, recipe):
    #     try:
    #         del_recipe = class_object.objects.get(user=user, recipe=recipe)
    #     except class_object.DoesNotExist:
    #         return Response(
    #             {'errors': 'Невозможно удалить'},
    #             status=status.HTTP_400_BAD_REQUEST
    #         )
    #     del_recipe.delete()
    #     return Response(
    #         {'detail': 'Удаление прошло успешно'},
    #         status=status.HTTP_204_NO_CONTENT
    #     )

    @action(methods=['POST', 'DELETE'], detail=True)
    def favorite(self, request, pk):
        recipe_obj = get_object_or_404(Recipes, pk=pk)
        if request.method == 'POST':
            return self.create_recipe(
                class_object=Favorite,
                user=request.user,
                recipe=recipe_obj,
                serializer=RecipeSerializer
            )
        elif request.method == 'DELETE':
            return self.delete_recipe(
                class__object=Favorite,
                user=request.user,
                recipe=recipe_obj
            )

    def get_shopping_list(self, request, pk):
        recipe = get_object_or_404(Recipes, pk=pk)
        if request.method == 'POST':
            serializer = ShoppingListSerializer(
                data={'user': request.user.id, 'recipe': recipe.id}
            )
            serializer.is_valid(raise_exeption=True)
            serializer.save()
            shopping_list_serializer = RecipeSerializer(recipe)
            return Response(
                shopping_list_serializer.data, status=status.HTTP_201_CREATED
            )
        shopping_list_serializer = get_object_or_404(
            ShoppingList, user=request.user, recipe=recipe
        )
        shopping_list_serializer.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def create_shopping_list(ingredients_list):
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = (
            "attachment; filename='shopping_list.pdf'"
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
        url_path='download_shopping_list',
        url_name='download_shopping_list',
        permission_classes=(permissions.IsAuthenticated,)
    )
    def download_shopping_list(self, request):
        ingredients_list = (
            IngredientsList.objects.filter(
                recipe__shopping_list__user=request.user
            ).values(
                'ingredient__name',
                'ingredient__measurement_unit'
            ).order_by(
                'ingredient__name'
            ).annotate(ingredient_value=Sum('amount'))
        )
        return self.create_shopping_list(ingredients_list)


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None
    filter_backends = (DjangoFilterBackend,)
    # filterset_class =
    # search_fields = ['^name', ]


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
        queryset = User.objects.filter(subscriber__user=self.request.user)
        serializer = SubscribeSerializer(
            self.paginate_queryset(queryset),
            context={'request': request},
            many=True
        )
        return self.get_paginated_response(serializer.data)
    # def post(self, request, id):
    #     author_obj = get_object_or_404(User, pk=id)
    #     if request.user == author_obj:
    #         return Response(
    #             {'errors': 'Подписаться на себя нельзя'},
    #             status=status.HTTP_400_BAD_REQEST
    #         )
    #     data = {'user': request.user, 'author': author_obj}
    #     already_existed, created = Subscribe.objects.get_or_create(**data)
    #     if not created:
    #         return Response(
    #             {'errors': 'Ошибка при создании записи'},
    #             status=status.HTTP_400_BAD_REQEST
    #         )
    #     return Response(
    #         MyUserSerializer(
    #             author_obj,
    #             context={'request': request}
    #         ).data,
    #         status=status.HTTP_201_CREATED
    #     )

    # def delete(self, request, id):
    #     author = get_object_or_404(User, id=id)
    #     if not Subscribe.objects.filter(
    #         user=request.user, author=author
    #     ).exists():
    #         return Response(status=status.HTTP_400_BAD_REQEST)
    #     subscription = get_object_or_404(
    #         Subscribe, user=request.user, author=author
    #     )
    #     subscription.delete()
    #     return Response(status=status.HTTP_204_NO_CONTENT)


# class SubscriptionsViewSet(ListAPIView):
#     permission_classes = [IsAuthenticated, ]
#     pagination_class = RecipePagination

#     def get(self, request):
#         queryset = request.user.followers.all()
#         page = self.paginate_queryset(queryset)
#         serializer = SubscribeSerializer(page, many=True, context={
#             'request': request
#         })
#         return self.get_paginated_response(serializer.data)
