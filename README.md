# RF4 Assistant v0.1 — стартовый каркас

Второй этап: модели `Waterbody`, `Fish`, `WaterbodyFish`, миграции схемы и начальное заполнение базы (18 водоёмов и 251 рыба). Django Admin и публичные карточки — следующие этапы.

## Требования

- Python 3.10+ (рекомендуется Python 3.12 или 3.13)
- Windows PowerShell (инструкции ниже) или другое окружение Python

## Запуск в Windows PowerShell

```powershell
cd C:\path\to\rf4-assistant
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

Если установлен другой Python, замените `py -3.13` на путь к вашему `python.exe` или на `py -3.12`.

Откройте http://127.0.0.1:8000/ . Django Admin: http://127.0.0.1:8000/admin/ . Создайте администратора командой `manage.py createsuperuser` (передав её через python из `.venv`).

Для запуска тестов:

```powershell
.\.venv\Scripts\python.exe manage.py test
```

## Архитектура

- `config` — настройки, корневые URL, ASGI/WSGI.
- `core` — публичная главная страница.
- `waterbodies` — модель водоёма и миграция 18 исходных записей.
- `fish` — модели рыб и связей с водоёмами, миграция 251 исходной записи.
- `templates` — базовый шаблон и частичные шаблоны.
- `static` — код и ресурсы приложения.
- `media` — изображения, загружаемые администратором.

**Важно:** `SECRET_KEY` имеет небезопасное значение для локальной разработки, а `DEBUG` включён. Перед публикацией задайте `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=0` и `DJANGO_ALLOWED_HOSTS` через переменные окружения; отдельно настройте выдачу статических и медиафайлов. `runserver` предназначен только для разработки.

## Структура данных (этап 2)

- `Waterbody`: сохраняет ID/название/уровень из старой `Location`; дополнительные поля `slug`, `description`, `image`, `sort_order`, `is_active`. Изображения загружаются в `media/waterbodies/` (пока интерфейс загрузки через Django Admin не настроен).
- `Fish`: сохраняет ID, название, трофейный вес (г) и редкость 1/2/3; значение `9999999` порога супертрофея заменяется на `NULL` для ID 154 и 240. Изображений рыб пока нет.
- `WaterbodyFish`: самостоятельный `id`, внешние ключи на водоём и рыбу, ограничение уникальности пары. Связей изначально нет.

Миграции `0001_initial` создают структуру, `0002_seed_*` заполняют справочники. Для сохранности пользовательских изменений обратное действие у data migrations оставлено пустым (не удаляет справочники). После применения проверьте: `python manage.py check`, `python manage.py makemigrations --check --dry-run`, `python manage.py test`. Для `Fish` и `WaterbodyFish` админ-формы появятся на следующем этапе.
