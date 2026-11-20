import asyncio
import inspect
import queue
import sys
from datetime import datetime
from pathlib import Path


from dotenv import load_dotenv


from loguru import logger

from act.adapters.chat.twitch import TwitchChat
from act.core.audio.output import AudioOutput
from act.core.tts.config import TTSConfig
from act.core.tts.registry import create_engine
from act.services.brain import Brain
from act.services.tts_player import TTSPlayer
from act.filter.filter_twitch_chat import FilterTwitchChat

# src/act/main.py -> parents[0]=src/act, parents[1]=src, parents[2]=корень проекта
PROJECT_ROOT = Path(__file__).resolve().parents[2]


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
    log_dir = PROJECT_ROOT / "logs" / now.strftime("%Y-%m-%d")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"run_{now.strftime('%H-%M-%S')}.log"

    logger.add(
        log_file,
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name} - {message}",
        encoding="utf-8",
    )

    logger.info(f"Логирование настроено. Файл: {log_file}")


async def _maybe_await(value) -> None:
    """Ждёт результат, если это awaitable; иначе ничего не делает."""
    if inspect.isawaitable(value):
        await value


async def _shutdown(
    tts: TTSPlayer | None,
    brain: Brain | None,
    chat: TwitchChat | None,
) -> None:
    logger.info("Shutdown: останавливаю сервисы")

    if brain is not None:
        try:
            await brain.stop()
            logger.info("Brain: остановлен")
        except Exception:
            logger.exception("Brain: ошибка при остановке")

    if tts is not None:
        try:
            await tts.stop()
            logger.info("TTS: остановлен")
        except Exception:
            logger.exception("TTS: ошибка при остановке")

    if chat is not None and hasattr(chat, "stop"):
        try:
            await _maybe_await(chat.stop())
            logger.info("TwitchChat: остановлен")
        except Exception:
            logger.exception("TwitchChat: ошибка при остановке")

    logger.info("Shutdown завершён")


def _build_engine(cfg: TTSConfig):
    engine = create_engine(cfg.engine, **cfg.engine_kwargs(cfg.engine))
    logger.info(f"TTS: выбран движок '{cfg.engine}'")
    return engine


async def _async_main() -> None:
    load_dotenv()
    setup_loguru()
    logger.info("Запуск main")

    tts: TTSPlayer | None = None
    brain: Brain | None = None
    chat: TwitchChat | None = None
    chat_filter: FilterTwitchChat | None = None

    try:
        cfg = TTSConfig.load(PROJECT_ROOT / "config" / "tts.yaml")
        engine = _build_engine(cfg)

        output = AudioOutput(
            target_sr=cfg.audio.get("target_sr", 48000),
            target_ch=cfg.audio.get("target_ch", 2),
            device_index=cfg.audio.get("device_index"),
        )

        tts = TTSPlayer(engine=engine, output=output)
        await tts.start()
        logger.info(f"TTSPlayer запущен (engine={engine.name})")

        brain = Brain(tts_player=tts)
        await brain.start()
        logger.info("Brain запущен")

        chat = TwitchChat()
        chat.start()
        logger.info("TwitchChat подключён, слушаю")

        chat_filter = FilterTwitchChat(banned_words=[])

        while True:
            try:
                raw = await asyncio.to_thread(chat.message_queue.get, True, 2)
            except queue.Empty:
                continue

            msg = chat_filter.filter_one(raw)
            if msg is None:
                logger.debug(f"Пропущено невалидное сообщение: {raw!r}")
                continue

            logger.debug(f"Сообщение от {msg.user}: {msg.text!r}")

            try:
                brain.enqueue(user=msg.user, text=msg.text, meta={"source": "twitch"})
            except Exception:
                logger.exception(f"Не удалось обработать сообщение от {msg.user}")

            # user, text = msg
            # logger.debug(f"Сообщение от {user}: {text!r}")

            # try:
            #     brain.enqueue(user=user, text=text, meta={"source": "twitch"})
            # except Exception:
            #     logger.exception(f"Не удалось обработать сообщение от {user}")

    finally:
        await _shutdown(tts, brain, chat)


def main() -> None:
    """Синхронная точка входа для pyproject.toml (`act = 'act.main:main'`)."""
    try:
        asyncio.run(_async_main())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()