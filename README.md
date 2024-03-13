# Документация по проекту Referral System API

Этот проект представляет собой простой RESTful API сервис для реферальной системы. Он предоставляет функциональность для регистрации и аутентификации пользователей, создания и удаления реферальных кодов, получения реферальных кодов по электронной почте, регистрации по реферальному коду и получения информации о рефералах.

## Требования

- Python 3.x
- Flask
- Flask-SQLAlchemy
- Flask-JWT-Extended
- Flask-Marshmallow
- Flask-Swagger-UI

## Установка

1. Склонируйте репозиторий:
```bash
git clone https://github.com/your-username/referral-system-api.git
```
1. Перейдите в каталог проекта:
```bash
cd referral-system-api
```
1. Создайте и активируйте виртуальное окружение (рекомендуется):
```bash
python -m venv venv
source venv/bin/activate (Linux/macOS)
venv\Scripts\activate (Windows)
```
1. Установите необходимые пакеты:
```bash
pip install -r requirements.txt
```
## Запуск

1. Выполните следующую команду, чтобы запустить сервер:
```bash
python app.py
```
1. Откройте веб-браузер и перейдите по адресу `http://localhost:5000/api/docs`, чтобы просмотреть документацию Swagger UI.

## Использование

Вы можете использовать инструменты, такие как curl, Postman или Swagger UI, для взаимодействия с API. Ниже приведены некоторые примеры использования curl.

### Регистрация пользователя

```bash
curl -X POST -H "Content-Type: application/json" -d '{"email": "user@example.com", "password": "password123"}' http://localhost:5000/register
```

### Авторизация пользователя

```bash
curl -X POST -H "Content-Type: application/json" -d '{"email": "user@example.com", "password": "password123"}' http://localhost:5000/login
```

### Создание реферального кода

```bash
curl -X POST -H "Content-Type: application/json" -H "Authorization: Bearer <access_token>" -d '{"code": "ABCDEF", "expiry": "2023-12-31T23:59:59"}' http://localhost:5000/referral_code
```

### Удаление реферального кода

```bash
curl -X DELETE -H "Authorization: Bearer <access_token>" http://localhost:5000/referral_code
```

### Получение реферального кода по электронной почте

```bash
curl -X GET http://localhost:5000/referral_code/user@example.com
```

### Регистрация по реферальному коду

```bash
curl -X POST -H "Content-Type: application/json" -d '{"email": "newuser@example.com", "password": "password123", "referral_code": "ABCDEF"}' http://localhost:5000/register
```

### Получение информации о рефералах

```bash
curl -X GET -H "Authorization: Bearer <access_token>" http://localhost:5000/referrals/<user_id>
```

Замените `<access_token>` на полученный токен доступа, а `<user_id>` на идентификатор пользователя.

## Документация API

Документация API доступна в формате Swagger UI. После запуска сервера вы можете просмотреть документацию, перейдя по адресу `http://localhost:5000/api/docs`.
