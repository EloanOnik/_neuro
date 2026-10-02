# services/brain.py
import asyncio
import time
import yaml
from pathlib import Path

from core.llm import LLMClient
from core.context import ChatContext
from services.tts_player import TTSPlayer

_BASE_DIR = Path(__file__).resolve().parent.parent


class Brain:
    def __init__(
        self,
        model: str = "qwen2.5:3b",
        path_system_prompt: str | Path = _BASE_DIR / "system" / "system.yaml",
    ):
        self.model = model
        self.queue: asyncio.Queue | None = None
        self.llm_client: LLMClient | None = None
        self.chat_context = ChatContext()
        self.tts_player = TTSPlayer()
        self._task = None
        self.path_system_prompt = Path(path_system_prompt)
        self.system_prompt = self._load_system_prompt()

    def _load_system_prompt(self) -> str:
        with self.path_system_prompt.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)

        prompt = (data.get("system_prompt") or "").strip()
        if not prompt:
            raise ValueError(
                f"system_prompt пустой или отсутствует: {self.path_system_prompt}"
            )
        return prompt

    async def start(self): 
        print("Попытка выполнить start (brain)")
        self.queue = asyncio.Queue()
        self.llm_client = LLMClient(model=self.model)
        if not await self.llm_client.load_model():
            raise RuntimeError("Не удалось загрузить модель LLM. Выход из start (brain)")
        print("LLM модель успешно загружена. Выход из start (brain)")
        # запустить фоновую задачу обработки очереди
        self._task = asyncio.create_task(self._process_queue())

    async def stop(self):
        print("Попытка выполнить stop. (brain)")
        if (self.queue is None) and (self.llm_client is None):
            print("Brain: start не запустился, что бы выполнять stop")
            return
        # 1. Остановить приём новых сообщений
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        if self.llm_client:
            await self.llm_client.stop()
            await self.llm_client.close_client()
            await self.llm_client.close_stream_client()
        if self.tts_player:
            await self.tts_player.stop()
        print("Brain: остановлен")
        

    async def enqueue(self, user: str, text: str, meta: dict):
        if self.queue is None:
            raise RuntimeError("Brain не запущен")        
        await self.queue.put({
            "user": user,
            "text": text,
            "meta": meta,
            "ts": time.time(),
        })
        print(f"Brain: enqueue {user}: {text}")

    async def _process_queue(self):
        print("Brain: _process_queue запущен")
        while True:
            try:
                item = await self.queue.get()
                try:
                    await self._handle_item(item)
                except Exception as e:
                    print(f"{type(e).__name__}: {e}")
                finally:
                    self.queue.task_done()
            except asyncio.CancelledError:
                print("Brain: method _process_queue: except CancelledError")
                break

    async def _handle_item(self, item): # использует другие подметоды
        """Оркестратор Brain: промпт → LLM → TTS → контекст."""
        prompt = self._build_prompt(item) # создать промпт 
        tokens = self._stream_llm(prompt) # просто вывод от ollama может стоит добавить await
        answer = await self._flush_tts_buffer(tokens) # собирает предложения из токенов -> озвучивает -> выдает полный ответ llm для input context
        self.chat_context.add_user_message(item["text"]) # добавляет наш запрос в context
        self.chat_context.add_assistant_message(answer) # добавляет ответ LLM в контекст



    def _build_prompt(self, item):# создает промпт, контекст + то что пришло из чата
        """system prompt + context + this prompt"""
        messages = []
        messages.append({"role": "system", "content": self.system_prompt})
        messages.extend(self.chat_context.get_all())
        messages.append({"role": "user", "content": item["text"]})
        return messages


    async def _stream_llm(self, prompt): # отправляет элемент из очереди в llm # подумать на счет async, yield
        """output llm (ollama) tokens"""
        await self.llm_client.stream_ask_generator(prompt)
        


    async def _flush_tts_buffer(self, tokens_async_iterator):# получает ответ llm из очереди его ответов
        """join tokens in sentence + speak + full ollama output"""
        #создать буфер для накопления токенов
        #передавать накопленные токены из буфера в tts при накоплении полного предложения
        #накапливать полный ответ LLM для дальнейшой записи в контекстное окно и предачи дальше
        buffer = ""
        full_response = ""

        async for token in tokens_async_iterator:
            buffer += token
            full_response += token
            if buffer.endswith(('.', '!', '?')):
                self.tts_player.speak(buffer)
                buffer = ""

        if len(buffer) != 0:
            self.tts_player.speak(buffer)
            buffer = ""

        return full_response
