import asyncio
from contextlib import aclosing
from loguru import logger

from core.audio.output import AudioOutput
from core.tts.base import TTSEngine


# Еще раз перепроверить на баги


class TTSPlayer:
    def __init__(self, engine: TTSEngine, output: AudioOutput, maxsize: int = 10):
        self.engine = engine
        self.output = output
        self.queue: asyncio.Queue[str] | None = None
        self._task: asyncio.Task | None = None
        self._started = False
        self._maxsize = maxsize
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        async with self._lock:
            if self._started:
                return
            # Сначала проверяем устройство, потом грузим тяжелую модель
            if not self.output.find_vbcable_devices():
                raise RuntimeError("TTSPlayer: VB-Cable не найден")
            
            await self.engine.load()
            try:
                self.queue = asyncio.Queue(maxsize=self._maxsize)
                self._task = asyncio.create_task(self._process_queue())
                self._started = True
                logger.info(f"TTSPlayer: запущен (engine={self.engine.name})")
            except Exception:
                await self.engine.unload()
                raise

    async def stop(self) -> None:
        async with self._lock:
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

        if not text or not any(ch.isalnum() for ch in text):
            return

        await self.queue.put(text.strip())

    async def wait_until_done(self) -> None:
        """Дождаться озвучивания всех фраз в очереди."""
        if self.queue is not None:
            await self.queue.join()

    async def _process_queue(self) -> None:
        assert self.queue is not None
        while True:
            text = await self.queue.get()
            try:
                # Если synthesize возвращает AsyncGenerator, aclosing гарантирует его закрытие при отмене
                stream = self.engine.synthesize(text)
                if hasattr(stream, "__aiter__"):
                    async with aclosing(stream) as safe_stream:
                        await self.output.play(safe_stream)
                else:
                    await self.output.play(stream)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"[TTS {self.engine.name}] Ошибка на тексте {text!r}: {e}")
            finally:
                self.queue.task_done()

    def _clear_queue(self) -> None:
        if self.queue is None:
            return
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
                self.queue.task_done()
            except asyncio.QueueEmpty:
                break