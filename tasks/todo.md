# План: Последовательный вызов CDP-источников и увеличение таймаута в compare_prices

- [ ] 1. Исследование и проектирование архитектуры <!-- id: 1 -->
  - [x] 1.1 Определить критерий отнесения источников к CDP / fast-источникам (через `mcp_core.sources`) <!-- id: 1.1 -->
  - [x] 1.2 Спроектировать схему таймаутов (per-source timeout `COMPARE_SOURCE_TIMEOUT` и tool-level timeout `COMPARE_TOOL_TIMEOUT`) <!-- id: 1.2 -->
  - [x] 1.3 Подготовить детальный Implementation Plan артефакт и согласовать с пользователем <!-- id: 1.3 -->
- [x] 2. Реализация в `mcp-core` и `compare-connector` <!-- id: 2 -->
  - [x] 2.1 В `packages/mcp-core/src/mcp_core/sources.py`: добавить предикат `is_cdp_source` (с учётом DOM-режима Wildberries) <!-- id: 2.1 -->
  - [x] 2.2 В `packages/compare-connector/src/compare_connector/server.py`: обновить `_run_source` для приёма индивидуального `timeout` <!-- id: 2.2 -->
  - [x] 2.3 В `compare_prices`: разделить `active` на быстрые (без CDP) и CDP-источники; быстрые запускать через `asyncio.gather`, CDP — строго последовательно <!-- id: 2.3 -->
  - [x] 2.4 В `compare_prices`: реализовать учёт общего бюджета времени (`COMPARE_TOOL_TIMEOUT`, по умолчанию 450с) с корректной фиксацией таймаутов при исчерпании бюджета <!-- id: 2.4 -->
  - [x] 2.5 В `compare_sources`: экспортировать информацию об общем таймауте инструмента (`tool_timeout_s`) <!-- id: 2.5 -->
- [x] 3. Обновление документации и скиллов <!-- id: 3 -->
  - [x] 3.1 Обновить `skills/compare-prices/SKILL.md` и `dsh/skills/compare-prices/SKILL.md` <!-- id: 3.1 -->
  - [x] 3.2 Обновить `skills/marketplace/SKILL.md` и `dsh/skills/marketplace/SKILL.md` <!-- id: 3.2 -->
  - [x] 3.3 Обновить `docs/CDP_SETUP.md` с описанием `COMPARE_TOOL_TIMEOUT` <!-- id: 3.3 -->
- [x] 4. Тестирование и верификация <!-- id: 4 -->
  - [x] 4.1 Добавить тесты на параллельность fast-источников и последовательность CDP-источников в `packages/compare-connector/tests/test_server.py` <!-- id: 4.1 -->
  - [x] 4.2 Добавить тест на исчерпание бюджета `COMPARE_TOOL_TIMEOUT` <!-- id: 4.2 -->
  - [x] 4.3 Прогнать весь тестовый набор `packages/compare-connector/tests` <!-- id: 4.3 -->
  - [x] 4.4 Запустить линтер `ruff` и проверку типов `mypy` <!-- id: 4.4 -->

## Review & Results

- **Двухфазное исполнение `compare_prices`**:
  - В `mcp_core.sources` добавлен предикат `is_cdp_source` и набор `BROWSER_ACCESS_TIERS`.
  - В `compare_connector.server`:
    - Быстрые HTTP-источники (`wildberries` в API режиме, `yandex_market`) запускаются параллельно через `asyncio.gather`.
    - Все CDP-источники (`ozon`, `avito`, `taobao`, `megamarket`, `lamoda`, `dns`, `citilink`, `aliexpress`, `drom`, а также `wildberries` в DOM-режиме) запускаются строго последовательно.
    - Исходный детерминированный порядок вывода (`source_outcomes` и `offers`) сохраняется согласно списку `active`.
- **Управление таймаутами**:
  - Добавлена переменная окружения `COMPARE_TOOL_TIMEOUT` (по умолчанию 450 секунд, `TOOL_TIMEOUT_S = max(COMPARE_TOOL_TIMEOUT, SOURCE_TIMEOUT_S)`).
  - В последовательном цикле CDP проверяется оставшийся дедлайн: если бюджет времени исчерпан, последующие источники получают честный статус `timeout` (`"tool timeout budget (...) exceeded"`), а уже полученные результаты сохраняются и возвращаются пользователю.
  - В `compare_sources` экспортируется `"tool_timeout_s": TOOL_TIMEOUT_S`, документация и контракты в `mcp_core.resources` обновлены.
- **Документация и скиллы**:
  - Обновлены `skills/compare-prices/SKILL.md`, `dsh/skills/compare-prices/SKILL.md`, `skills/marketplace/SKILL.md`, `dsh/skills/marketplace/SKILL.md` и `docs/CDP_SETUP.md`.
  - Счётчик тестов в документации (`README.md`, `docs/ARCHITECTURE.md`) обновлён до 3288.
- **Верификация**:
  - `check_test_count.py`: согласуется во всех 7 местах (3288).
  - `ruff check .` и `ruff format --check .`: без замечаний.
  - `mypy`: 121 файл проверен успешно (включая кроссплатформенные проверки `win32`, `darwin`, `linux`).
  - Все гейты качества (`check_no_print.py`, `check_provenance.py`, `check_lock_revision.py`, `check_versions.py`): зеленые.
  - `pytest packages/compare-connector/tests`: 377 passed.
  - Полный офлайн-сьют `pytest -q -m "not live and not cdp"`: 3177 passed, 111 skipped, 0 failed.
