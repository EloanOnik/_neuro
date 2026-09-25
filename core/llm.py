# core/llm.py
import logging

import httpx

logger = logging.getLogger(__name__)

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
        self._client: httpx.AsyncClient | None = None

    """Ленивая инициализация.
    Клиент создаётся только при первом обращении.
    Переиспользование соединений (connection pooling).
    код не защищён от гонок. Если два корутины одновременно вызовут _get_client() до создания клиента, может создаться два клиента.
    Обычно решается через asyncio.Lock."""
    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def load_model(self) -> bool:
        """Прогревает модель в память (пустой запрос)."""
        client = await self._get_client() #Возможно гонка
        print("await self._get_client() в load_model прошел")
        try:
            response = await client.post(
                self.url,
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": "Привет!"}],
                    "stream": False,
                    "keep_alive": self.keep_alive,
                },
            )
            print(f"DEBUG load_model: status={response.status_code}")
            print(f"DEBUG load_model: body={response.text[:500]}")
            return response.status_code == 200
        #except httpx.RequestError as e:
         #   logger.error("LLM: ошибка загрузки модели: %s", e)
        #    print(f"LLM: ошибка загрузки модели: {e}")
       #     return False
        except Exception as e:
            print(f"DEBUG load_model: {type(e).__name__}: {e}")
            return False

    async def stop(self):
        client = await self._get_client() #Возможно гонка
        try:
            response = await client.post(
                self.url,
                json={
                    "model": self.model,
                    "keep_alive": "0m",
                },
            )
            if response.status_code >=400:
                logger.error(
                    "LLM stop вернул статус %s: %s",
                    response.status_code, response.text,
                )
                print(f"LLM stop вернул статус {response.status_code}: {response.text}")
                return False
            return True

        except httpx.RequestError as e:
            logger.error("LLMClient.stop: не удалось выгрузить модель: %s", e)
            print(f"Объект LLMClient не смог вызвать метод stop (не получилось выключить llm и убрать из памяти) {e}")
            return False


    async def ask(self, prompt: str) -> str | None:
        """Отправляет запрос и возвращает текст ответа."""
        client = await self._get_client()
        try:
            response = await client.post(
                self.url,
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    "keep_alive": self.keep_alive,
                },
            )

            if response.status_code != 200:
                logger.error("LLM: ошибка %s: %s", response.status_code, response.text)
                print(f"LLM: ошибка {response.status_code}: {response.text}")
                return None

            data = response.json()
            return data.get("message", {}).get("content", "")

        except httpx.RequestError as e:
            logger.error("LLM: ошибка запроса: %s", e)
            print(f"LLM: ошибка запроса: {e}")
            return None
