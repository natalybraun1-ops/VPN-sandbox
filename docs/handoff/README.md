# Handoff для следующих веток разработки

Эта папка хранит короткие документы, которые нужно читать в новых ветках
диалога перед детализацией следующего этапа.

Рекомендуемый порядок чтения:

1. [Product Logic And Decisions](product-logic-and-decisions.md)
2. [Global Roadmap](global-roadmap.md)
3. [Подробная продуктовая спецификация](../superpowers/specs/2026-06-12-vpn-sandbox-design.md)
4. [План уже реализованного фундамента](../superpowers/plans/2026-06-12-vpn-sandbox-foundation.md)
5. [План уже реализованной PyQt6-оболочки](../superpowers/plans/2026-06-12-vpn-sandbox-pyqt-shell.md)

Текущее состояние кода:

- ветка: `codex/pyqt-shell`;
- техническое имя пакета: `vpn-sandbox`;
- реализовано: Python foundation + PyQt6 application shell;
- следующий этап: `Этап 2. Calibration And Detection`;
- проверка тестов: `$env:QT_QPA_PLATFORM = "offscreen"; python -m pytest -p no:cacheprovider --basetemp .pytest-tmp -q`;
- smoke-команда: `$env:PYTHONPATH = "src"; python -m vpn_sandbox doctor`.

Следующие диалоги не должны заново пересогласовывать базовую продуктовую
логику. Они должны выбрать один глобальный этап из roadmap и уже для него
составить детальный task-plan.
