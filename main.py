import asyncio
import queue
import sys
from datetime import datetime
from pathlib import Path

from loguru import logger

from services.brain import Brain
from services.tts_player import TTSPlayer
from adapters.chat.twitch import TwitchChat


def setup_loguru() -> None:
    """Настраивает Loguru: файл в папке с датой + отдельный файл на запуск + консоль."""
    logger.remove()

    logger.add(
        sys.stderr,
        level="INFO",
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan> - <level>{message}</level>"
        ),
    )

    now = datetime.now()
    log_dir = Path("logs") / now.strftime("%Y-%m-%d")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"run_{now.strftime('%H-%M-%S')}.log"

    logger.add(
        log_file,
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name} - {message}",
        encoding="utf-8",
    )

    logger.info(f"Логирование настроено. Файл: {log_file}")


async def _shutdown(tts: TTSPlayer, brain: Brain, chat: TwitchChat) -> None:
    logger.info("Shutdown: останавливаю сервисы")

    # 1. Brain.stop() — отменяет _process_queue, выгружает модель, закрывает клиент
    try:
        await brain.stop()
        logger.info("Brain: остановлен")
    except Exception:
        logger.exception("Brain: ошибка при остановке")

    # 2. TTS
    try:
        await tts.stop()
        logger.info("TTS: остановлен")
    except Exception:
        logger.exception("TTS: ошибка при остановке")

    # 3. Чат
    try:
        if hasattr(chat, "stop"):
            chat.stop()
            logger.info("TwitchChat: остановлен")
    except Exception:
        logger.exception("TwitchChat: ошибка при остановке")

    logger.info("Shutdown завершён")


async def main() -> None:
    setup_loguru()
    logger.info("Запуск main")

    tts = TTSPlayer()
    await tts.start()
    logger.info("TTSPlayer запущен")

    brain = Brain(tts_player=tts)
    try:
        await brain.start()
    except Exception:
        logger.exception("Brain не запустился — останавливаю TTS")
        await tts.stop()
        raise
    logger.info("Brain запущен")

    chat = TwitchChat()
    chat.start()
    logger.info("TwitchChat подключён, слушаю")

    try:
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
            text = text.strip()
            logger.debug(f"Сообщение от {user}: {text!r}")

            try:
                await brain.enqueue(user=user, text=text, meta={"source": "twitch"})
            except Exception:
                logger.exception(f"Не удалось обработать сообщение от {user}")

    finally:
        await _shutdown(tts, brain, chat)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Сюда попадаем после того, как finally в main() уже выполнил cleanup.
        # Подавляем трейсбек — пользователь и так знает, что нажал Ctrl+C.
        pass