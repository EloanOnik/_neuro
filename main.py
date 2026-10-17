import asyncio
import queue

from services.brain import Brain
from services.tts_player import TTSPlayer
from adapters.chat.twitch import TwitchChat


async def main():
    tts = TTSPlayer()
    await tts.start()

    brain = Brain(tts_player=tts)
    try:
        await brain.start()
    except Exception:
        await tts.stop()
        raise

    chat = TwitchChat();  chat.start()

    while True:
        try:
            raw = await asyncio.to_thread(chat.message_queue.get, True, 2)
        except queue.Empty:
            continue

        if not raw or ":" not in raw:
            continue

        user_part, text = raw.split(":", 1)
        user = user_part.strip("[]")
        await brain.enqueue(user=user, text=text.strip(), meta={"source": "twitch"})

if __name__ == "__main__":
    asyncio.run(main())