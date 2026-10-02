import asyncio
from pathlib import Path
from datetime import datetime

from core.tts import TextToSpeech

#Принимает текст с приоритетом, играет его через TTS в VB-Cable, не блокируя вызывающий код

class TTSPlayer:
    def __init__(
        self,
    ):

        self.text_to_speech: TextToSpeech | None = None
        self._task = None
        self.queue = None


    async def start(self,):
        self.queue = asyncio.Queue()
        self.text_to_speech = TextToSpeech()
        #Запуск очереди фоном
        self._task = asyncio.create_task(self._process_queue())
        

    async def stop(self):
        if (self.queue is None) and (self.text_to_speech is None):
            print("TTSPlayer: method stop: TTSPlayer не запустил start, что бы выполнить stop")
            return
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def speak(self, message):
        await self.queue.put(message)        

    async def _process_queue(self):
        while True:
            try:
                message = await self.queue.get()
                try:
                    await self.text_to_speech.speak(message)
                except Exception as e:
                    print(f"{type(e).__name__}: {e}")
                finally:
                    self.queue.task_done()
            except asyncio.CancelledError:
                print("TTSPlayer: method _process_queue: except CancelledError")
                break

    async def _local_tts_stream(self):


    async def _stream_edge_tts(self):