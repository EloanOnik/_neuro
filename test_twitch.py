import queue
from adapters.chat.twitch import TwitchChat

chat = TwitchChat()
chat.start()
print("TwitchChat запущен, ждём 30 секунд сообщений...")

try:
    while True:
        raw = chat.message_queue.get(True, 20)
        print(f"ПОЛУЧЕНО: {raw!r}")
except queue.Empty:
    print("Таймаут 20 сек — за это время ничего не пришло")