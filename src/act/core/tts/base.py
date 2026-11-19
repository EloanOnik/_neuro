from typing import Protocol, AsyncIterator
from dataclasses import dataclass
import numpy as np


@dataclass
class TTSCapabilities:
    languages: list[str]
    voices: list[str] | None      # None = только клонирование
    streaming: bool
    clone: bool
    requires_gpu: bool
    sample_rate: int


class TTSEngine(Protocol):
    name: str
    capabilities: TTSCapabilities

    async def load(self) -> None: ...
    async def unload(self) -> None: ...
    async def synthesize(
        self, text: str
    ) -> AsyncIterator[tuple[np.ndarray, int]]: ...