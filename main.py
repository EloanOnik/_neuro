import asyncio
import queue
import sys
from datetime import datetime
from pathlib import Path

from loguru import logger  # ← вместо import logging

from services.brain import Brain
from services.tts_player import TTSPlayer
from adapters.chat.twitch import TwitchChat


def setup_loguru():
    """Настраивает Loguru: файл в папке с датой + консоль."""
    # 1. Убираем дефолтный обработчик, чтобы не было дублей в консоли
    logger.remove()

    # 2. Настраиваем консольный вывод (цветной, в stderr)
    logger.add(
        sys.stderr,
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>",
    )

    # 3. Настраиваем файловый вывод
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H-%M-%S")

    log_dir = Path("logs") / date_str
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"run_{time_str}.log"

    logger.add(
        log_file,
        level="DEBUG",  # В файл пишем всё
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name} - {message}",
        encoding="utf-8",  # Важно для Windows и кириллицы
    )

    logger.info(f"Логирование настроено. Файл: {log_file}")


async def main():
    setup_loguru()  # Настройка теперь внутри main, а не на уровне модуля
    logger.info("Запуск main")

    tts = TTSPlayer()
    await tts.start()

    brain = Brain(tts_player=tts)
    try:
        await brain.start()
    except Exception:
        logger.exception("Brain не запустился — останавливаю TTS")  # ← Автоматически со стектрейсом
        await tts.stop()
        raise

    chat = TwitchChat()
    chat.start()
    logger.info("TwitchChat подключён, слушаю")

    while True:
        try:
            raw = await asyncio.to_thread(chat.message_queue.get, True, 2)
        except queue.Empty:
            continue

        if not raw or ":" not in raw:
            logger.debug(f"Пропущено невалидное сообщение: {raw!r}")
            continue

        user_part, text = raw.split(":", 1)
        user = user_part.strip("[]")
        await brain.enqueue(user=user, text=text.strip(), meta={"source": "twitch"})


if __name__ == "__main__":
    asyncio.run(main())