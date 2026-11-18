import asyncio
from pathlib import Path
from typing import AsyncIterator

import numpy as np
from kokoro_onnx import Kokoro

from core.tts.base import TTSCapabilities


class KokoroEngine:
    name = "kokoro"

    def __init__(
        self,
        model_path: str | Path,
        voices_path: str | Path,
        voice: str = "af_heart",
        speed: float = 1.0,
        lang: str = "en-us",
    ):
        self._model_path = Path(model_path)
        self._voices_path = Path(voices_path)
        self._voice = voice
        self._speed = speed
        self._lang = lang
        self._kokoro: Kokoro | None = None

    @property
    def capabilities(self) -> TTSCapabilities:
        voices = (
            list(self._kokoro.get_voices()) if self._kokoro else [self._voice]
        )
        return TTSCapabilities(
            languages=[self._lang],
            voices=voices,
            streaming=True,
            clone=False,
            requires_gpu=False,
            sample_rate=24000,
        )

    async def load(self) -> None:
        if self._kokoro is None:
            self._kokoro = Kokoro(
                str(self._model_path), str(self._voices_path)
            )
        print(f"KokoroEngine: загружен ({self._model_path.name})")

    async def unload(self) -> None:
        self._kokoro = None

    async def synthesize(
        self, text: str
    ) -> AsyncIterator[tuple[np.ndarray, int]]:
        if self._kokoro is None:
            raise RuntimeError("KokoroEngine: сначала вызовите load()")

        stream = self._kokoro.create_stream(
            text=text,
            voice=self._voice,
            speed=self._speed,
            lang=self._lang,
        )
        async for audio, sr in stream:
            yield audio, sr