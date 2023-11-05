[![.github/workflows/main.yml](https://github.com/Trivium1999/foodgram-project-react/actions/workflows/main.yml/badge.svg)](https://github.com/Trivium1999/foodgram-project-react/actions/workflows/main.yml)

# Foodgram - социальная сеть для любителей готовить

## Возможности сервиса
- Создавать свои рецепты
- Читать рецепты других пользователей
- Подписываться на избранных авторов 
- Добавлять рецепты в избранное
- Добавлять рецепты в список покупок, чтобы потом выгрузить список ингредиентов

## Технологии
- Python 
- Django 
- Django REST framework 
- JavaScript

#  Запуск проекта из репозитория GitHub:
1. Клонируйте репозиторий на свой компьютер
2. Перейдите в директорию infra и пропишите команду:
```
sudo docker compose up -d
```

# Запуск проекта из образов DockerHub:
1. Создайте папку, в которой будет храниться проект
2. Скачайте файл ```docker-compose.yml``` и запустите его командой:
```
sudo docker compose up -d
```

- Выполните миграции, соберите статику, создайте суперпользователя
```bash
docker compose exec backend python manage.py makemigrations
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py collectstatic
docker compose exec backend cp -r /app/collected_static/. /app/static/
docker compose exec backend python manage.py createsuperuser
```
- Наполните базу данных ингредиентами и тегами
```bash
docker-compose exec backend python manage.py load_data

Проект доступен по адресу: http://foodgram-little4one.sytes.net
Автор: Анна Романова
