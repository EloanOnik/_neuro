from collections import deque


class ChatContext:
    """Контекст из 10 последних сообщений"""
    def __init__(self, max_messages=10):
        self.messages = deque(maxlen=max_messages)

    def add_user_message(self, text):
        """Добавить сообщение пользователя"""
        self.messages.append({"role": "user", "content": text})

    def add_assistant_message(self, text):
        """Добавить сообщение LLM"""
        self.messages.append({"role": "assistant", "content": text})

    def get_all(self):
        """Получить все сообщения для LLM"""
        return list(self.messages)

    def clear(self):
        """Очистить историю"""
        self.messages.clear()
