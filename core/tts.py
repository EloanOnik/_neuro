"""# core/tts.py
import wave
from pathlib import Path
from datetime import datetime
from piper import PiperVoice


class TextToSpeech:
    
    #Синхронный TTS на Piper.
    #Сохраняет озвучку в output/ с уникальным именем.
    

    def __init__(
        self,
        model_path: str | Path,
        output_dir: str | Path = "output",
    ):
        self.model_path = Path(model_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        self.voice = PiperVoice.load(str(self.model_path))
        print(f"TTS: модель загружена ({self.model_path.name})")

    def speak(self, text: str) -> Path:
        
        #Синтезирует текст в WAV-файл.
        #Возвращает путь к сохранённому файлу.
        
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S_%f")
        output_path = self.output_dir / f"speech_{timestamp}.wav"

        with wave.open(str(output_path), "wb") as wav_file:
            self.voice.synthesize_wav(text, wav_file)

        print(f"TTS: сохранено в {output_path}")
        return output_path
"""

from math import gcd
from pathlib import Path

import numpy as np
import sounddevice as sd
from kokoro_onnx import Kokoro
from scipy.signal import resample_poly


class TextToSpeech:
    def __init__(
        self,
        model_path: str | Path,
        voices_path: str | Path,
        device_index: int = 17,
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

    async def speak(self, text: str) -> None:
        stream = self.voice_engine.create_stream(
            text=text,
            voice=self.voice,
            speed=self.speed,
            lang=self.lang,
        )

        with sd.OutputStream(
            samplerate=self.target_sr,
            channels=self.target_ch,
            dtype="float32",
            device=self.device_index,
        ) as out:
            async for audio, sr in stream:
                if sr != self.target_sr:
                    g = gcd(sr, self.target_sr)
                    audio = resample_poly(audio, self.target_sr // g, sr // g)

                if self.target_ch == 2 and audio.ndim == 1:
                    audio = np.column_stack((audio, audio))

                out.write(audio.astype(np.float32, copy=False))