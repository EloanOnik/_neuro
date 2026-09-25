# main.py
import asyncio
from pathlib import Path

from core.llm import LLMClient
from core.tts import TextToSpeech

BASE_DIR = Path(__file__).parent


async def main():
    # Инициализация
    llm = LLMClient(model="qwen2.5:3b")
    tts = TextToSpeech(
        model_path=BASE_DIR / "tts_models" / "kokoro-v1.0.onnx",
        voices_path=BASE_DIR / "tts_models" / "voices-v1.0.bin",
        #output_dir=BASE_DIR / "output",
    )

    # Прогрев LLM
    if not await llm.load_model():
        print("Не удалось загрузить модель LLM")
        return
    print("LLM: модель загружена")

    print("Введите текст (Ctrl+C для выхода):")

    try:
        while True:
            user_input = await asyncio.to_thread(input, "> ")
            if not user_input.strip():
                continue

            answer = await llm.ask(user_input)
            if not answer:
                continue

            print(f": {answer}")
            await tts.speak(answer)

    except KeyboardInterrupt:
        print("\nЗавершение работы...")


if __name__ == "__main__":
    asyncio.run(main())
