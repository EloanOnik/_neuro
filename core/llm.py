# core/llm.py
import requests
from typing import Optional


class LLMClient:
    """Клиент для общения с Ollama."""

    def __init__(
        self,
        model: str = "qwen2.5:3b",
        url: str = "http://localhost:11434/api/chat",
        timeout: float = 30.0,
        keep_alive: str = "5m",
    ):
        self.model = model
        self.url = url
        self.timeout = timeout
        self.keep_alive = keep_alive

    def load_model(self) -> bool:
        """Прогревает модель в память (пустой запрос)."""
        try:
            response = requests.post(
                self.url,
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": "Привет!"}],
                    "stream": False,
                    "keep_alive": self.keep_alive,
                },
                timeout=self.timeout,
            )
            return response.status_code == 200
        except requests.RequestException as e:
            print(f"LLM: ошибка загрузки модели: {e}")
            return False

    def ask(self, prompt: str) -> Optional[str]:
        """Отправляет запрос и возвращает текст ответа."""
        try:
            response = requests.post(
                self.url,
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    "keep_alive": self.keep_alive,
                },
                timeout=self.timeout,
            )

            if response.status_code != 200:
                print(f"LLM: ошибка {response.status_code}: {response.text}")
                return None

            data = response.json()
            return data.get("message", {}).get("content", "")

        except requests.RequestException as e:
            print(f"LLM: ошибка запроса: {e}")
            return None
