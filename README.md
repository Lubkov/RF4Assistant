# RF4 Assistant v0.1 — стартовый каркас

Первый этап: только структура Django-проекта, настройки, приложения и тестовая главная страница. Модели, миграции с 18 водоёмами и 251 рыбой, Django Admin и Bootstrap-карточки — следующие этапы.

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
- `waterbodies` — приложение будущей модели водоёма.
- `fish` — приложение будущих моделей рыбы и связи водоём–рыба.
- `templates` — базовый шаблон и частичные шаблоны.
- `static` — код и ресурсы приложения.
- `media` — изображения, загружаемые администратором.

**Важно:** `SECRET_KEY` имеет небезопасное значение для локальной разработки, а `DEBUG` включён. Перед публикацией задайте `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=0` и `DJANGO_ALLOWED_HOSTS` через переменные окружения; отдельно настройте выдачу статических и медиафайлов. `runserver` предназначен только для разработки.
