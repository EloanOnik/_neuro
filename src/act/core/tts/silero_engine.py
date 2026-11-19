import asyncio
import re
from pathlib import Path
from typing import AsyncIterator

import numpy as np
from loguru import logger
from num2words import num2words
from silero_onnx import SileroTTS

from act.core.tts.base import TTSCapabilities


def _prepare_ru_text(text: str) -> str:
    """Готовит текст для русской модели Silero: убирает эмодзи/латиницу, переводит числа в слова."""
    if not text:
        return ""

    def _num_repl(match: re.Match) -> str:
        raw = match.group()
        if len(raw) > 12:
            return " ".join(num2words(int(d), lang="ru") for d in raw)
        try:
            return num2words(int(raw), lang="ru")
        except Exception:
            return ""

    text = re.sub(r"\d+", _num_repl, text)
    text = re.sub(r"[^а-яА-ЯёЁ\s.,!?;:\-—]", " ", text)
    text = re.sub(r"([.,!?;:\-—])\1+", r"\1", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


class SileroEngine:
    name = "silero"

    def __init__(
        self,
        model_dir: str | Path,
        speaker: str = "xenia",
        sample_rate: int = 48000,
    ):
        self._model_dir = Path(model_dir)
        self._speaker = speaker
        self._sample_rate = sample_rate
        self._tts: SileroTTS | None = None

    @property
    def capabilities(self) -> TTSCapabilities:
        return TTSCapabilities(
            languages=["ru"],
            voices=["aidar", "baya", "kseniya", "eugene", "xenia"],
            streaming=False,
            clone=False,
            requires_gpu=False,
            sample_rate=self._sample_rate,
        )

    async def load(self) -> None:
        if self._tts is None:
            self._tts = await asyncio.to_thread(
                SileroTTS,
                model_dir=str(self._model_dir),
            )
            # Если в объекте SileroTTS есть атрибут sample_rate — используем его
            tts_sr = getattr(self._tts, "sample_rate", None)
            if isinstance(tts_sr, (int, float)) and tts_sr > 0:
                self._sample_rate = int(tts_sr)
        logger.info(f"SileroEngine: загружен ({self._model_dir.name}, sr={self._sample_rate})")

    async def unload(self) -> None:
        self._tts = None

    async def synthesize(
        self, text: str
    ) -> AsyncIterator[tuple[np.ndarray, int]]:
        if self._tts is None:
            raise RuntimeError("SileroEngine: сначала вызовите load()")

        clean_text = _prepare_ru_text(text)

        if not re.search(r"[а-яА-ЯёЁ]", clean_text):
            return

        result = await asyncio.to_thread(
            self._tts.synthesize,
            clean_text,
            speaker=self._speaker,
        )

        # silero_onnx возвращает (audio, durations) либо просто audio
        audio = result[0] if isinstance(result, tuple) else result

        if audio is None:
            return

        audio_arr = np.asarray(audio, dtype=np.float32).squeeze()
        if audio_arr.size == 0:
            return

        yield audio_arr, self._sample_rate