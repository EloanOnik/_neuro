import asyncio
import re

from loguru import logger

from core.audio.output import AudioOutput
from core.tts.base import TTSEngine


class TTSPlayer:
    def __init__(self, engine: TTSEngine, output: AudioOutput, maxsize: int = 10):
        self.engine = engine
        self.output = output
        self.queue: asyncio.Queue[str] | None = None
        self._task: asyncio.Task | None = None
        self._started = False
        self._maxsize = maxsize

    async def start(self) -> None:
        if self._started:
            return
        await self.engine.load()
        if not self.output.find_vbcable_devices():
            raise RuntimeError("TTSPlayer: VB-Cable не найден")
        self.queue = asyncio.Queue(maxsize=self._maxsize)
        self._task = asyncio.create_task(self._process_queue())
        self._started = True
        logger.info(f"TTSPlayer: запущен (engine={self.engine.name})")

    async def stop(self) -> None:
        if not self._started:
            return
        self._started = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        if self.queue is not None:
            self._clear_queue()
            self.queue = None
        await self.engine.unload()
        logger.info("TTSPlayer: остановлен")

    async def speak(self, text: str) -> None:
        if self.queue is None or not self._started:
            raise RuntimeError("TTSPlayer: не запущен")

        # Не засоряем очередь пустыми кусками и одиночными эмодзи/знаками без букв и цифр
        if not text or not re.search(r"[а-яА-ЯёЁa-zA-Z0-9]", text):
            return

        await self.queue.put(text.strip())

    async def _process_queue(self) -> None:
        assert self.queue is not None
        while True:
            try:
                text = await self.queue.get()
                try:
                    await self.output.play(self.engine.synthesize(text))
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.exception(f"[TTS {self.engine.name}] Ошибка на тексте {text!r}: {e}")
                finally:
                    self.queue.task_done()
            except asyncio.CancelledError:
                break

    def _clear_queue(self) -> None:
        if self.queue is None:
            return
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
                self.queue.task_done()
            except asyncio.QueueEmpty:
                break