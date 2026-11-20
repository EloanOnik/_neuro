# core/llm.py
import asyncio
import json
import os

import httpx
from loguru import logger


# Удалить лишний код, который не используется


class LLMClient:
    """Клиент для общения с Ollama."""

    def __init__(
        self,
        model: str = "gemma3:12b", # qwen2.5:3b
        url: str | None = None, # http://localhost:11434/api/chat
        timeout: float = 180.0,
        keep_alive: str = "30m",
    ):
        self.model = model
        # Берём из аргумента, иначе из env, иначе localhost
        base = (url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")
        self.base_url = base
        self.url = f"{base}/api/chat"
        self.timeout = timeout
        self.keep_alive = keep_alive
        self._client: httpx.AsyncClient | None = None
        self._stream_client: httpx.AsyncClient | None = None
        self.lock = asyncio.Lock()

    """Ленивая инициализация.
    Клиент создаётся только при первом обращении.
    Переиспользование соединений (connection pooling).
    код не защищён от гонок. Если два корутины одновременно вызовут _get_client() до создания клиента, может создаться два клиента.
    Обычно решается через asyncio.Lock."""

    async def _get_stream_client(self) -> httpx.AsyncClient:

        if self._stream_client is not None:
            return self._stream_client

        async with self.lock:
            if self._stream_client is None:
                self._stream_client = httpx.AsyncClient(timeout=self.timeout)
            return self._stream_client


    async def close_stream_client(self) -> None:
        if self._stream_client is not None:
            await self._stream_client.aclose()
            self._stream_client = None


    async def load_stream_model(self) -> bool:
        """Прогревает модель в память (пустой запрос)."""
        logger.debug("LLM.load_stream_model: прогрев модели {}", self.model)
        client = await self._get_stream_client() #Возможно гонка
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
            logger.debug(
                "LLM.load_straem_model: HTTP {} body={!r}",
                response.status_code, response.text[:200],
            )
            if response.status_code == 200:
                logger.success("LLM.load_straem_model: модель {} загружена", self.model)
                return True
            logger.error(
                "LLM.load_straem_model: HTTP {} при прогреве модели: {}",
                response.status_code, response.text[:500],
            )
            return False
        except httpx.RequestError:
            logger.exception("LLM.load_straem_model: сетевая ошибка при прогреве модели")
            return False


    async def stop_stream_client(self):
        logger.debug("LLM.stop_stream_client: выгрузка модели {}", self.model)
        client = await self._get_stream_client() #Возможно гонка       
        #url = self.url.replace("/api/chat", "/api/generate")
        url = f"{self.base_url}/api/generate"
        try:
            response = await client.post(
                url,
                json={
                    "model": self.model,
                    "keep_alive": 0,
                },
                timeout=10.0,
            )
            if response.status_code >=400:
                logger.error(
                    "LLM.stop_stream_client: HTTP {} при выгрузке: {}",
                    response.status_code, response.text[:500],
                )
                print(f"llm: class LLMClient: method stop_stream_client: вернул статус {response.status_code}: {response.text}")
                return False
            logger.debug("LLM.stop_stream_client: модель выгружена")
            return True
        except httpx.RequestError:
            logger.exception("LLM.stop_stream_client: не удалось выгрузить модель")
            return False


    async def stream_ask_generator(self, message: list):
        """Отправляет запрос и возвращает токены ответа."""
        logger.debug("LLM.stream: начало ({} сообщений в контексте)", len(message))
        client = await self._get_stream_client()
        tokens_count = 0
        finished_cleanly = False

        try:
            async with client.stream(
                "POST",
                self.url,
                json={
                    "model": self.model,
                    "messages": message,
                    "stream": True,
                    "keep_alive": self.keep_alive,
                },
            ) as response:
                if response.status_code >= 400:
                    body = await response.aread()
                    logger.error(
                        "LLM.stream: HTTP {} body={!r}",
                        response.status_code, body[:500],
                    )
                    response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line.strip():
                        logger.trace("LLM.stream: пустая строка, пропускаю")
                        continue

                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        logger.warning("LLM.stream: не-JSON строка: {!r}", line[:200])
                        continue

                    if chunk.get("done") is True:
                        finished_cleanly = True
                        break

                    token = chunk.get("message", {}).get("content", "")
                    if token:
                        tokens_count += 1
                        yield token

        except httpx.HTTPStatusError:
            logger.exception("LLM.stream: HTTP-ошибка во время стрима")
            raise
        except httpx.RequestError:
            logger.exception("LLM.stream: сетевая ошибка во время стрима")
            raise
        finally:
            if finished_cleanly:
                logger.debug("LLM.stream: завершено чисто, токенов={}", tokens_count)
            else:
                logger.warning(
                    "LLM.stream: оборвано без 'done: true', токенов={}",
                    tokens_count,
                )