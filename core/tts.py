# core/tts.py
import wave
from pathlib import Path
from datetime import datetime
from piper import PiperVoice


class TextToSpeech:
    """
    Синхронный TTS на Piper.
    Сохраняет озвучку в output/ с уникальным именем.
    """

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
        """
        Синтезирует текст в WAV-файл.
        Возвращает путь к сохранённому файлу.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S_%f")
        output_path = self.output_dir / f"speech_{timestamp}.wav"

        with wave.open(str(output_path), "wb") as wav_file:
            self.voice.synthesize_wav(text, wav_file)

        print(f"TTS: сохранено в {output_path}")
        return output_path
