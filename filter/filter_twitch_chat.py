from adapters.chat.twitch import TwitchChat

class FilterTwitchChat:
    def __init__(
        self,
        chat: TwitchChat,
        banned_words: list = []
    ):

        self.chat = chat
        self.banned_words = [w.lower() for w in (banned_words or [])]


    def process_messages(self):
        """Обработка сообщений из очереди"""
        valid = []

        while not self.chat.message_queue.empty():
            raw = self.chat.message_queue.get()

            #Разделение на никнейм и содержимое сообщения
            if ':' in raw:
                user_part, text = raw.split(':', 1)
                user = user_part.split('[]')

                #Фильтруем
                if not any(word in text.lower() for word in self.banned_words):
                    valid.append({
                        'user': user,
                        'text': text.strip()
                    })

        return valid


if __name__ == "__main__":
    chat = TwitchChat()
    chat.start()

    filter = FilterTwitchChat(
        chat = chat,
        banned_words=[]
    )

    try:
        while True:
            messages = filter.process_messages()
            for msg in messages:
                print(f"{msg['user']}: {msg['text']}")
    except KeyboardInterrupt:
         print("\nЗавершение работы...")
         chat.stop()  # Корректно останавливаем поток
         print("Чат остановлен")
