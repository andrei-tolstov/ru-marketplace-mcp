# Задачи: Синхронизация форка с upstream v2.8.2 с сохранением drom-connector

- [x] 1. Подготовка и создание резервной копии:
  - [x] Зафиксировать резервную ветку `backup-main-before-v2.8.2` на текущем коммите `HEAD` (f0f48ca)
  - [x] Убедиться в чистоте рабочего дерева перед слиянием
- [x] 2. Слияние ветки upstream/main:
  - [x] Выполнить `git merge --no-commit upstream/main`
  - [x] Разрешить конфликты в `packages/marketplace-connector/src/marketplace_connector/server.py`
  - [x] Разрешить конфликты в `packages/compare-connector/src/compare_connector/server.py`
  - [x] Разрешить конфликты в `packages/marketplace-connector/tests/test_server.py`
  - [x] Разрешить конфликты в `packages/marketplace-connector/tests/test_wire_frugality.py`
  - [x] Разрешить конфликты в `README.md` и `docs/ARCHITECTURE.md`
  - [x] Разрешить конфликт в `uv.lock` через чистый пересчет `uv lock` (revision = 5)
- [x] 3. Архитектурная гармонизация drom-connector с v2.8.2:
  - [x] Добавить `SourceSpec` для `drom` в `packages/mcp-core/src/mcp_core/sources.py`
  - [x] Добавить запись `drom-mcp` в `server.json`
  - [x] Обновить версию `drom-connector` до `2.8.2` в `pyproject.toml`, `__init__.py`, `server.py`
  - [x] Обновить пин `mcp-core==2.8.2` в `packages/drom-connector/pyproject.toml`
  - [x] Добавить guides для `drom_*` и `_NATIVE_OUTPUT_FIELDS` для `drom_card_photos` в `packages/mcp-core/src/mcp_core/resources.py`
  - [x] Вызвать `register_reference_resources(mcp)` в `packages/drom-connector/src/drom_connector/server.py`
  - [x] Сгенерировать .provenance.json для фикстур drom
  - [x] Перегенерировать снимок публичного контракта `packages/marketplace-connector/tests/fixtures/public_contract.json`
  - [x] Перегенерировать справочник инструментов `docs/TOOLS.md` скриптом `scripts/gen_tools_doc.py`
  - [x] Актуализировать счетчик офлайн-тестов во всех 7 местах документации через `scripts/check_test_count.py` (3280)
- [x] 4. Комплексная верификация качества:
  - [x] Проверить `uv lock --check` и выполнить `uv sync --all-packages`
  - [x] Запустить `uv run ruff check .` (All checks passed!) и `uv run ruff format --check .` (452 files already formatted)
  - [x] Запустить `uv run mypy` (Success: no issues found in 121 source files на win32 и darwin)
  - [x] Запустить `uv run python scripts/check_no_print.py` (104 files checked: no stdout writes)
  - [x] Запустить `uv run python scripts/check_versions.py 2.8.2` (92 places agreed)
  - [x] Запустить `uv run python scripts/check_provenance.py` (36 pins in 44 sidecars: ok)
  - [x] Запустить `uv run python scripts/check_test_count.py` (7 places agree: 3280)
  - [x] Запустить `uv run python scripts/gen_tools_doc.py --check`
  - [x] Запустить тесты `packages/drom-connector/tests` (27 passed)
  - [x] Запустить тесты паритета реестра `packages/marketplace-connector/tests/test_source_registry_parity.py` (9 passed)
  - [x] Запустить тесты контрактов гайдов `packages/mcp-core/tests/test_guide_contracts.py` (54 passed)
  - [x] Запустить тесты `packages/marketplace-connector/tests` и `packages/compare-connector/tests` (833 passed)
  - [x] Запустить полный набор офлайн-тестов `uv run pytest -q -m "not live and not cdp"` (3169 passed, 111 skipped, 5 deselected, 0 failed)
- [x] 5. Фиксация коммита и синхронизация рабочего MCP сервера:
  - [x] Закоммитить слияние `Merge upstream/main into main (v2.8.2 sync with drom-connector integration)` (`a57e663`)
  - [x] Синхронизировать рабочую копию `C:\mcp\ru_marketplace-mcp` (ветка `main` подтянута к `a57e663`)
  - [x] Запушить изменения в GitHub форк `origin main`
- [x] 6. Документирование результатов:
  - [x] Зафиксировать результаты и метрики синхронизации в `tasks/todo.md`

---

## Review & Validation Metrics

1. **Коммит слияния**: `a57e663` ("Merge upstream/main into main (v2.8.2 sync with drom-connector integration)").
2. **Ветки**:
   - `backup-main-before-v2.8.2` указывает на исходное состояние до слияния (`f0f48ca`).
   - `main` указывает на `a57e663` и синхронизирована с `origin/main`.
   - `C:\mcp\ru_marketplace-mcp` (рабочая копия MCP) синхронизирована с `main` (`a57e663`).
3. **Статические проверки**:
   - `uv lock --check`: Resolved 116 packages, lockfile в актуальном состоянии.
   - `uv run ruff check .`: 0 issues (All checks passed!).
   - `uv run ruff format --check .`: 452 files already formatted.
   - `uv run mypy`: Success: no issues found in 121 source files (проверено для win32 и darwin).
   - `scripts/check_no_print.py`: 104 files checked, 0 stdout writes.
4. **Релизные гейты upstream v2.8.2**:
   - `scripts/check_versions.py 2.8.2`: согласовано в 92 местах.
   - `scripts/check_provenance.py`: проверено 36 пинов в 44 sidecar-файлах (.provenance.json).
   - `scripts/check_lock_revision.py`: revision 5 (floor 5).
   - `scripts/check_test_count.py`: согласовано в 7 местах (3280 офлайн-тестов).
   - `scripts/gen_tools_doc.py --check`: актуальны `docs/TOOLS.md`, `README.md`, `dsh/README.md`.
5. **Тестирование**:
   - Контракты гайдов (`test_guide_contracts.py`): 54 passed.
   - Паритет реестра источников (`test_source_registry_parity.py`): 9 passed.
   - Модульные тесты drom (`drom-connector/tests`): 27 passed.
   - Тесты маркетплейса и сравнения цен (`marketplace-connector` + `compare-connector`): 833 passed, 1 skipped.
   - Полный офлайн-прогон: `3169 passed, 111 skipped, 5 deselected, 0 failed` за 190.26s.
6. **Сохраненные пользовательские возможности**:
   - Коннектор `drom-connector` (4 инструмента: `drom_search`, `drom_card`, `drom_card_photos`, `drom_seller`).
   - Инспекция фотографий запчастей с регламентом анализа (`drom_card_photos`).
   - Интеграция Drom в `compare_prices` (поиск по автозапчастям, маслам, шинам) и единый `marketplace-connector` (43 инструмента).
   - Полная совместимость с новой архитектурой v2.8.2 (ресурсы `guide://drom/*`, `serialize_by_alias=True`, `_NATIVE_OUTPUT_FIELDS`, `SourceSpec` в `mcp_core.sources.py`).
