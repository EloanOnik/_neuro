import queue

from adapters.chat.twitch import TwitchChat


class FilterTwitchChat:
    def __init__(
        self,
        chat: TwitchChat,
        banned_words: list | None = None
    ):

        self.chat = chat
        self.banned_words = [w.lower() for w in (banned_words or [])]


    def process_messages(self):
        """Обработка сообщений из очереди"""
        valid = []

        while True:
            try:
                raw = self.chat.message_queue.get_nowait()
            except queue.Empty:
                break

            #Разделение на никнейм и содержимое сообщения
            if ':' not in raw:
                continue
            user_part, text = raw.split(':', 1)
            user = user_part.strip('[]')

            #Фильтруем
            if any(w in text.lower() for w in self.banned_words):
                continue
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
            try:
                raw = chat.message_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            print(raw)

    except KeyboardInterrupt:
         print("\nЗавершение работы...")
         chat.stop()  # Корректно останавливаем поток
         print("Чат остановлен")


"""Главная причина «нет вывода» — KeyboardInterrupt и занятость GIL

Скорее всего, у вас вывод есть, но он не успевает появляться из-за busy-loop:
python

while True:
    messages = filter.process_messages()  # мгновенно возвращает []
    for msg in messages: ...              # ничего не делает

Цикл крутится на 100% CPU в главном потоке, захватывая GIL. 
Поток TwitchChat не успевает нормально обрабатывать данные из сокета, потому что главный поток постоянно его вытесняет. 
Внешне это выглядит как «сообщения не приходят»."""