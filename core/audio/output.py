import asyncio
import queue
import threading
from math import gcd
from typing import AsyncIterator

import numpy as np
import sounddevice as sd
from scipy.signal import resample_poly


class _AudioWriter:
    """Отдельный поток: держит OutputStream и пишет в него из очереди."""

    def __init__(self, device_index: int, samplerate: int, channels: int):
        self._queue: queue.Queue[np.ndarray | None] = queue.Queue()
        self._device = device_index
        self._samplerate = samplerate
        self._channels = channels
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="AudioWriter"
        )
        self._done = threading.Event()
        self._exc: BaseException | None = None

    def start(self) -> None:
        self._thread.start()

    def _run(self) -> None:
        try:
            with sd.OutputStream(
                samplerate=self._samplerate,
                channels=self._channels,
                dtype="float32",
                device=self._device,
            ) as out:
                while True:
                    chunk = self._queue.get()
                    if chunk is None:
                        break
                    out.write(chunk)
        except BaseException as e:
            self._exc = e
        finally:
            self._done.set()

    def write(self, chunk: np.ndarray) -> None:
        if self._exc is not None:
            raise self._exc
        self._queue.put(chunk)

    async def finish(self) -> None:
        self._queue.put(None)
        await asyncio.to_thread(self._done.wait)
        if self._exc is not None:
            raise self._exc


class AudioOutput:
    """Приводит аудио-чанки любого движка к формату VB-Cable и пишет в него."""

    def __init__(
        self,
        target_sr: int = 48000,
        target_ch: int = 2,
        device_index: int | None = None,
    ):
        self.target_sr = target_sr
        self.target_ch = target_ch
        self.device_index = device_index

    def find_vbcable_devices(self) -> bool:
        self.device_index = None
        for i, dev in enumerate(sd.query_devices()):
            hostapi = sd.query_hostapis(dev["hostapi"])["name"]
            if (
                "HI-FI CABLE INPUT" in dev["name"].upper()
                and hostapi == "Windows WASAPI"
                and dev["max_output_channels"] >= self.target_ch
            ):
                self.device_index = i
                self.target_sr = int(dev["default_samplerate"])
                print(f"AudioOutput: VB-Cable найден: ID {i} ({self.target_sr} Hz)")
                return True
        print("AudioOutput: подходящее устройство VB-Cable не найдено")
        return False

    async def play(
        self, chunks: AsyncIterator[tuple[np.ndarray, int]]
    ) -> None:
        if self.device_index is None:
            raise RuntimeError("AudioOutput: device_index не задан")

        writer = _AudioWriter(
            self.device_index, self.target_sr, self.target_ch
        )
        writer.start()

        stream_failed = False
        try:
            async for audio, sr in chunks:
                if audio is None or len(audio) == 0:
                    continue

                audio = np.asarray(audio, dtype=np.float32).reshape(-1)

                if sr != self.target_sr:
                    g = gcd(sr, self.target_sr)
                    audio = resample_poly(
                        audio, self.target_sr // g, sr // g
                    )

                if self.target_ch == 2 and audio.ndim == 1:
                    audio = np.column_stack((audio, audio))
                elif self.target_ch == 1 and audio.ndim == 2:
                    audio = audio.mean(axis=1)

                writer.write(audio.astype(np.float32, copy=False))
        except BaseException:
            stream_failed = True
            raise
        finally:
            try:
                await writer.finish()
            except BaseException:
                if not stream_failed:
                    raise