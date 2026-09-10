import socket
import ssl
import re
import threading
import queue
from typing import Optional

"""Блокировка потока, переписать на асинхронность no gil"""

class TwitchChat:
    # Настройки подключения
    HOST = "irc.chat.twitch.tv"
    PORT = 6697
    CHAN = "#nuke73"  # Имя канала строчными буквами с решеткой (например, #xqc)
    NICK = "justinfan84732"   # Анонимный ник
    PASSWORD = "SCHMOOPIIE"       # Заглушка пароля

    # Регулярное выражение для парсинга сообщения
    # Выделяет никнейм и текст сообщения
    MESSAGE_REGEX = re.compile(r"^:(\w+)!\w+@\w+\.tmi\.twitch\.tv PRIVMSG #\w+ :(.*)$")


    def __init__(
        self,
        host: str = HOST,
        port: int = PORT,
        chan: str = CHAN,
        nick: str = NICK,
        password: str = PASSWORD
    ):


        self.host = host
        self.port = port
        self.chan = chan if chan.startswith('#') else f'#{chan}'
        self.nick = nick
        self.password = password
        self._thread: Optional[threading.Thread] = None
        self.message_queue = queue.Queue()
        self._running = True


    def start(self):
        """Запуск чата в отдельном потоке"""
        self._thread = threading.Thread(
            target=self.connect_to_twitch,
            daemon=True,
            name=f"TwitchChat-{self.chan}"
        )
        self._thread.start()
        print(f"Чат {self.chan} запущен в отдельном потоке")


    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)


    def connect_to_twitch(self) -> None:
        # Создаем TCP-сокет и оборачиваем его в SSL для безопасности
        context = ssl.create_default_context()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        secure_sock = context.wrap_socket(sock, server_hostname=self.host)

        secure_sock.connect((self.host, self.port))

        # Отправляем учетные данные в формате IRC
        secure_sock.send(f"PASS {self.password}\r\n".encode("utf-8"))
        secure_sock.send(f"NICK {self.nick}\r\n".encode("utf-8"))
        secure_sock.send(f"JOIN {self.chan}\r\n".encode("utf-8"))

        print(f"Успешно подключились к чату {self.chan}. Ожидание сообщений...")

        secure_sock.settimeout(1.0)

        buffer = ""
        while self._running:
            # Читаем данные из сокета частями
            try:
                data = secure_sock.recv(2048).decode("utf-8", errors="ignore")
                if not data:
                    break

                buffer += data
                lines = buffer.split("\r\n")
                buffer = lines.pop()  # Оставляем незавершенную строку в буфере

                for line in lines:
                    # 1. Ответ на PING от сервера (критично, чтобы Twitch не кикнул)
                    if line.startswith("PING"):
                        secure_sock.send("PONG :tmi.twitch.tv\r\n".encode("utf-8"))
                        continue

                    # 2. Обработка обычных сообщений чата (PRIVMSG)
                    match = self.MESSAGE_REGEX.match(line)
                    if match:
                        username = match.group(1)
                        message = match.group(2)
                        self.message_queue.put(f"[{username}]: {message}")

            except KeyboardInterrupt:
                print("\nОтключение от чата...")
                secure_sock.close()
                break

            except socket.timeout:
                # Таймаут — просто проверяем _running и продолжаем
                continue
            except Exception as e:
                print(f"Ошибка: {e}")
                break

        secure_sock.close()


# Использование
if __name__ == "__main__":
    # Вариант 1: С настройками по умолчанию
    chat = TwitchChat()
    chat.start()

    while True:
        try:
            msg = chat.message_queue.get(timeout=1)
            print(f"Получил из очереди: {msg}")
        except queue.Empty:
            pass

    # Вариант 2: С переопределением настроек
    # chat = TwitchChat(
    #     chan="#another_channel",
    #     nick="my_custom_nick"
    # )
    # chat.connect_to_twitch()
