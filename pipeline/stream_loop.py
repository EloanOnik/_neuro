import asyncio
import queue

from adapters.chat.twitch import TwitchChat
from filter.filter_twitch_chat import FilterTwitchChat
from services.brain import Brain
from services.tts_player import TTSPlayer

class StreamLoop:
    def __init__(
    self,
    ):
        self.twitch_chat: TwitchChat | None = None
        self.filter: FilterTwitchChat | None = None
        self.brain: Brain | None = None
        self.queue = None
        self._task = None

    #соединить все модули
    #TwitchChat (поток) → Filter → Brain.enqueue() → очередь → LLM → TTS → аудио


    async def start(self):
        self.queue = asyncio.Queue()
        self.twitch_chat = TwitchChat(
            host="irc.chat.twitch.tv",
            port=6697,
            chan="Name",
            nick="MyName",
            password="SCHMOOPIIE",
        )
        self.filter = FilterTwitchChat(self.twitch_chat, banned_words=[])
        self.brain = Brain()
        await self.brain.start()
        await self.brain.tts_player.start()
        self._task = asyncio.create_task(self._poll_chat())


    async def stop(self):
        if (self.queue is None) and (self.brain is None) and (self.filter is None):
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
            self.twitch_chat.stop()
            self.twitch_chat = None
        if self.brain:
            self.brain.stop()
            self.brain = None
        


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
        if self.filter(item):
            await self.brain.queue(item)
