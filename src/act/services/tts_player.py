import asyncio
import inspect
from contextlib import aclosing
from loguru import logger

from act.core.audio.output import AudioOutput
from act.core.tts.base import TTSEngine


class TTSPlayer:
    def __init__(
        self,
        engine: TTSEngine,
        output: AudioOutput,
        maxsize: int = 10,
        sentence_pause: float = 0.3,
    ):
        self.engine = engine
        self.output = output
        self.sentence_pause = sentence_pause
        self.queue: asyncio.Queue[str] | None = None
        self._task: asyncio.Task | None = None
        self._started = False
        self._maxsize = maxsize
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        async with self._lock:
            if self._started:
                return
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
        q = self.queue
        if q is None or not self._started:
            raise RuntimeError("TTSPlayer: не запущен")

        if not text or not any(ch.isalnum() for ch in text):
            return

        await q.put(text.strip())

    async def wait_until_done(self) -> None:
        """Дождаться озвучивания всех фраз в очереди."""
        q = self.queue
        if q is not None and self._started:
            await q.join()

    async def _process_queue(self) -> None:
        q = self.queue
        assert q is not None
        while True:
            text = await q.get()
            try:
                stream = self.engine.synthesize(text)
                if inspect.isawaitable(stream):
                    stream = await stream

                if hasattr(stream, "__aiter__"):
                    async with aclosing(stream) as safe_stream:
                        await self.output.play(safe_stream)
                else:
                    await self.output.play(stream)

                # Небольшая естественная пауза между фразами, если в очереди есть ещё текст
                if self.sentence_pause > 0 and not q.empty():
                    await asyncio.sleep(self.sentence_pause)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"[TTS {self.engine.name}] Ошибка на тексте {text!r}: {e}")
            finally:
                q.task_done()

    def _clear_queue(self) -> None:
        if self.queue is None:
            return
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
                self.queue.task_done()
            except asyncio.QueueEmpty:
                break