#!/usr/bin/env python3
"""
CLI-скрипт: генерация данных -> шаблон -> рендеринг -> PDF -> автооткрытие.

Команды:
    python main.py init        — создать /data, CSV и HTML-шаблон
    python main.py render      — прочитать CSV, отрендерить шаблон, сгенерировать PDF
    python main.py all         — выполнить init + render одной командой

Зависимости:
    pip install jinja2 fpdf2
"""

import argparse
import csv
import logging
import os
import platform
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import List, Dict

import jinja2
from fpdf import FPDF

# --- Конфигурация -----------------------------------------------------------

BASE_DIR: Path = Path(__file__).resolve().parent
DATA_DIR: Path = BASE_DIR / "data"
OUTPUT_DIR: Path = BASE_DIR / "output"

CSV_PATH: Path = DATA_DIR / "products.csv"
TEMPLATE_PATH: Path = DATA_DIR / "template.html"
PDF_PATH: Path = OUTPUT_DIR / "products.pdf"

# --- Логирование ------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)
# --- Вспомогательные функции -------------------------------------------------

def _create_directories() -> None:
    """Создать папки DATA_DIR и OUTPUT_DIR, если их нет."""
    for directory in (DATA_DIR, OUTPUT_DIR):
        directory.mkdir(parents=True, exist_ok=True)
        logger.info("Папка готова: %s", directory)


def _generate_csv(filepath: Path) -> None:
    """
    Сгенерировать CSV-файл с реалистичными товарами.

    Args:
        filepath: Путь для сохранения CSV-файла.
    """
    rows: List[Dict[str, str | int]] = [
        {"product": "Ноутбук", "price": 75000, "qty": 3},
        {"product": "Беспроводная мышь", "price": 2500, "qty": 15},
        {"product": "Механическая клавиатура", "price": 8900, "qty": 7},
        {"product": "Монитор 27\" 4K", "price": 45500, "qty": 2},
        {"product": "Веб-камера HD", "price": 3200, "qty": 10},
        {"product": "Наушники с шумоподавлением", "price": 12000, "qty": 5},
    ]

    with open(filepath, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["product", "price", "qty"])
        writer.writeheader()
        writer.writerows(rows)

    logger.info("CSV сгенерирован: %s (%d строк)", filepath, len(rows))
