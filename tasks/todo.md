# План: Исправление нестабильного теста в CI (Windows py3.12)

- [x] 1. Диагностика и локализация сбоя в CI <!-- id: 1 -->
  - [x] 1.1 Получить логи упавшего CI job `Tests (windows-latest, py3.12)` (job ID 129169899374) <!-- id: 1.1 -->
  - [x] 1.2 Локализовать причину сбоя: таймаут `_slow_wb` в `test_compare_prices_tool_timeout_budget_exhaustion` из-за неточного таймера сна на Windows CI runner <!-- id: 1.2 -->
- [x] 2. Рефакторинг тестов `compare-connector` <!-- id: 2 -->
  - [x] 2.1 Перевести `test_compare_prices_tool_timeout_budget_exhaustion` на детерминированные псевдо-часы `time.monotonic` без `asyncio.sleep` <!-- id: 2.1 -->
  - [x] 2.2 Перевести `test_compare_prices_runs_fast_sources_concurrently_and_cdp_sequentially` на синхронизацию через `asyncio.Event` и счётчик конкурентности <!-- id: 2.2 -->
- [x] 3. Локальная верификация <!-- id: 3 -->
  - [x] 3.1 Запустить тесты `test_server.py` многократно (stress-run) для подтверждения отсутствия флаков <!-- id: 3.1 -->
  - [x] 3.2 Прогнать все гейты качества (`ruff`, `mypy`, `check_test_count.py`, `check_no_print.py`, `check_versions.py`) <!-- id: 3.2 -->
  - [x] 3.3 Прогнать полный офлайн-сьют `pytest -q -m "not live and not cdp"` <!-- id: 3.3 -->
- [x] 4. Синхронизация, коммит и пуш в git <!-- id: 4 -->
  - [x] 4.1 Закоммитить изменения и запушить в `origin/main` (коммит `23e011c`) <!-- id: 4.1 -->
  - [x] 4.2 Синхронизировать с `C:\mcp\ru_marketplace-mcp` <!-- id: 4.2 -->
  - [x] 4.3 Дождаться прохождения всех проверок в GitHub Actions CI (run `42627297959` — 100% success) <!-- id: 4.3 -->

## Review & Results

- **Причина падения в CI (`windows-latest, py3.12`, run `42620154603`)**:
  - В тесте `test_compare_prices_tool_timeout_budget_exhaustion` использовался жесткий бюджет `TOOL_TIMEOUT_S = 0.08` и реальные задержки `asyncio.sleep(0.06)` для fast-источника `wildberries`.
  - На виртуальном Windows раннере в GitHub Actions системный таймер и планировщик потоков задержали выполнение `_slow_wb` более чем на 80 мс, из-за чего fast-источник непреднамеренно упал по таймауту вместо `'ok'`.
- **Элегантное решение без сна и флаков**:
  - `test_compare_prices_tool_timeout_budget_exhaustion`: переведён на детерминированные виртуальные часы `time.monotonic` через `monkeypatch`. Время продвигается строго детерминированно между вызовами, задержки `asyncio.sleep` устранены полностью.
  - `test_compare_prices_runs_fast_sources_concurrently_and_cdp_sequentially`: задержки `asyncio.sleep(0.05)` заменены на взаимную синхронизацию через `asyncio.Event` (`wb_started`, `ym_started`), что математически доказывает конкурентный старт обеих корутин без ожидания таймеров. Последовательность CDP доказана через явный счётчик активных задач (`max_cdp_concurrency == 1`).
- **Локальная верификация**:
  - 25 последовательных запусков стресс-теста: 100% успех.
  - `ruff check .` и `ruff format --check .`: чисто.
  - `mypy`: 121 файл проверен успешно.
  - Все скрипты гейтов качества (`check_no_print`, `check_provenance`, `check_lock_revision`, `check_versions`, `check_test_count`): зеленые.
  - Полный сьют `pytest -q -m "not live and not cdp"`: 3177 passed.
  - Сьют `pytest -q scripts`: 314 passed.
- **CI в GitHub Actions**:
  - Запущен run `42627297959` на коммите `23e011c`.
  - Все 11 джобов успешно пройдены:
    - `Lint and types`: success
    - `Tests (ubuntu-latest, py3.12 & py3.13)`: success
    - `Tests (windows-latest, py3.12 & py3.13)`: success
    - `Tests (macos-latest, py3.12 & py3.13)`: success
    - `Coverage (ubuntu, py3.12)`: success
    - `Server smoke test`: success
    - `dsh bundle installs and activates`: success
    - `PyPI bundle installs`: success
