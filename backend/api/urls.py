from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    RecipesViewSet,
    TagViewSet,
    IngredientViewSet,
    SubscribeViewSet
)

app_name = 'api'

router = DefaultRouter()
router.register('users', SubscribeViewSet, basename='users')
router.register('tags', TagViewSet, basename='tags')
router.register('ingredients', IngredientViewSet, basename='ingredients')
router.register('recipes', RecipesViewSet, basename='recipes')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/', include('djoser.urls.authtoken')),
    path('', include('djoser.urls')),
]
