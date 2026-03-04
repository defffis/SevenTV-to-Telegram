# SevenTV-to-Telegram

Утилита синхронизирует эмоуты пользователя 7TV в Telegram-наборы (custom emoji и/или stickers) через локальный запуск и GitHub Actions.

---

## Назначение проекта

`SevenTV-to-Telegram` нужен, чтобы автоматически:

- читать активный emote set пользователя в 7TV;
- строить целевое состояние для Telegram;
- рассчитывать diff (`create` / `update` / `delete`);
- применять изменения в Telegram API (или выполнять dry-run без изменений);
- сохранять артефакты запуска (`report.json`, `desired-state.json`, `run.log`).

Основной сценарий — регулярная синхронизация через nightly/manual workflow в GitHub Actions, а также безопасный локальный dry-run перед боевым применением.

---

## Ограничения

### Общие ограничения проекта

- Проект работает только с **активным emote set** указанного пользователя 7TV.
- Поддерживаются только два типа синхронизации:
  - `emoji` (статические custom emoji);
  - `stickers` (animated/video-контент в терминах текущей реализации).
- Для Telegram-операций используются только наборы, имя которых оканчивается на `_by_<bot_username>` (защита от изменения чужих наборов).
- Создание/обновление возможно только если у бота есть корректные права и `user_id` для операций со стикер-наборами.

### Ограничения по размеру шардов

- Встроенные лимиты на один набор:
  - `emoji`: максимум `200` элементов;
  - `stickers`: максимум `120` элементов.
- Фактический `SHARD_SIZE` берётся как `min(SHARD_SIZE, лимит Telegram для типа)`.

### Ограничения по именованию

- Имена шардов формируются как:  
  `<base>_<kind>_<NNN>_by_<bot_username>`
- Пример: `seventv_emoji_001_by_mybot`.

---

## Допущения и ограничения API (7TV и Telegram)

### 7TV API: допущения

- Используется `https://7tv.io/v3`.
- Если задан `SEVENTV_EMOTE_SET_ID`, провайдер сразу читает набор по `GET /emote-sets/{SEVENTV_EMOTE_SET_ID}` (без зависимости от структуры user-профиля).
- Иначе профиль пользователя читается по `GET /users/{SEVENTV_USER_ID}`, затем активный emote set ищется в root-полях (`emote_set` / `emote_set_id`) и в `connections[]` (`emote_set` / `emote_set_id`) с приоритетом `TWITCH`; при наличии только id набор догружается через `GET /emote-sets/{id}`.
- Если активный набор не найден или имеет неожиданный формат — синхронизация завершается ошибкой.
- Выбор файла эмоута делается эвристически по формату/размеру, затем строится `image_url`.

### 7TV API: ограничения/риски

- Контракт ответа 7TV не закреплён этим проектом; при изменении схемы API может потребоваться адаптация парсинга.
- Ретраи настроены только на сетевые/таймаут-ошибки; логические ошибки ответа не ретраятся бесконечно.

### Telegram API: допущения

- Используется Bot API (`https://api.telegram.org/bot<TOKEN>` по умолчанию).
- Набор операций: `getStickerSet`, `createNewStickerSet`, `addStickerToSet`, `replaceStickerInSet`, `deleteStickerFromSet`, `setStickerEmojiList`, `setStickerSetTitle`.
- Для rate limit (`429`) реализовано ожидание `retry_after`.
- Для `5xx`/сетевых ошибок есть экспоненциальный backoff и ограниченное число ретраев.

### Telegram API: ограничения/риски

- Изменяются только управляемые наборы с ожидаемым суффиксом имени.
- Если Telegram возвращает ошибки прав/валидации, синхронизация завершится ошибкой.
- Требуется корректный `TELEGRAM_BOT_USER_ID` для операций создания/изменения наборов.

### Animated / Video policy (важно)

Политика задаётся переменными окружения:

- `ENABLE_ANIMATED=1` (по умолчанию): разрешает animated-источники (`gif`, `webp`, `tgs`).
- `ENABLE_VIDEO=0` (по умолчанию): **запрещает** video-источники (`webm`, `mp4`).

Поведение:

- если animated выключен, animated-эмоуты пропускаются и попадают в `skipped`;
- если video выключен, video-эмоуты пропускаются и попадают в `skipped`;
- если формат не поддержан политикой, элемент пропускается с причиной.

> Рекомендуется начинать с `ENABLE_VIDEO=0` и включать видео только после проверки совместимости вашего Telegram-сценария.

---

## Подготовка Telegram

1. Создайте бота через `@BotFather` и получите токен.
2. Узнайте username бота (без `@` или с `@` — проект нормализует).
3. Определите `TELEGRAM_BOT_USER_ID` (ID пользователя/бота, от имени которого выполняются операции с наборами).
4. Убедитесь, что бот может выполнять операции со стикер-наборами в вашем сценарии.
5. Выберите базовое имя набора (`TELEGRAM_SET_BASE_NAME`, например `seventv`).

Минимально обязательные переменные:

- `SEVENTV_USER_ID`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_BOT_USERNAME`

---

## Настройка GitHub Secrets / Environment

Проектные workflow (`manual-sync.yml`, `nightly-sync.yml`) запускают job в `environment: production` и читают параметры из `secrets`.

### Обязательно

- `SEVENTV_USER_ID`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_BOT_USERNAME`

### Опционально

