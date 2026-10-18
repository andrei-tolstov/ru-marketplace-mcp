# Задачи: Синхронизация форка с upstream Vladimir-Human/ru-marketplace-mcp

- [x] 1. Инициализация и анализ:
  - [x] Добавить upstream remote `https://github.com/Vladimir-Human/ru-marketplace-mcp.git`
  - [x] Выполнить `git fetch upstream`
  - [x] Определить diff / новые коммиты в upstream/main относительно текущего main
  - [x] Зафиксировать перечень кастомных изменений в форке (drom-connector, drom_card_photos, тесты, скиллы)
- [x] 2. Слияние изменений:
  - [x] Выполнить `git merge upstream/main` в локальную ветку main
  - [x] Разрешить возможные конфликты с полным сохранением нашего функционала
  - [x] Обновить общие конфигурации монорепозитория (pyproject.toml, uv.lock, public contract) если необходимо
- [x] 3. Верификация работоспособности монорепозитория:
  - [x] Запустить `uv sync`
  - [x] Запустить `uv run ruff check` и `uv run ruff format --check`
  - [x] Запустить `uv run mypy`
  - [x] Запустить тесты монорепозитория (`packages/drom-connector`, `packages/marketplace-connector`, `packages/compare-connector` и др.)
  - [x] Запустить `uv run python scripts/check_no_print.py`
  - [x] Запустить тесты контрактов (`test_public_contract_snapshot.py`, `test_wire_frugality.py`)
- [x] 4. Обновление локально установленного MCP-сервера:
  - [x] Проверить состояние `C:\mcp\ru_marketplace-mcp`
  - [x] Синхронизировать `C:\mcp\ru_marketplace-mcp` с актуальной веткой main
  - [x] Выполнить `uv sync` в `C:\mcp\ru_marketplace-mcp`
  - [x] Проверить работоспособность entrypoints (`drom-mcp`, `ozon-mcp`, `avito-mcp`, `yandex-mcp`, `aliexpress-mcp`)
  - [x] Обновить схемы инструментов в `C:\Users\andrei\.gemini\antigravity-ide\mcp\` при изменении сигнатур
- [x] 5. Пуш изменений в GitHub форк:
  - [x] Настроить доступ к GitHub (добавить SSH-ключ или обновить scopes у PAT для workflow)
  - [x] Запушить изменения в `origin main`
  - [x] Проверить статус репозитория на GitHub
- [x] 6. Документирование результатов:
  - [x] Зафиксировать ревью в `tasks/todo.md`

## Ревью синхронизации с апстримом (v2.5.3)

1. **Слияние и разрешение конфликтов:**
   - Выполнено слияние коммитов ветки `upstream/main` в `main`.
   - Разрешены конфликты в `README.md`, `packages/compare-connector/pyproject.toml`, `packages/compare-connector/src/compare_connector/server.py`, `packages/marketplace-connector/tests/test_server.py`, `packages/marketplace-connector/tests/test_wire_frugality.py`, `uv.lock`.
   - `drom-connector` обновлен до версии `2.5.3`, синхронизирован с `mcp-core==2.5.3`, добавлен возврат `OfferBatch` в `compare_connector/server.py`.
   - В едином сервере смонтировано 44 инструмента (43 из 15 серверов + `marketplace_sources`).
   - Обновлен контракт дистрибьюции `scripts/test_distribution_contract.py` и список тестов в `pyproject.toml`.
   - Обновлен счетчик тестов до 2302 во всех 7 местах документации (`README.md`, `docs/ARCHITECTURE.md`).

2. **Верификация качества:**
   - `uv sync`: OK (118 пакетов разрешены, все локальные пакеты версии 2.5.3).
   - `uv run ruff check` & `uv run ruff format --check`: OK (357 файлов).
   - `uv run mypy`: OK (110 файлов, 0 ошибок).
   - `scripts/check_no_print.py`: OK (93 файла).
   - `scripts/check_versions.py`: OK (версия 2.5.3 в 88 местах).
   - `scripts/check_provenance.py`: OK (30 пинов).
   - `scripts/check_test_count.py`: OK (2302 теста).
   - `uv run pytest -q -m "not live and not cdp"`: OK (2199 passed, 103 skipped, 5 deselected).

3. **Локальный MCP-сервер (`C:\mcp\ru_marketplace-mcp`):**
   - Синхронизирован с веткой `main`.
   - Выполнен `uv sync` без ошибок.
   - Проверены entrypoints серверов (`drom-mcp`, `ozon-mcp`, `avito-mcp`, `yandex-mcp`, `aliexpress-mcp`, `marketplace-mcp`).
   - Схемы инструментов в `C:\Users\andrei\.gemini\antigravity-ide\mcp\` проверены и полностью совпадают.

4. **GitHub форк (`origin/main`):**
   - Коммит `32861c4` успешно запушен в `https://github.com/andrei-tolstov/ru-marketplace-mcp.git`.
   - Локальная и удаленная ветка `main` находятся в актуальном состоянии.
