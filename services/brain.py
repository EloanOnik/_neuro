import asyncio
from core.llm import LLMClient
from core.context import ChatContext
from services.tts_player import TTSPlayer


class Brain:
    def __init__(
        self,
        model: str = "qwen2.5:3b"
    ):
        self.model = model
        self.queue: asyncio.Queue | None = None
        self.llm_client: LLMClient | None = None
        self.chat_context = ChatContext()
        self.tts_player = TTSPlayer()

    async def start(self):
        self.queue = asyncio.Queue()
        self.llm_client = LLMClient(model=self.model)
        if not self.llm_client.load_model():
            print("Не удалось загрузить модель LLM")
            return
        print("LLM: модель загружена")

    async def stop(self):
        if self.llm_client:
            self.llm_client.stop()

    async def enqueue(self, user: str, text: str, meta: dict):
        await self.queue.put({
            "user": user,
            "text": text,
            "meta": meta,
        })

    async def _process_queue():

    async def _handle_item(item):

    async def _build_prompt(item):

    async def _stream_llm(prompt):

    async def _flush_tts_buffer(tokens):
