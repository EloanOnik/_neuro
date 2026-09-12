import asyncio
import edge_tts
from pathlib import Path
from datetime import datetime

class TTSPlayer:
    def __init__(
        self,
        voice: str = "ru-RU-SvetlanaNeural",
        message: str = None,
    ):
        self.voice = voice
        self.message = message
        self.flag_tts_player = False
        self.communicate = None


    async def start(self,):

            

    async def stop(self):

    async def speak(self, voice, message):

    async def _process_queue(self):

    async def _stream_edge_tts(self):