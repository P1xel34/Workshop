# Гостевая книга — FastAPI + PostgreSQL

Небольшой API: приветствие, проверка работы, добавление и чтение сообщений.
Приложение упаковано в Docker, PostgreSQL хранит сообщения в отдельном volume.
GitHub Actions запускает Ruff и pytest на push и pull request. После успешной
проверки push в main собирает и публикует образ в GHCR с тегом latest.

## Быстрый запуск в Windows (PowerShell)

Нужны запущенный Docker Desktop с Linux containers и Docker Compose v2.
Откройте терминал в папке проекта, где лежит compose.yaml.

При первом запуске:

```powershell
Copy-Item .env.example .env
notepad .env
```

Замените POSTGRES_PASSWORD на свой локальный пароль и сохраните файл.
После настройки запуск выполняется одной командой:

```powershell
docker compose up --build -d --wait
```

Откройте:

- http://localhost:8000/ — приветствие;
- http://localhost:8000/health — ответ `{"status":"ok"}`;
- http://localhost:8000/docs — Swagger UI для отправки сообщений;
- http://localhost:8000/messages — список сообщений.

В Swagger раскройте POST /messages → Try it out, отправьте:

```json
{"author":"Матвей","text":"Привет из Docker!"}
```

После этого GET /messages должен вернуть добавленное сообщение.

## Устройство проекта

- main.py — API и создание таблицы при старте.
- config.py — настройки через pydantic-settings.
- pyproject.toml, uv.lock, .python-version — зависимости и Python 3.12.
- Dockerfile — сначала установка зависимостей, затем копирование кода.
- compose.yaml — приложение, PostgreSQL, healthcheck и постоянный volume.
- tests/ — 6 тестов; проверки сообщений используют настоящую PostgreSQL.
- .github/workflows/ci.yml — проверка и публикация образа.

В compose приложение подключается к базе по имени `db`. Значения DB_USER,
DB_PASSWORD и DB_NAME берутся из POSTGRES_USER, POSTGRES_PASSWORD и POSTGRES_DB
в локальном .env. Дублировать их двумя наборами переменных не нужно.
`.env` исключён из Git и Docker build context. `.env.example` содержит только
пример. Порт базы не опубликован на хосте; API доступен на localhost:8000.

`/health` — проверка ответа приложения, без SQL-запроса. Готовность PostgreSQL
проверяет отдельный healthcheck базы. Схема исходной гостевой книги сохранена.

## Управление

```powershell
docker compose ps
docker compose logs --tail 100 app
docker compose logs --tail 100 db
docker compose down
docker compose up -d --wait
```

`down` сохраняет volume. Ключ `-v` удаляет данные — для обычной остановки его
не используйте. Для демонстрации сохранности добавьте сообщение, выполните
`down`, затем `up -d --wait` и проверьте GET /messages.

При переносе этих файлов в существующий проект сохраните прежний `.env`,
папку проекта и имя Compose-проекта. Значения POSTGRES_* должны соответствовать
уже созданной базе. Изменение пароля в .env не меняет пароль существующего
пользователя PostgreSQL в volume.

## CI и образ

На push и pull_request job `check` устанавливает зависимости строго по uv.lock,
запускает Ruff и все тесты. GitHub Actions сам поднимает отдельную PostgreSQL
для тестов; ваш локальный .env ему не нужен. Тестовый пароль в workflow относится
только к одноразовой базе CI.

Job `publish` зависит от `check` и запускается на push в main или тега vX.Y.Z. Он
использует встроенный GITHUB_TOKEN с правом packages:write и публикует:

```text
ghcr.io/<владелец>/<репозиторий>:latest
```

Имя образа приводится к нижнему регистру. Дополнительный токен в Secrets для
публикации создавать не нужно. В репозитории должна быть разрешена работа
GitHub Actions; ограничения организации могут запрещать публикацию пакетов.

Для запуска опубликованного образа вместо локальной сборки в PowerShell:

```powershell
$env:APP_IMAGE = "ghcr.io/YOUR_LOGIN/YOUR_REPOSITORY:latest"
docker compose pull app
docker compose up -d --no-build --wait
```

Замените имя на фактическое из Packages, полностью в нижнем регистре.
Если пакет приватный, сначала авторизуйтесь через `docker login ghcr.io`
с токеном, имеющим read:packages, либо разрешите публичное чтение пакета
в его настройках. Не добавляйте токен в файлы проекта.

Чтобы снова использовать локальную сборку:

```powershell
Remove-Item Env:APP_IMAGE
docker compose up --build -d --wait
```


## Локальная проверка (не обязательна для запуска)

Для Ruff и тестов установите uv и Python 3.12. В папке проекта:

```powershell
uv sync --locked
uv run --locked ruff check .
```

Тесты сообщений очищают таблицу messages. Используйте ТОЛЬКО отдельную
одноразовую базу, не базу с нужными сообщениями. Например:

```powershell
docker run --name guestbook-test-db --rm -d -p 127.0.0.1:5433:5432 -e POSTGRES_USER=guestbook -e POSTGRES_PASSWORD=ci_test_password -e POSTGRES_DB=guestbook_test postgres:16
docker exec guestbook-test-db pg_isready -U guestbook -d guestbook_test
```

Если PostgreSQL ещё не готова, повторите команду pg_isready до ответа
`accepting connections`. Затем в том же терминале:

```powershell
$env:DB_HOST = "localhost"
$env:DB_PORT = "5433"
$env:DB_USER = "guestbook"
$env:DB_PASSWORD = "ci_test_password"
$env:DB_NAME = "guestbook_test"
uv run --locked pytest
docker stop guestbook-test-db
Remove-Item Env:DB_HOST, Env:DB_PORT, Env:DB_USER, Env:DB_PASSWORD, Env:DB_NAME
```

Тесты проверяют ответы API, пустой список, сохранение и порядок сообщений,
обработку кавычек в сообщениях, отклонение неполного запроса и специальные
символы в пароле подключения. В GitHub Actions всё это запускается автоматически.

## Релиз по тегу

После успешного workflow для main добавьте описание версии в CHANGELOG.md,
закоммитьте изменения и отправьте main. Затем создайте тег на этом коммите:

```powershell
git switch main
git pull --ff-only
git tag v0.1.0
git push origin v0.1.0
```

Actions повторно выполнит check, затем опубликует образ
`ghcr.io/<владелец>/<репозиторий>:v0.1.0`. Тег latest при этом не меняется.
Поддерживается формат vX.Y.Z без ведущих нулей. Следующие версии: v0.1.1,
v0.2.0 и т. д. Не переносите уже опубликованные теги на другие коммиты.
Git-тег и версионный образ создают релизный артефакт; отдельная страница
GitHub Releases автоматически не создаётся. Создавайте теги только на
проверенных коммитах main: workflow не проверяет принадлежность тега ветке.

Для запуска версии используйте команды из раздела «CI и образ», заменив
latest на v0.1.0. Следующую версию сначала опишите в CHANGELOG.md.
