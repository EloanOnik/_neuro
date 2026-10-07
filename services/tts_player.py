import asyncio
from pathlib import Path

from core.tts import TextToSpeech


BASE_DIR = Path(__file__).resolve().parent.parent


#Принимает текст с приоритетом, играет его через TTS в VB-Cable, не блокируя вызывающий код

class TTSPlayer:
    def __init__(
        self,
    ):
        self.text_to_speech: TextToSpeech | None = None
        self._task = None
        self.queue = None
        self._started = False


    async def start(self):
        self.queue = asyncio.Queue()
        await self.text_to_speech = TextToSpeech(
            model_path=BASE_DIR / "tts_models" / "kokoro-v1.0.onnx",
            voices_path=BASE_DIR / "tts_models" / "voices-v1.0.bin",
        ) # Возможно без await
        self._started = True
        #Запуск очереди фоном
        self._task = asyncio.create_task(self._process_queue())
        

    async def stop(self):
        if not self._started:
            print("TTSPlayer: method stop: TTSPlayer не запустил start, что бы выполнить stop")
            return
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        if self.text_to_speech:
            self.text_to_speech = None
        if self.queue:
            self._clear_queue
            self.queue = None
            
    async def speak(self, message):
        if self.queue.empty():
            return
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

    def _clear_queue(self):
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
                self.queue.task_done()
            except asyncio.QueueEmpty:
                break

    async def _local_tts_stream(self):
        pass

    async def _stream_edge_tts(self):
        pass