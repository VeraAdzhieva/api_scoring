## API scoring
Валидация запросов к АПИ.

## Установка
1. Клонирование репозитория
```git clone https://github.com/VeraAdzhieva/api_scoring.git```
2. Установка зависимостей
```poetry install```

## Основные зависимости
Ключевые библиотеки:
- **pytest** — тестирование
- **black, isort, flake8** — форматирование и статический анализ кода

*Полный список зависимостей доступен в `pyproject.toml`.*

## Запуск тестов
```poetry run pytest tests/test.py -v```

## Запуск pre-commit
```poetry run pre-commit run --all-files```

## Пример запуска кода
- запустить сервис
- отправить запрос:
    --пример валидного запроса **online_score**:
        ```curl -X POST -H "Content-Type: application/json" -d '{"account": "horns&hoofs", "login": "h&f", "method": "online_score", "token": "55cc9ce545bcd144300fe9efc28e65d415b923ebb6be1e19d2750a2c03e80dd209a27954dca045e5bb12418e7d89b6d718a9e35af34e14e1d5bcd5a08f21fc95", "arguments": {"phone": "79175002040", "email": "stupnikov@otus.ru", "first_name": "Стансилав", "last_name": "Ступников", "birthday": "01.01.1990", "gender": 1}}' http://127.0.0.1:8080/method/```
    --пример валидного запроса **clients_interests**:
        ```curl -X POST -H "Content-Type: application/json" -d '{"account": "horns&hoofs", "login": "admin", "method": "clients_interests", "token": "d3573aff1555cd67dccf21b95fe8c4dc8732f33fd4e32461b7fe6a71d83c947688515e36774c00fb630b039fe2223c991f045f13f24091386050205c324687a0", "arguments": {"client_ids": [1,2,3,4], "date": "20.07.2017"}}' http://127.0.0.1:8080/method/```