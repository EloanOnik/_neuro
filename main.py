#Соединить llm + tts
import pyttsx3
import requests
from core.context import ChatContext

engine = pyttsx3.init()

# Настройка голоса, необязательность
voices = engine.getProperty('voices')

if isinstance(voices, list):
    for voice in voices:
        # На случий None
        languages = voice.languages if voice.languages else []

        if isinstance(languages, str):
            if 'ru' in languages.lower():
                engine.setProperty('voice', voice.id)
                break

        if isinstance(languages, list):
            for lang in languages:
                if 'ru' in lang.lower():
                    engine.setProperty('voice', voice.id)
                    break


# Загружаем модель в память
response = requests.post(
    "http://localhost:11434/api/chat",
    json={
        "model": "qwen2.5:3b",
        "messages": [{'role': 'user', 'content': 'Привет!'}],  # Пустой промпт просто загрузит модель
        "stream": False,
        "keep_alive": '5m', # Держать в памяти бесконечно (-1)
    }
)

print(f"Статус: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    print(data)
    text_response = data['message']['content']

    print(f"Ответ: {text_response}")

    # озвучиваем текст
    engine.say(text_response)
    engine.runAndWait()
else:
    print(f"Ошибка: {response.text}")
