import asyncio
import queue

from adapters.chat.twitch import TwitchChat
from filter.filter_twitch_chat import FilterTwitchChat
from services.brain import Brain

class StreamLoop:
    def __init__(
    self,
    ):
        self.twitch_chat: TwitchChat | None = None
        self.filter: FilterTwitchChat | None = None
        self.brain: Brain | None = None
        self._task = None
        self._started = False

    #соединить все модули
    #TwitchChat (поток) → Filter → Brain.enqueue() → очередь → LLM → TTS → аудио
    #TwitchChat(thread) -> queue.Queue[str] -> StreamLoop(async) -> Brain.enqueue(dict) -> LLM -> TTS -> VB-Cable


    async def start(self):
        if self._started:
            return
        self.twitch_chat = TwitchChat()
        self.filter = FilterTwitchChat(self.twitch_chat, banned_words=[])
        self.brain = Brain()
        try:
            await self.brain.start()
        except Exception as e:
            print(f"stream_loop: StreamLoop: method start: {type(e).__name__}: {e}")
            await asyncio.to_thread(self.twitch_chat.stop)
            self.filter = None
            return
        self.twitch_chat.start()
        self._task = asyncio.create_task(self._poll_chat())
        self._started = True
        


    async def stop(self):
        if not self._started:
            print("StreamLoop: method stop: start не запустился, что бы выполнять stop")
            return
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None            
        if self.twitch_chat:
            await asyncio.to_thread(self.twitch_chat.stop)
            self.twitch_chat = None
        if self.brain:
            self.brain.stop()
            self.brain = None
        if self.filter:
            self.filter = None
        self._started = False
        


    async def _poll_chat(self):
        while True:
            try:
                item = await asyncio.to_thread(self.twitch_chat.message_queue.get, True, 2)
                try:
                    await self._message(item)
                except Exception as e:
                    print(f"{type(e).__name__}: {e}")
                finally:
                    self.twitch_chat.message_queue.task_done()
            except queue.Empty:
                continue
            except asyncio.CancelledError:
                print("StreamLoop: method _poll_chat: CancelledError")
                break

    async def _message(self, item):
        cleaned = self.filter.process_messages(item)
        if not cleaned:
            return
        await self.brain.enqueue(
            user={"user"},
            text=cleaned["text"],
            meta={"source": "twitch"},
        )
