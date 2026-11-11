import queue
import threading
import asyncio
from math import gcd
from pathlib import Path

import numpy as np
import sounddevice as sd
from kokoro_onnx import Kokoro
from scipy.signal import resample_poly


class _AudioWriter:
    """Отдельный поток: держит OutputStream и пишет в него из очереди."""

    def __init__(
            self,
            device_index,
            samplerate: int,
            channels: int,
    ):
        self._queue: queue.Queue = queue.Queue()
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

        def write(self, chunk):
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
        lang: str = "ru",
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

    def get_audio_devices(self):
        print("=== Все VB-Cable / CABLE устройства ===")
        for i, dev in enumerate(sd.query_devices()):
            name = dev["name"]
            if "CABLE" in name.upper() or "VB-Audio" in name:
                hostapi = sd.query_hostapis(dev["hostapi"])["name"]
                print(f"[{i}] {name}")
                print(f"    hostapi: {hostapi}")
                print(f"    max_output_channels: {dev['max_output_channels']}")
                print(f"    max_input_channels:  {dev['max_input_channels']}")
                print(f"    default_samplerate:  {dev['default_samplerate']}")
                print()

    def find_vbcable_devices(self):
        self.device_index = None
        for i, dev in enumerate(sd.query_devices()):
            name = dev["name"]
            hostapi = sd.query_hostapis(dev["hostapi"])["name"]
            max_output_channels = dev["max_output_channels"]
            max_input_channels = dev["max_input_channels"]
            default_samplerate = dev["default_samplerate"]
            if name == "Hi-Fi Cable Input (VB-Audio Hi-Fi Cable)" and hostapi == "Windows WASAPI" and max_output_channels == 2 and max_input_channels == 0 and default_samplerate == 48000.0:
                self.device_index = i
                print(f"Нужный кабель найден: ID {i}")
                return
        self.get_audio_devices()
        print("core: tts: class TextToSpeech: method find_vbcable_devices: В списке устройст не найден подходящий")

                

    async def speak(self, text: str) -> None:
        if self.device_index is None:
            print("core: tts: class TextToSpeech: method speak: device_index равен None")
            return
        stream = self.voice_engine.create_stream(
            text=text,
            voice=self.voice,
            speed=self.speed,
            lang=self.lang,
        )
        writer = _AudioWriter(self.device_index, self.target_sr, self.target_ch)
        writer.start()
        try:
            async for audio, sr in stream:
                if sr != self.target_sr:
                    g = gcd(sr, self.target_sr)
                    audio = resample_poly(audio, self.target_sr // g, sr // g)

                if self.target_ch == 2 and audio.ndim == 1:
                    audio = np.column_stack((audio, audio))

                writer.write(audio.astype(np.float32, copy=False))
        finally:
            await writer.finish()
