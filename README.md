# Video Playlist Manager (сервер)

Сервер на **FastAPI** для загрузки видео, управления плейлистом с датами показа и выдачи актуального списка клиентам **Android TV** (MD5, версия файла, ревизия плейлиста).

## Установка и запуск

```bash
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python app/main.py
```

По умолчанию: `http://127.0.0.1:8000/`.

Для продакшена укажите `DATABASE_URL` на PostgreSQL, ограничьте `CORS_ORIGINS`, задайте `ADMIN_USERNAME` / `ADMIN_PASSWORD` и `SECRET_KEY`.

## Аутентификация админки

Если в `.env` заданы `ADMIN_USERNAME` и `ADMIN_PASSWORD`, браузер запросит **HTTP Basic** при открытии `/` и при обращении к защищённым API. Эндпоинты синхронизации для ТВ (`/api/sync`, `/api/download/...`, `/api/client/status`) остаются без Basic Auth (ограничьте доступ на уровне сети или добавьте отдельный токен при необходимости).

## Примеры запросов (curl)

Список видео (при включённой админской аутентификации подставьте `-u user:pass`):

```bash
curl -s http://127.0.0.1:8000/api/videos
```

Загрузка файла:

```bash
curl -s -F "file=@/path/to/video.mp4" http://127.0.0.1:8000/upload
```

Плейлист:

```bash
curl -s http://127.0.0.1:8000/api/playlist
```

Добавить видео в плейлист:

```bash
curl -s -X POST http://127.0.0.1:8000/api/playlist \
  -H "Content-Type: application/json" \
  -d '{"video_id":1}'
```

Изменить порядок:

```bash
curl -s -X POST http://127.0.0.1:8000/api/playlist/reorder \
  -H "Content-Type: application/json" \
  -d '{"items":[{"id":1,"order":0},{"id":2,"order":1}]}'
```

Синхронизация для клиента:

```bash
curl -s "http://127.0.0.1:8000/api/sync?client_id=tv-living-room-01"
```

Статус клиента:

```bash
curl -s -X POST "http://127.0.0.1:8000/api/client/status?client_id=tv-living-room-01" \
  -H "Content-Type: application/json" \
  -d '{"detail":"ok","synced_playlist_version":3}'
```

Скачивание (заголовки `X-Video-MD5`, `X-Video-Version`):

```bash
curl -sOJ http://127.0.0.1:8000/api/download/1
```

## Структура

См. каталоги `app/`, `static/`, `templates/`, `uploads/` — соответствуют описанию в ТЗ.

## Примечание по python-magic

Для проверки MIME через `libmagic` в системе должен быть установлен пакет **file** (на macOS часто уже есть). Если `magic` недоступен, используется запасная проверка по расширению и `Content-Type`.
