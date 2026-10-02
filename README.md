# 📄 CSV → HTML → PDF: Пайплайн генерации отчётов

CLI-скрипт на Python 3, который выполняет полный пайплайн:

```
генерация данных → шаблон → рендеринг → PDF → автооткрытие
```

## 📂 Структура проекта

```
.
├── main.py              # Главный скрипт
├── arial.ttf            # Unicode-шрифт для кириллицы в PDF
├── arialbd.ttf          # Жирное начертание Arial
├── data/                # Входные данные и шаблон
│   ├── products.csv     # CSV с товарами (генерируется)
│   └── template.html    # HTML-шаблон Jinja2 (генерируется)
├── output/              # Готовые PDF
│   └── products.pdf     # Сгенерированный отчёт
└── venv/                # Виртуальное окружение
```

## ⚙️ Установка

```bash
# Создать виртуальное окружение (рекомендуется)
python -m venv venv
.\venv\Scripts\activate   # Windows
source venv/bin/activate  # macOS / Linux

# Установить зависимости
pip install jinja2 fpdf2
```

## 🚀 Использование

### Инициализация проекта

Создаёт папки `/data`, `/output`, генерирует `products.csv` и `template.html`:

```bash
python main.py init
```

### Рендеринг PDF

Читает CSV, подставляет данные в HTML-шаблон (Jinja2), генерирует PDF через fpdf2:

```bash
python main.py render

# Без автооткрытия PDF
python main.py render --no-open
```

### Полный пайплайн

Init + render одной командой:

```bash
python main.py all

# Без автооткрытия
python main.py all --no-open
```

## 📋 Команды

| Команда | Описание |
|---|---|
| `python main.py init` | Создаёт `/data`, `products.csv`, `template.html` |
| `python main.py render` | CSV → HTML → PDF в `/output/products.pdf` |
| `python main.py render --no-open` | Рендеринг без автооткрытия PDF |
| `python main.py all` | Init + render |
| `python main.py all --no-open` | Init + render без автооткрытия |

## 📊 Формат CSV

Файл: `data/products.csv`

| product | price | qty |
|---|---|---|
| Ноутбук | 75000 | 3 |
| Беспроводная мышь | 2500 | 15 |
| Механическая клавиатура | 8900 | 7 |
| Монитор 27" 4K | 45500 | 2 |
| Веб-камера HD | 3200 | 10 |
| Наушники с шумоподавлением | 12000 | 5 |

Колонки: `product` (строка), `price` (число), `qty` (целое). Кодировка: UTF-8.

## 🎨 HTML-шаблон

Файл: `data/template.html`

- Плейсхолдеры Jinja2: `{% for row in rows %}` с полями `{{ row.product }}`, `{{ row.price }}`, `{{ row.qty }}`
- Мета-тег `<meta charset="UTF-8">` для поддержки кириллицы
- Стилизованная таблица: голубой заголовок (`#3498db`), чередование строк, границы
- Автоматическая подстановка даты через `{{ date }}`

## 🖨️ Генерация PDF

PDF создаётся библиотекой **fpdf2** (чистый Python, без системных зависимостей). Шрифт Arial скопирован из системы для корректного отображения кириллицы.

Выходной файл: `output/products.pdf` (~42 КБ для 6 товаров).

## 🔄 Автооткрытие PDF

Кроссплатформенное открытие файла после генерации:

| ОС | Механизм |
|---|---|
| Windows | `os.startfile()` |
| macOS | `subprocess.call(["open", ...])` |
| Linux | `subprocess.call(["xdg-open", ...])` |

Флаг `--no-open` отключает автооткрытие.

## 🧪 Пример вывода

```
> python main.py all --no-open
21:42:40 [INFO] === Запуск 'all' (init + render) ===
21:42:40 [INFO] Папка готова: ...\data
21:42:40 [INFO] Папка готова: ...\output
21:42:40 [INFO] CSV сгенерирован: ...\data\products.csv (6 строк)
21:42:40 [INFO] Шаблон сгенерирован: ...\data\template.html
21:42:40 [INFO] CSV прочитан: ...\data\products.csv (6 строк)
21:42:40 [INFO] HTML отрендерен (2251 символов)
21:42:41 [INFO] PDF сгенерирован: ...\output\products.pdf
21:42:41 [INFO] === Пайплайн завершён ===
```

## 🛠️ Требования

- Python 3.10+
- Библиотеки: `jinja2`, `fpdf2`

## 📝 Примечание

WeasyPrint (предпочтительная библиотека) требует системных библиотек GTK, которые отсутствуют на многих Windows-системах. В качестве замены используется **fpdf2** — лёгкая библиотека, не требующая внешних зависимостей и отлично работающая с кириллицей.