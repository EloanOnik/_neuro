# main.py
from pathlib import Path

from core.llm import LLMClient
from core.tts import TextToSpeech


BASE_DIR = Path(__file__).parent


def main():
    # Инициализация
    llm = LLMClient(model="qwen2.5:3b")
    tts = TextToSpeech(
        model_path=BASE_DIR / "tts_models" / "ru_RU-irina-medium.onnx",
        output_dir=BASE_DIR / "output",
    )

    # Прогрев LLM
    if not llm.load_model():
        print("Не удалось загрузить модель LLM")
        return
    print("LLM: модель загружена")

    print("Введите текст (Ctrl+C для выхода):")

    try:
        while True:
            user_input = input("> ")
            if not user_input.strip():
                continue

            answer = llm.ask(user_input)
            if not answer:
                continue

            print(f"🤖: {answer}")
            tts.speak(answer)

    except KeyboardInterrupt:
        print("\nЗавершение работы...")


if __name__ == "__main__":
    main()
