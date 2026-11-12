import logging
import sys
from datetime import datetime
from pathlib import Path


def setup_logger() -> logging.Logger:
    """Настраивает логгер: файл в папке с датой + вывод в консоль."""
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")   # 2026-11-12
    time_str = now.strftime("%H-%M-%S")   # 14-30-05

    # Папка: logs/2026-11-12/  (создастся, если её нет; если есть — не упадёт)
    log_dir = Path("logs") / date_str
    log_dir.mkdir(parents=True, exist_ok=True)

    # Файл: logs/2026-11-12/run_14-30-05.log
    log_file = log_dir / f"run_{time_str}.log"

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    # Защита от дублирования обработчиков, если setup_logger вызовут повторно
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 1) Файл — пишем всё от DEBUG и выше
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # 2) Консоль — только INFO и выше, чтобы не засорять вывод
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logger.info("Логирование настроено. Файл: %s", log_file)
    return logger


logger = setup_logger()


def do_work():
    logger.debug("Начинаем обработку (видно только в файле)")
    logger.info("Обработка запущена")
    logger.warning("Что-то подозрительное, но работаем дальше")
    try:
        1 / 0
    except ZeroDivisionError:
        logger.error("Деление на ноль!", exc_info=True)  # exc_info=True → сохранит стектрейс
    logger.info("Работа завершена")


if __name__ == "__main__":
    do_work()