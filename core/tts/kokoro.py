import asyncio
import queue
import threading
from math import gcd
from pathlib import Path

import numpy as np
import sounddevice as sd
from kokoro_onnx import Kokoro
from scipy.signal import resample_poly
from loguru import logger


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
        logger.debug("_AudioWriter.start: _thread.start")

    def _run(self):
        try:
            with sd.OutputStream(
                samplerate=self._samplerate,
                channels=self._channels,
                dtype="float32",
                device=self._device,
            ) as out:
                logger.debug(
                    "_AudioWriter._run: with OutputStream: \n"
                    "samplerate = {} \n"
                    "channels = {} \n"
                    "device = {} \n",
                    self._samplerate,
                    self._channels,
                    self._device,
                )
                while True:
                    chunk = self._queue.get()
                    if chunk is None:
                        break
                    out.write(chunk)
        except BaseException as e:
            logger.exception("_AudioWriter: ошибка при записи в аудиопоток")
            self._exc = e
        finally:
            self._done.set()

    def write(self, chunk: np.ndarray):
        if self._exc is not None:
            raise self._exc
        self._queue.put(chunk)

    async def finish(self):
        """Запросить завершение и дождаться, не блокируя event loop."""
        logger.debug("_AudioWriter: запрос на завершение поток")
        self._queue.put(None)
        await asyncio.to_thread(self._done.wait)
        logger.debug("_AudioWriter: поток успешно завершен")
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
        self.voices_path = Path(voices_path)
        self.voice_engine = Kokoro(str(self.model_path), str(self.voices_path))
        logger.info(
            "TTS: модель загружена ({})",
            self.model_path.name,
        )

        self.device_index = device_index
        self.target_sr = target_sr
        self.target_ch = target_ch
        self.voice = voice
        self.speed = speed
        self.lang = lang
        self._speak_lock = asyncio.Lock()
        self._stats: dict[str, int] = {}

        logger.debug(
            "TTS.init: init прошел успешно.\n"
            "model_path = {}\n"
            "voices_path = {}\n"
            "device_index = {}\n"
            "target_sr = {}\n"
            "target_ch = {}\n"
            "voice = {}\n"
            "speed = {}\n"
            "lang = {}",
            self.model_path,
            self.voices_path,
            self.device_index,
            self.target_sr,
            self.target_ch,
            self.voice,
            self.speed,
            self.lang,
        )


    def _track_stat(self, key: str, label: str, step: int = 100) -> None:
        count = self._stats.get(key, 0) + 1
        self._stats[key] = count
        if count % step == 0:
            logger.info("TTS.speak: {} достигло {}", label, count)


    @staticmethod
    def get_audio_devices():
        logger.info("Все VB-Cable / CABLE устройства")
        found = False
        for i, dev in enumerate(sd.query_devices()):
            name = dev["name"]
            if "CABLE" in name.upper() or "VB-AUDIO" in name.upper():
                found = True
                hostapi = sd.query_hostapis(dev["hostapi"])["name"]
                logger.info(
                    "[{}] {} | {} | out:{} in:{} | sr:{:.0f}",
                    i,
                    name,
                    hostapi,
                    dev['max_output_channels'],
                    dev['max_input_channels'],
                    dev['default_samplerate'],
                )
        if not found:
            logger.warning("VB-Cable / CABLE устройства не найдены")


    def find_vbcable_devices(self) -> bool:
        self.device_index = None
        logger.info("TTS.find_vbcable_devices: device_index = None")
        for i, dev in enumerate(sd.query_devices()):
            hostapi = sd.query_hostapis(dev["hostapi"])["name"]
            if (
                "HI-FI CABLE INPUT" in dev["name"].upper()
                and hostapi == "Windows WASAPI"
                and dev["max_output_channels"] >= self.target_ch
            ):
                self.device_index = i
                self.target_sr = int(dev["default_samplerate"])
                logger.info(
                    "Нужный кабель найден: ID {} ({} Hz)",
                    i, self.target_sr,
                )
                return True

        self.get_audio_devices()
        logger.error("TextToSpeech.find_vbcable_devices: подходящее устройство не найдено")
        return False


    async def speak(self, text: str) -> None:
        if not text or not text.strip():
            self._track_stat("empty_line", "количество пустых строк")
            return
        if self.device_index is None:
            msg = "Аудиоустройство не выбрано (device_index is None)"
            logger.error("TTS.speak: {}", msg)
            raise RuntimeError(msg)
 
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
                        self._track_stat("empty_line", "количество пустых строк")
                        continue

                    if sr != self.target_sr:
                        g = gcd(sr, self.target_sr)
                        audio = resample_poly(audio, self.target_sr // g, sr // g)
                        self._track_stat("resampling", "количество ресемплингов")

                    if self.target_ch == 2 and audio.ndim == 1:
                        audio = np.column_stack((audio, audio))
                        self._track_stat("mono_stereo", "количество преобразований моно -> стерео")
                    elif self.target_ch == 1 and audio.ndim == 2:
                        audio = audio.mean(axis=1)
                        self._track_stat("stereo_mono", "количество преобразований стерео -> моно")

                    writer.write(audio.astype(np.float32, copy=False))
            except BaseException:
                stream_failed = True
                logger.exception("TTS.speak: ошибка при генерации речи для текста длиной {} символов", len(text))
                raise
            finally:
                try:
                    await writer.finish()
                except BaseException:
                    if not stream_failed:
                        raise