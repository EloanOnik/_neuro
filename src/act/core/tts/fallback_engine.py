from typing import AsyncIterator
import numpy as np
from loguru import logger

from act.core.tts.base import TTSEngine, TTSCapabilities


class FallbackEngine:
    """Пробует движки по порядку. Переключается на следующий, если текущий упал до начала воспроизведения."""

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

            yielded_any = False
            try:
                async for chunk in eng.synthesize(text):
                    yielded_any = True
                    yield chunk
                return
            except Exception as e:
                if yielded_any:
                    logger.error(f"fallback: {eng.name} оборвался в середине фразы: {e}")
                    raise
                logger.warning(f"fallback: {eng.name} упал до начала озвучки: {e}")
                last_exc = e

        raise last_exc or RuntimeError("fallback: все движки упали")