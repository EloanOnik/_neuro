import re
from dataclasses import dataclass


@dataclass(slots=True)
class ChatMessage:
    user: str
    text: str


class FilterTwitchChat:
    """Фильтрует и парсит сырые сообщения из TwitchChat по одному."""

    DEFAULT_IGNORED_USERS = frozenset({
        "streamelements",
        "nightbot",
        "moobot",
        "fossabot",
        "wizebot",
    })

    # Регулярка для мусора вроде "xd", "xdx", "хаха", "ахаха", "lul", "kekw", "???", ")))"
    _NOISE_RE = re.compile(
        r"^(?:[xхdд]+|[ахха]+|lul|kekw|omegalul|[?!.)(\s]+)$",
        re.IGNORECASE,
    )

    def __init__(
        self,
        banned_words: list[str] | None = None,
        ignored_users: list[str] | None = None,
        min_length: int = 3,
        max_length: int = 300,
    ):
        self.banned_words = [w.lower().strip() for w in (banned_words or []) if w.strip()]
        self.ignored_users = (
            {u.lower().strip() for u in ignored_users}
            if ignored_users is not None
            else set(self.DEFAULT_IGNORED_USERS)
        )
        self.min_length = min_length
        self.max_length = max_length

    def filter_one(self, raw: str) -> ChatMessage | None:
        """
        Принимает сырую строку вида '[user]: text'.
        Возвращает ChatMessage, если сообщение прошло фильтрацию, иначе None.
        """
        if not raw or ":" not in raw:
            return None

        user_part, text_part = raw.split(":", 1)
        user = user_part.strip("[]").strip()
        text = text_part.strip()

        if not user or not text:
            return None

        # 1. Игнорируем чат-ботов
        if user.lower() in self.ignored_users:
            return None

        # 2. Игнорируем чат-команды (!казино, !выпороть и т.д.)
        if text.startswith("!"):
            return None

        # 3. Игнорируем ссылки
        lower_text = text.lower()
        if "http://" in lower_text or "https://" in lower_text or "www." in lower_text:
            return None

        # 4. Проверка длины (слишком короткие не несут смысла, слишком длинные — спам-пасты)
        if len(text) < self.min_length or len(text) > self.max_length:
            return None

        # 5. Должна быть хотя бы одна буква или цифра (отсекает спам скобками/знаками)
        if not any(ch.isalnum() for ch in text):
            return None

        # 6. Отсекаем короткий смех/реакции без текста ("xd", "xdx", "хаха")
        if self._NOISE_RE.match(text):
            return None

        # 7. Фильтр запрещённых слов (банвордов Twitch)
        if any(word in lower_text for word in self.banned_words):
            return None

        return ChatMessage(user=user, text=text)