def _generate_template(filepath: Path) -> None:
    """
    Сгенерировать HTML-шаблон с поддержкой кириллицы и стилизацией.

    Args:
        filepath: Путь для сохранения шаблона.
    """
    template_html: str = r"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Товары - Отчёт</title>
    <style>
        @page { size: A4; margin: 20mm 15mm; }
        body { font-family: 'Segoe UI', Arial, 'Helvetica Neue', sans-serif; color: #333; }
        h1 { text-align: center; color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 12px; }
        table { width: 100%; border-collapse: collapse; font-size: 14px; }
        thead th { background: #3498db; color: #fff; padding: 12px 10px; text-align: left; }
        tbody td { padding: 10px; border-bottom: 1px solid #ddd; }
        tbody tr:nth-child(even) { background: #f8f9fa; }
        td.price, td.qty { text-align: right; }
        td.price::after { content: " \20BD"; color: #888; }
        .footer { text-align: center; color: #999; font-size: 11px; margin-top: 30px; }
    </style>
</head>
<body>
    <h1>Список товаров</h1>
    <table>
        <thead>
            <tr><th>Наименование</th><th>Цена</th><th>Количество</th></tr>
        </thead>
        <tbody>
        {% for row in rows %}
            <tr>
                <td>{{ row.product }}</td>
                <td class="price">{{ row.price }}</td>
                <td class="qty">{{ row.qty }}</td>
            </tr>
        {% endfor %}
        </tbody>
    </table>
    <div class="footer">Сгенерировано {{ date }}</div>
</body>
</html>"""

    with open(filepath, mode="w", encoding="utf-8") as f:
        f.write(template_html)

    logger.info("Шаблон сгенерирован: %s", filepath)
def _read_csv(filepath: Path) -> List[Dict[str, str]]:
    """
    Прочитать CSV-файл и вернуть список словарей.

    Args:
        filepath: Путь к CSV-файлу.

    Returns:
        Список строк в виде словарей {fieldname: value}.

    Raises:
        FileNotFoundError: Если файл не найден.
        csv.Error: Если файл повреждён или пуст.
    """
    if not filepath.exists():
        raise FileNotFoundError(
            f"CSV-файл не найден: {filepath}. "
            f"Выполните 'python main.py init' для генерации."
        )

    rows: List[Dict[str, str]] = []
    with open(filepath, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for line_no, row in enumerate(reader, start=2):
            for col in ("product", "price", "qty"):
                if col not in row or row[col] is None:
                    raise csv.Error(f"Строка {line_no}: отсутствует колонка '{col}'")
            rows.append(row)

    if not rows:
        raise csv.Error("CSV-файл не содержит строк данных (только заголовок).")

    logger.info("CSV прочитан: %s (%d строк)", filepath, len(rows))
    return rows
def _render_html(rows: List[Dict[str, str]], template_path: Path) -> str:
    """
    Отрендерить HTML с помощью Jinja2.

    Args:
        rows: Данные для подстановки.
        template_path: Путь к файлу шаблона.

    Returns:
        Готовая HTML-строка.

    Raises:
        FileNotFoundError: Если шаблон не найден.
        jinja2.TemplateNotFound: Если шаблон не найден.
        jinja2.TemplateError: При ошибке рендеринга.
    """
    if not template_path.exists():
        raise FileNotFoundError(
            f"Шаблон не найден: {template_path}. "
            f"Выполните 'python main.py init' для генерации."
        )

    loader = jinja2.FileSystemLoader(searchpath=str(template_path.parent))
    env = jinja2.Environment(loader=loader, autoescape=True)
    template = env.get_template(template_path.name)

    html_content: str = template.render(
        rows=rows,
        date=date.today().strftime("%d.%m.%Y"),
    )
    logger.info("HTML отрендерен (%d символов)", len(html_content))
    return html_content


class _ProductsPDF(FPDF):
    """Кастомный PDF-класс для генерации отчёта о товарах."""

    def __init__(self) -> None:
        """Инициализировать PDF и добавить Unicode-шрифт Arial с кириллицей."""
        super().__init__(orientation="P", unit="mm", format="A4")
        font_dir = Path(__file__).resolve().parent
        self.add_font("Arial", "", str(font_dir / "arial.ttf"))
        self.add_font("Arial", "B", str(font_dir / "arialbd.ttf"))

    def header(self) -> None:
        """Верхний колонтитул страницы."""
        if self.page_no() > 1:
            # Показывать заголовок только на страницах после первой
            return
        self.set_font("Arial", "B", 16)
        self.set_text_color(44, 62, 80)
        self.cell(0, 15, "Список товаров", align="C",
                  new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(52, 152, 219)
        self.set_line_width(0.8)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(8)

    def footer(self) -> None:
        """Нижний колонтитул страницы."""
        self.set_y(-15)
        self.set_font("Arial", "", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Страница {self.page_no()}/{{nb}}", align="C")


def _generate_pdf(rows: List[Dict[str, str]], output_path: Path) -> None:
    """
    Сгенерировать PDF-файл из данных CSV с помощью fpdf2.

    Args:
        rows: Данные для таблицы.
        output_path: Путь для сохранения PDF.

    Raises:
        RuntimeError: При ошибке генерации PDF.
    """
    try:
        pdf = _ProductsPDF()
        pdf.alias_nb_pages()
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.add_page()

        # Заголовки таблицы
        pdf.set_font("Arial", "B", 11)
        pdf.set_fill_color(52, 152, 219)
        pdf.set_text_color(255, 255, 255)

        col_widths = [90, 50, 40]
        headers = ["Наименование", "Цена (руб.)", "Количество"]

        for i, header in enumerate(headers):
            pdf.cell(col_widths[i], 12, header, border=1, align="C",
                     fill=True)
        pdf.ln()

        # Строки таблицы
        pdf.set_font("Arial", "", 10)
        pdf.set_text_color(51, 51, 51)

        for idx, row in enumerate(rows):
            # Чередование фона
            if idx % 2 == 0:
                pdf.set_fill_color(248, 249, 250)
            else:
                pdf.set_fill_color(255, 255, 255)

            try:
                price_val: int = int(row["price"])
                qty_val: int = int(row["qty"])
            except (ValueError, TypeError):
                price_val = 0
                qty_val = 0

            pdf.cell(col_widths[0], 10, str(row["product"]), border=1,
                     fill=True)
            pdf.cell(col_widths[1], 10, f"{price_val:,}".replace(",", " "),
                     border=1, align="R", fill=True)
            pdf.cell(col_widths[2], 10, str(qty_val),
                     border=1, align="R", fill=True)
            pdf.ln()

        # Итоговая строка
        total_price = sum(
            int(r["price"]) * int(r["qty"])
            for r in rows
            if r["price"].isdigit() and r["qty"].isdigit()
        )
        total_qty = sum(
            int(r["qty"]) for r in rows if r["qty"].isdigit()
        )

        pdf.ln(5)
        pdf.set_font("Arial", "B", 11)
        pdf.set_text_color(44, 62, 80)
        pdf.cell(col_widths[0], 10, "ИТОГО:", border="T")
        pdf.cell(col_widths[1], 10, f"{total_price:,} руб.".replace(",", " "),
                 border="T", align="R")
        pdf.cell(col_widths[2], 10, str(total_qty),
                 border="T", align="R")

        # Дата
        pdf.ln(15)
        pdf.set_font("Arial", "", 9)
        pdf.set_text_color(150, 150, 150)
        pdf.cell(0, 10, f"Сгенерировано {date.today().strftime('%d.%m.%Y')}",
                 align="C")

        pdf.output(str(output_path))
        logger.info("PDF сгенерирован: %s", output_path)

    except Exception as exc:
        raise RuntimeError(f"Ошибка генерации PDF: {exc}") from exc


def _open_file(filepath: Path) -> None:
    """
    Открыть файл в стандартной программе (кроссплатформенно).

    Args:
        filepath: Путь к файлу для открытия.
    """
    system: str = platform.system()
    try:
        if system == "Windows":
            os.startfile(str(filepath))
        elif system == "Darwin":
            subprocess.call(["open", str(filepath)])
        else:
            subprocess.call(["xdg-open", str(filepath)])
        logger.info("Файл открыт: %s", filepath)
    except Exception as exc:
        logger.warning("Не удалось открыть файл: %s. Ошибка: %s",
                       filepath, exc)
# --- Команды CLI ---------------------------------------------------------------

def cmd_init(args: argparse.Namespace) -> None:
    """
    Команда 'init': создать папки /data, /output, CSV и HTML-шаблон.

    Args:
        args: Аргументы командной строки (не используются).
    """
    _create_directories()

    if CSV_PATH.exists():
        logger.warning("CSV уже существует, будет перезаписан: %s", CSV_PATH)
    _generate_csv(CSV_PATH)

    if TEMPLATE_PATH.exists():
        logger.warning("Шаблон уже существует, будет перезаписан: %s", TEMPLATE_PATH)
    _generate_template(TEMPLATE_PATH)


def cmd_render(args: argparse.Namespace) -> None:
    """
    Команда 'render': прочитать CSV, отрендерить шаблон, сгенерировать PDF.

    Args:
        args: Аргументы командной строки. Используется args.open (bool).
    """
    rows: List[Dict[str, str]] = _read_csv(CSV_PATH)
    html_content: str = _render_html(rows, TEMPLATE_PATH)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    _generate_pdf(rows, PDF_PATH)

    if args.open:
        _open_file(PDF_PATH)


def cmd_all(args: argparse.Namespace) -> None:
    """
    Команда 'all': выполнить init, затем render.

    Args:
        args: Аргументы командной строки.
    """
    logger.info("=== Запуск 'all' (init + render) ===")

    init_args = argparse.Namespace()
    cmd_init(init_args)
    cmd_render(args)

    logger.info("=== Пайплайн завершён ===")
# --- CLI - настройка аргументов ----------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """
    Собрать парсер аргументов с субкомандами.

    Returns:
        Настроенный экземпляр ArgumentParser.
    """
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="Пайплайн: генерация данных -> шаблон -> HTML -> PDF -> автооткрытие",
        epilog="Пример: python main.py all",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init", help="Создать /data, CSV и HTML-шаблон")

    render_parser = subparsers.add_parser(
        "render", help="Прочитать CSV, отрендерить шаблон, сгенерировать PDF"
    )
    render_parser.add_argument(
        "--open",
        "--no-open",
        dest="open",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Автоматически открыть PDF после генерации (по умолч. True)",
    )

    all_parser = subparsers.add_parser(
        "all", help="Выполнить init + render одной командой"
    )
    all_parser.add_argument(
        "--open",
        "--no-open",
        dest="open",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Автоматически открыть PDF после генерации (по умолч. True)",
    )

    return parser


# --- Точка входа -------------------------------------------------------------

def main() -> None:
    """
    Главная точка входа: разобрать аргументы и выполнить команду.
    """
    parser = build_parser()
    args = parser.parse_args()

    command_handlers = {
        "init": cmd_init,
        "render": cmd_render,
        "all": cmd_all,
    }

    handler = command_handlers.get(args.command)
    if handler is None:
        parser.print_help()
        sys.exit(1)

    try:
        handler(args)
    except (FileNotFoundError, csv.Error, jinja2.TemplateError, RuntimeError) as exc:
        logger.error("Ошибка: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()