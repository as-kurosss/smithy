# Smithy

Python RPA engine — робот-исполнитель, Windows UIA инструменты, оркестратор и HTTP-сервер.

## Установка

```bash
pip install -e ".[dev]"
```

## Разработка

```bash
pytest                    # запуск тестов
ruff check src/ tests/    # линтер
mypy src/                 # типизация
```

## Структура

```
src/smithy/
├── core/         — Tool ABC, ExecutionContext, ToolRegistry, ошибки
├── engine/       — Robot/Step модели, интерполяция, исполнитель, HTTP-инструмент
├── windows/      — UIA инструменты (click, find, process и т.д.)
├── orchestrator/ — Менеджер запусков, отладка
├── server/       — FastAPI REST API (мост Tauri ↔ Python)
└── cli/          — CLI: validate / run
```
