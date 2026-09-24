# Задачи: Разработка коннектора baza.drom.ru для ru-marketplace-mcp

- [x] Изучить архитектуру `ru-marketplace-mcp` (монорепозиторий uv, mcp-core, FastMCP, протоколы защиты, соглашения по коду)
- [x] Провести live-зондирование `baza.drom.ru` (WAF, кодировка Windows-1251, структура выдачи, карточки товаров, профили продавцов, отзывы)
- [x] Определить транспортный уровень (Chrome CDP Tier-2 через DevTools MCP / in-page fetch, с возможностью Tier-1 через residential proxy)
- [x] Создать детальный `implementation_plan.md` с архитектурными решениями, моделями данных, спецификациями инструментов и тестами
- [x] Согласовать план реализации с пользователем (автосогласование получено)
- [x] Развернуть монорепозиторий в рабочей директории
- [x] Реализовать пакет `packages/drom-connector`:
  - [x] `pyproject.toml`
  - [x] `src/drom_connector/settings.py`
  - [x] `src/drom_connector/models_output.py`
  - [x] `src/drom_connector/shape_reference.py`
  - [x] `src/drom_connector/server.py`
  - [x] `src/drom_connector/__init__.py`, `__main__.py`, `py.typed`
- [x] Реализовать тестовые фикстуры и unit-тесты (`tests/test_server.py`, `tests/test_settings_secrets.py`, `tests/test_shape_reference.py`)
- [x] Создать документацию и скилл `skills/drom-connector/SKILL.md` (включая зеркало в `dsh/skills/drom-connector/SKILL.md`)
- [x] Зарегистрировать коннектор в корневом `pyproject.toml`, `marketplace-connector` и `compare-connector`
- [x] Провести валидацию (ruff, mypy, pytest, no-print check, selfcheck)

## Результаты проверки базового коннектора

- `uv run pytest packages/drom-connector/tests -v` — 20 passed.
- `uv run pytest packages/marketplace-connector/tests -v` — 146 passed, 1 skipped (0 failed).
- `uv run pytest packages/compare-connector/tests -v` — 96 passed (0 failed).
- `uv run ruff check` — 0 errors.
- `uv run ruff format --check` — 32 files formatted.
- `uv run mypy -p drom_connector -p compare_connector -p marketplace_connector` — Success (16 source files).
- `uv run python scripts/check_no_print.py` — checked 88 files, 0 stdout writes.

## Задачи: Фото-инспекция деталей (скачивание, передача и анализ состояния)

- [x] 1. Реализация скачивания и передачи фото в `packages/drom-connector`:
  - [x] Реализовать функцию `_download_photo(url, high_res=True)` (загрузка CDN / in-page CDP, выбор `_full` разрешения, Base64 ImageContent)
  - [x] Реализовать инструмент `@mcp.tool drom_card_photos(url_or_id, max_photos=5, high_res=True)` с поддержкой `mcp.types.ImageContent`
  - [x] Добавить в `drom_card` явное указание на необходимость вызова `drom_card_photos`
  - [x] Добавить `## Return Format` и `## Error Format` в docstrings
- [x] 2. Unit-тесты для фото-функционала:
  - [x] Тесты скачивания фото (mock responses, base64, mimeTypes)
  - [x] Тесты инструмента `drom_card_photos` (извлечение фото из карточки, возврат `ImageContent` и `TextContent`)
- [x] 3. Документация и скиллы (`skills/drom-connector/SKILL.md` и `dsh/`):
  - [x] Добавить `drom_card_photos` в список доступных MCP-инструментов
  - [x] Добавить протокол обязательного визуального анализа фото (проверка соответствия детали, геометрии, OEM-номеров, кронштейнов, дефектов, износа, трещин)
- [x] 4. Синхронизация монорепозитория:
  - [x] Обновить тесты `test_wire_frugality.py` (число инструментов 42 -> 43) и `test_server.py`
  - [x] Обновить `public_contract.json` через скрипт `test_public_contract_snapshot.py`
  - [x] Обновить схемы инструментов в `C:\Users\andrei\.gemini\antigravity\mcp\drom` (`drom_card_photos.json`, `instructions.md`)
  - [x] Обновить `C:\mcp\ru_marketplace-mcp` (ветка main синхронизирована с форком)
- [x] 5. Верификация:
  - [x] Полный прогон `pytest`, `mypy`, `ruff`, `check_no_print.py` (273 passed, 1 skipped, 0 failed, 0 ruff errors, mypy success)
  - [x] Пуш в GitHub форк пользователя (`https://github.com/andrei-tolstov/ru-marketplace-mcp`, коммит `f4ca895`)

## Итоговые результаты реализации фото-контроля Drom

1. **Инструмент `drom_card_photos`**:
   - Принимает `url_or_id` (ID лота, goods ID `g...`, ссылку на объявление или прямую ссылку на фото).
   - Поддерживает получение оригиналов высокого разрешения (`high_res=True`, автозамена `_bulletin` -> `_full`).
   - Возвращает структурированный `TextContent` с ключевыми параметрами детали и обязательным протоколом инспекции, а также последовательность `ImageContent` в формате Base64 с определением MIME-типа (`image/webp`, `image/jpeg`, `image/png`).
2. **Протокол визуального контроля**:
   - Закреплен в docstring инструментов `drom_card` и `drom_card_photos`.
   - Включен в скиллы `skills/drom-connector/SKILL.md` и `dsh/skills/drom-connector/SKILL.md`.
   - Обязывает модель перед выдачей вердикта проверять:
     * геометрию, крепежные ушки/кронштейны, сторону (L/R) и рестайлинг;
     * совпадение OEM-штампов и маркировок на деталях;
     * отсутствие трещин, заломов, ржавчины, обломанных ушей, следов кустарной пайки/сварки и износа РТИ.
3. **Все тесты пройдены**: 273 passed, 1 skipped. Все проверки ruff, mypy, wire frugality и contract snapshot успешно завершены. Изменения опубликованы в GitHub форке.