- `SEVENTV_EMOTE_SET_ID`
- `TELEGRAM_BOT_USER_ID`
- `TELEGRAM_SET_BASE_NAME`
- `TELEGRAM_API_BASE_URL`
- `TELEGRAM_MAX_RETRIES`
- `TELEGRAM_BACKOFF_SECONDS`
- `TELEGRAM_TIMEOUT_SECONDS`
- `SHARD_SIZE`
- `ENABLE_ANIMATED`
- `ENABLE_VIDEO`

### Критически важное правило безопасности

**Никогда не храните секреты в репозитории** (`.env`, токены, приватные ID, ключи).  
Используйте только:

- GitHub Secrets / Environments для CI;
- локальный `.env`, который не коммитится.

Перед пушем проверяйте, что в git diff нет секретов.

---

## Локальный запуск

### 1) Создать и активировать venv

```bash
python -m venv .venv
source .venv/bin/activate
```

### 2) Установить зависимости

```bash
pip install -r requirements.txt
```

(для разработки)

```bash
pip install -e .[dev]
```

### 3) Подготовить `.env`

```bash
cp .env.example .env
```

Заполните обязательные переменные. Не коммитьте `.env`.

### 4) Dry-run (без изменений в Telegram)

```bash
./scripts/local_run.sh --dry-run
```

### 5) Apply (реальное применение)

```bash
./scripts/local_run.sh
```

### Полезные флаги

- `--kind emoji` или `--kind stickers`
- `--force-full-resync`
- `--max-items 50`

Пример:

```bash
./scripts/local_run.sh --dry-run --kind stickers --max-items 50
```

### Артефакты запуска

Пишутся в `artifacts/`:

- `artifacts/report.json`
- `artifacts/desired-state.json`
- `artifacts/run.log`

---

## Архитектура и pipeline

### Основные компоненты

- `SevenTVProvider` — чтение исходного состояния из 7TV.
- `SyncService` — оркестрация: normalize → render → diff → apply → shard plan.
- `TelegramProvider` — чтение/изменение целевого состояния в Telegram.
- `build_diff` — расчёт операций create/update/delete.
- `shard_target_sets` — разбиение на наборы (шарды) с учётом лимитов.

### Логический pipeline

1. Получить source items из 7TV (`emoji` или `stickers`).
2. Нормализовать в внутреннюю модель.
3. Рендер/политика:
   - static → профиль Telegram;
   - animated/video → по флагам `ENABLE_ANIMATED` / `ENABLE_VIDEO`.
4. Прочитать текущий Telegram state.
5. Вычислить diff.
6. Применить изменения (или смоделировать в dry-run).
7. Построить projected state и shard-план.
8. Записать отчёты в артефакты.

### CI pipeline

- `Nightly Sync` — плановый запуск по cron + ручной trigger.
- `Manual Sync` — ручной запуск с параметрами (`dry_run`, `force_full_resync`, `max_items`, `sync_kind`).

Оба workflow:

- устанавливают Python 3.12;
- ставят зависимости и `ffmpeg`;
- запускают `./scripts/local_run.sh`;
- публикуют артефакты.

---

## Troubleshooting

### Ошибка: `Missing required environment variables`

Проверьте, что заданы обязательные переменные:

- `SEVENTV_USER_ID`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_BOT_USERNAME`

Опционально для детерминированного выбора набора:

- `SEVENTV_EMOTE_SET_ID`

### Ошибки Telegram `429 Too Many Requests`

Это rate limit. Провайдер уже учитывает `retry_after`. При частых повторениях:

- уменьшите объём батча (`--max-items`);
- запускайте по видам (`--kind emoji`, затем `--kind stickers`);
- увеличьте `TELEGRAM_BACKOFF_SECONDS`.

### Ошибка `STICKERSET_INVALID`

Обычно означает, что набора ещё нет или имя некорректно. Проверьте:

- `TELEGRAM_SET_BASE_NAME`;
- `TELEGRAM_BOT_USERNAME`;
- доступность/права бота.

### Много элементов в `skipped`

Проверьте policy-флаги:

- `ENABLE_ANIMATED`
- `ENABLE_VIDEO`

Если video отключён, `webm/mp4` будут пропущены — это ожидаемо.

### Падает на сетевых ошибках

Проверьте:

- доступ к `https://7tv.io` и `https://api.telegram.org`;
- прокси/фаервол;
- таймаут `TELEGRAM_TIMEOUT_SECONDS`.

---

## FAQ

### Нужен ли `--force-full-resync` на каждый запуск?

Нет. Обычно не нужен. Используйте только при подозрении на рассинхронизацию или после изменений логики рендера.

### Можно ли синхронизировать только emoji или только stickers?

Да, через `--kind emoji` или `--kind stickers`.

### Что делает `--dry-run`?

Считает diff и формирует план без реальных изменений в Telegram. Это безопасный режим предварительной проверки.

### Где смотреть результат запуска?

В `artifacts/report.json`, `artifacts/desired-state.json`, `artifacts/run.log`.

### Можно ли хранить токен бота в `README` или в коде?

Нет. Секреты не должны попадать в git-историю, код, README, issue и PR-тексты.

### Почему часть эмоутов не попала в Telegram?

Частые причины:

- тип контента запрещён policy (`ENABLE_ANIMATED` / `ENABLE_VIDEO`);
- лимиты Telegram и шардирование;
- временные API-ошибки/rate limits;
- изменение данных на стороне 7TV.
