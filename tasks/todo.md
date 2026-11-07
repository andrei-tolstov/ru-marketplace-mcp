# План выполнения: исправление drom-connector, обновление скиллов CDP и починка CI

- [x] 1. Исправить интеграцию Drom в compare-connector и identity <!-- id: 1 -->
  - [x] 1.1 `_search_drom`: заменить `item.bulletin_id` на `item.item_id` в `packages/compare-connector/src/compare_connector/server.py` <!-- id: 1.1 -->
  - [x] 1.2 `_call_card_tool`: добавить `"drom": "url_or_id"` в `packages/compare-connector/src/compare_connector/server.py` <!-- id: 1.2 -->
  - [x] 1.3 `compare_sources`: добавить описание Drom в словарь `notes` <!-- id: 1.3 -->
  - [x] 1.4 `identity.py`: добавить `"oem"` в `_field(raw, "mpn", ...)` <!-- id: 1.4 -->
  - [x] 1.5 Добавить юнит-тесты на `_search_drom` и `_call_card_tool` в `packages/compare-connector/tests/` <!-- id: 1.5 -->
- [x] 2. Исправить баги и обработку ошибок в drom-connector <!-- id: 2 -->
  - [x] 2.1 `_ITEM_ID_RE`: поддержать `/bulletin/<id>.html` и канонические URL со слешем <!-- id: 2.1 -->
  - [x] 2.2 `_cdp_fetch` и `_fetch`: обернуть `fetch` в `try/catch` в JS, пробрасывать `ToolError` (R-CDP-HOST-PAUSE), сохранять причину таймаута в `TransportDownError` <!-- id: 2.2 -->
  - [x] 2.3 `drom_card_photos`: добавить `"item_id"` в `structured_content` <!-- id: 2.3 -->
  - [x] 2.4 Добавить/обновить тесты в `packages/drom-connector/tests/test_server.py` <!-- id: 2.4 -->
- [x] 3. Обновить скиллы по поочередному вызову CDP-источников (`skills/` и `dsh/skills/`) <!-- id: 3 -->
  - [x] 3.1 Обновить `skills/compare-prices/SKILL.md` и зеркало в `dsh/skills/` <!-- id: 3.1 -->
  - [x] 3.2 Обновить `skills/marketplace/SKILL.md` и зеркало в `dsh/skills/` <!-- id: 3.2 -->
  - [x] 3.3 Обновить `skills/drom-connector/SKILL.md` (сигнатуры и CDP) и зеркало в `dsh/skills/` <!-- id: 3.3 -->
  - [x] 3.4 Проверить соответствие через `uv run pytest packages/marketplace-connector/tests/test_dsh_bundle.py` <!-- id: 3.4 -->
- [x] 4. Починить тесты GitHub Actions CI <!-- id: 4 -->
  - [x] 4.1 Обновить `.github/workflows/ci.yml`: шаг `dsh bundle` (`test "$skills" -eq 16`) <!-- id: 4.1 -->
  - [x] 4.2 Пересчитать baseline токенов в `work/performance/wire-baseline.json` для 42 тулов (`marketplace-mcp`) и обновить ceiling <!-- id: 4.2 -->
  - [x] 4.3 Проверить `scripts/mcp_wire.py` и `scripts/test_mcp_wire_budgets.py` <!-- id: 4.3 -->
- [ ] 5. Полная верификация, коммит, пуш и синхронизация <!-- id: 5 -->
  - [x] 5.1 Проверить `scripts/check_test_count.py` (при необходимости обновить README.md/docs) <!-- id: 5.1 -->
  - [x] 5.2 Прогнать линтеры, тайпчекер и полный офлайн-набор тестов (`uv run pytest -q -m "not live and not cdp"`) <!-- id: 5.2 -->
  - [ ] 5.3 Закоммитить изменения и запушить в `origin/main` <!-- id: 5.3 -->
  - [ ] 5.4 Синхронизировать `C:\mcp\ru_marketplace-mcp` <!-- id: 5.4 -->

## Review & Results

- **Drom Connector & Compare Integration**:
  - `_search_drom` теперь читает `item.item_id`, что предотвращает ошибку `'DromSearchItemOut' object has no attribute 'bulletin_id'`.
  - `_call_card_tool` теперь содержит ключ `"drom": "url_or_id"`, предотвращая `KeyError` при верификации офферов Drom в `compare_verify_offer` и `decision_inspect`.
  - `identity_from_mapping` распознает каталожный номер `oem` (Drom) как `mpn`.
  - Регулярное выражение `_ITEM_ID_RE` и `_extract_item_id` теперь корректно парсят канонические URL со слешем `/bulletin/<id>.html`.
  - `_cdp_fetch` защищен `try/catch` в JavaScript-коде, а сообщения об ошибках в `drom_search`, `drom_card`, `drom_seller` сохраняют детали ошибки и таймаута (например, `CDP timeout after 20.0s`).
  - В `structured_content` инструмента `drom_card_photos` добавлены поля `item_id` и `bulletin_id`, что соответствует контракту ресурсов (`_NATIVE_OUTPUT_FIELDS`).
- **Skills (CDP Serialization)**:
  - В `skills/compare-prices/SKILL.md`, `skills/marketplace/SKILL.md` и `skills/drom-connector/SKILL.md` (а также синхронно в `dsh/skills/`) добавлены правила последовательного опроса CDP-источников во избежание насыщения пула вкладок браузера (`CHROME_CDP_MAX_NAVIGATIONS=3`) и ложных таймаутов.
- **GitHub Actions CI Fixes**:
  - `.github/workflows/ci.yml`: шаг `dsh bundle` обновлен до `test "$skills" -eq 16`.
  - `work/performance/wire-baseline.json`: baseline пересчитан для 42 тулов `marketplace-mcp`, потолок токенов обновлен до 15394.
- **Verification Evidence**:
  - `check_test_count.py`: 3285 тестов во всех 7 местах в `README.md` и `docs/ARCHITECTURE.md`.
  - `ruff check .` и `ruff format --check .`: успешно, код полностью отформатирован.
  - `mypy`: без ошибок на платформах win32, darwin, linux.
  - `scripts/check_no_print.py`, `check_provenance.py`, `check_lock_revision.py`, `check_versions.py`: все 4 гейта зеленые.
  - `pytest -q scripts`: 314 passed.
  - `scripts/e2e_stdio_check.py`: 34/34 сессий успешно завершены.
  - `pytest -q -m "not live and not cdp"`: 3174 passed, 111 skipped, 0 failed (всего 3285 офлайн-тестов).
