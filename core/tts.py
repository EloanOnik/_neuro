import asyncio
import queue
import threading
from math import gcd
from pathlib import Path

import numpy as np
import sounddevice as sd
from kokoro_onnx import Kokoro
from scipy.signal import resample_poly


class _AudioWriter:
    """Отдельный поток: держит OutputStream и пишет в него из очереди."""

    def __init__(self, device_index: int, samplerate: int, channels: int):
        self._queue: queue.Queue[np.ndarray | None] = queue.Queue()
        self._device = device_index
        self._samplerate = samplerate
        self._channels = channels
        self._thread = threading.Thread(target=self._run, daemon=True, name="AudioWriter")
        self._done = threading.Event()
        self._exc: BaseException | None = None

    def start(self):
        self._thread.start()

    def _run(self):
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

    def write(self, chunk: np.ndarray):
        if self._exc is not None:
            raise self._exc
        self._queue.put(chunk)

    async def finish(self):
        """Запросить завершение и дождаться, не блокируя event loop."""
        self._queue.put(None)
        await asyncio.to_thread(self._done.wait)
        if self._exc is not None:
            raise self._exc


class TextToSpeech:
    def __init__(
        self,
        model_path: str | Path,
        voices_path: str | Path,
        device_index: int | None = None,
        target_sr: int = 48000,
        target_ch: int = 2,
        voice: str = "af_heart",
        speed: float = 1.0,
        lang: str = "en-us",  # проверьте, поддерживает ли ваша сборка Kokoro "ru"
    ):
        self.model_path = Path(model_path)
        self.voice_engine = Kokoro(str(model_path), str(voices_path))
        print(f"TTS: модель загружена ({self.model_path.name})")

        self.device_index = device_index
        self.target_sr = target_sr
        self.target_ch = target_ch
        self.voice = voice
        self.speed = speed
        self.lang = lang
        self._speak_lock = asyncio.Lock()

    def get_audio_devices(self):
        print("Все VB-Cable / CABLE устройства")
        for i, dev in enumerate(sd.query_devices()):
            name = dev["name"]
            if "CABLE" in name.upper() or "VB-AUDIO" in name.upper():
                hostapi = sd.query_hostapis(dev["hostapi"])["name"]
                print(
                    f"[{i}] {name} | {hostapi} | "
                    f"out:{dev['max_output_channels']} in:{dev['max_input_channels']} | "
                    f"sr:{dev['default_samplerate']}"
                )

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
                print(f"Нужный кабель найден: ID {i} ({self.target_sr} Hz)")
                return True

        self.get_audio_devices()
        print("TextToSpeech.find_vbcable_devices: подходящее устройство не найдено")
        return False

    async def speak(self, text: str) -> None:
        if not text or not text.strip():
            return
        if self.device_index is None:
            raise RuntimeError("Аудиоустройство не выбрано (device_index is None)")

        async with self._speak_lock:
            stream = self.voice_engine.create_stream(
                text=text,
                voice=self.voice,
                speed=self.speed,
                lang=self.lang,
            )
            writer = _AudioWriter(self.device_index, self.target_sr, self.target_ch)
            writer.start()

            stream_failed = False
            try:
                async for audio, sr in stream:
                    if audio is None or len(audio) == 0:
                        continue

                    if sr != self.target_sr:
                        g = gcd(sr, self.target_sr)
                        audio = resample_poly(audio, self.target_sr // g, sr // g)

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