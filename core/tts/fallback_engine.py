from typing import AsyncIterator
import logging
import numpy as np

from core.tts.base import TTSEngine, TTSCapabilities

logger = logging.getLogger(__name__)


class FallbackEngine:
    """Пробует движки по порядку. Если первый упал в synthesize — идёт ко второму."""

    name = "fallback"

    def __init__(self, engines: list[TTSEngine]):
        if not engines:
            raise ValueError("FallbackEngine: нужен хотя бы один движок")
        self._engines = engines
        self._loaded: set[int] = set()

    @property
    def capabilities(self) -> TTSCapabilities:
        return self._engines[0].capabilities

    async def load(self) -> None:
        await self._engines[0].load()
        self._loaded.add(0)

    async def unload(self) -> None:
        for i, eng in enumerate(self._engines):
            if i in self._loaded:
                try:
                    await eng.unload()
                except Exception:
                    logger.exception(f"fallback: unload {eng.name} упал")
        self._loaded.clear()

    async def synthesize(
        self, text: str
    ) -> AsyncIterator[tuple[np.ndarray, int]]:
        last_exc: Exception | None = None
        for i, eng in enumerate(self._engines):
            if i not in self._loaded:
                try:
                    await eng.load()
                    self._loaded.add(i)
                except Exception as e:
                    logger.exception(f"fallback: не удалось загрузить {eng.name}")
                    last_exc = e
                    continue
            try:
                async for chunk in eng.synthesize(text):
                    yield chunk
                return
            except Exception as e:
                logger.warning(f"fallback: {eng.name} упал: {e}")
                last_exc = e
        raise last_exc or RuntimeError("fallback: все движки упали")