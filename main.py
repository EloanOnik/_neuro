import asyncio
import queue
import logging
import sys

from services.brain import Brain
from services.tts_player import TTSPlayer
from adapters.chat.twitch import TwitchChat
from datetime import datetime
from pathlib import Path


def setup_logger() -> logging.Logger:
    """Настраивает логгер: файл в папке с датой + вывод в консоль."""
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H-%M-%S")

    log_dir = Path("logs") / date_str
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / f"run_{time_str}.log"

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

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
        logger.error("Деление на ноль!", exc_info=True)
    logger.info("Работа завершена")


async def main():
    logger.info("Запуск main")


    tts = TTSPlayer()
    await tts.start()

    brain = Brain(tts_player=tts)
    try:
        await brain.start()
    except Exception:
        await tts.stop()
        raise

    chat = TwitchChat();  chat.start()

    while True:
        try:
            raw = await asyncio.to_thread(chat.message_queue.get, True, 2)
        except queue.Empty:
            continue

        if not raw or ":" not in raw:
            continue

        user_part, text = raw.split(":", 1)
        user = user_part.strip("[]")
        await brain.enqueue(user=user, text=text.strip(), meta={"source": "twitch"})

if __name__ == "__main__":
    asyncio.run(main())