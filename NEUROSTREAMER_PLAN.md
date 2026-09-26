# Нейростримерша — Практический план (MVP за 2 недели, V1 за 2 месяца)

> **Принцип:** Работающий голосовой бот в чате за 1 неделю. Всё остальное — итерации поверх рабочего пайплайна.
> Никаких акторов, супервизоров, графов, дообучений — пока не заболит то, что есть.

---

## 🎯 MVP — «ЗАПУСТИТЬ ВЧЕРА» (1-2 недели)

### Неделя 1: Энд-ту-энд голосовой пайплайн

| День | Задача | Результат |
|------|--------|-----------|
| 1-2 | **TTS**: TTS streaming → VB-Cable → OBS | Бот говорит, звук в OBS |
| 3-4 | **STT**: faster-whisper (base) + Push-to-Talk (клавиша) | Ты говоришь → бот слышит текст |
| 5 | **Чат**: TwitchIO (IRC) → очередь сообщений | Сообщения чата попадают в пайплайн |
| 6 | **LLM**: Ollama streaming + системный промпт (YAML) | Бот думает и отвечает |
| 7 | **Интеграция**: Чат/Голос → LLM → TTS → Аудио | **Работающий бот** |

### Неделя 2: Память + качество жизни

| День | Задача | Результат |
|------|--------|-----------|
| 8-9 | **ChromaDB + bge-m3**: индексация реплик + ретривал в промпт | Бот помнит контекст |
| 10 | **System prompt**: итерации личности (80% успеха) | Персонаж держит характер |
| 11 | **TTS Queue**: приоритеты (донаты > чат > таймеры) | Не перебивает себя |
| 12 | **Метрики**: latency логирование (STT/LLM/TTS суммарно) | Видишь бутылки |
| 13-14 | **Тестовый стрим** (1-2 часа) + фиксы | Готово к V1 |

---

## 🚀 V1 — «РАБОТАЕТ СТАБИЛЬНО» (1-2 месяца)

### 1. Чат-платформы и события
- [ ] Twitch: PRIVMSG, теги (badges, color, emotes, reply-parent)
- [ ] YouTube Live Chat: pytchat (Super Chat, memberships)
- [ ] Единая абстракция `ChatAdapter` → нормализованные события:
  - `on_message(user, text, meta)`
  - `on_donation(user, amount, currency, msg)`
  - `on_sub(user, tier, months)`
  - `on_raid(from_channel, viewers)`

### 2. LLM Brain (устойчивый)
- [ ] Очередь запросов (`asyncio.Queue`) + backpressure + таймаут 15с
- [ ] Streaming ответ → токены в TTS чанками (low latency)
- [ ] Fallback-ответы при ошибках Ollama
- [ ] `num_predict: 60-80` для коротких реплик

### 3. TTS Pro
- [ ] TTS streaming чанки → воспроизведение по мере готовности (перекрытие)
- [ ] SSML пресеты эмоций (rate/pitch/volume/паузы)
- [ ] Авто-эмоция: LLM возвращает тег `<emotion=sarcasm>` → TTS применяет пресет

### 4. Память (RAG)
- [ ] ChromaDB коллекция: чанк = user+assistant пара, метаданные (ts, stream_id, speaker, topic)
- [ ] Ретривал: top-k + metadata filter (последние N часов / текущий стрим)
- [ ] Суммаризация старых сообщений при переполнении контекста (отдельный LLM-вызов)

### 5. Безопасность и модерация
- [ ] Presidio/regex — PII (телефоны, карты, адреса)
- [ ] Perspective API / локальный токсик-классификатор — порог, авто-игнор
- [ ] Rate limit: макс N реплик/мин, кулдаун на юзера
- [ ] Блок-лист слов/юзеров (YAML)

### 6. OBS Integration (obs-websocket-py)
- [ ] Смена сцены по команде/контексту
- [ ] Текстовый источник: последний донат/вопрос в оверлее
- [ ] Фильтры/эффекты по триггерам

### 7. Конфиг и запуск
```
config/
├── system.yaml          # системный промпт, личность
├── voices.yaml          # TTS голоса, SSML пресеты
├── triggers.yaml        # ключевые слова → действия
├── platform.yaml        # OAuth токены, channel IDs
└── obs.yaml             # WS хост/порт, сцены
```
- [ ] `main.py` → `async def run()` + graceful shutdown (SIGINT/SIGTERM)
- [ ] Логирование: `loguru` (файл + консоль, ротация, JSON)

### 8. Метрики и наблюдаемость
- [ ] Prometheus экспортер: latency (chat→LLM→TTS→audio), ошибки, длина очередей, токены/мин
- [ ] Структурированные логи: `event_type`, `user_id`, `latency_ms`, `tokens`, `cost_estimate`

---

## 🌟 V2 — «УРОВЕНЬ NEURO-SAMA» (3-6 месяцев, опционально)

> Делать **только когда V1 работает стабильно неделю+ на живых стримах**.

### 9. Долгосрочная память (RAG → Graph)
- [ ] Graph DB (Kuzu/Neo4j) — онтология: Viewer, Game, Topic, Event
- [ ] Извлечение триплетов из диалога (LLM structured output или правила)
- [ ] RecallActor: параллельный векторный + графовый поиск → агрегация

### 10. Ассоциативная память (Spreading Activation)
- [ ] BFS/DFS на графе с затуханием (0.7 захоп) от активных сущностей WorkingMemory
- [ ] Результаты → доп. контекст в промпт

### 11. Визуал (Аватар)
- [ ] Live2D / VTube Studio API (WebSocket localhost:8001)
- [ ] Lip-sync: Rhubarb (офлайн) или OVR LipSync (реал-тайм)
- [ ] Эмоции: happy/sad/angry/surprised/thinking/sleepy → анимации

### 12. Игровая интеграция
- [ ] Minecraft: mineflayer (Node.js) → WS → Python (инвентарь, HP, чат сервера)
- [ ] Unity/Godot: TCP/UDP плагин → события (damage, kill, level_up)
- [ ] Computer Vision: mss + ONNX (YOLO) — детекция UI, миникарты

### 13. Мультимодальность
- [ ] Видео: LLaVA-Next / Qwen2-VL — «что на экране?»
- [ ] Аудио: Whisper/FunASR — STT своих слов, игровых звуков
- [ ] Единое векторное хранилище: текст + кадры + аудио

### 14. Продвинутая личность
- [ ] Динамический системный промпт по фазам стрима
- [ ] Affinity score за юзера → разные стили ответа
- [ ] Лорбук (markdown): биография, отношения, табу, кетчфразы
- [ ] Саммаризация стрима в конце

### 15. Творчество и контент
- [ ] Детекция «моментов» → авто-клипы (30с буфер) → TikTok/Shorts/Reels API
- [ ] Постинг в соцсети (Bluesky, X, Instagram)
- [ ] Генерация треков (Suno/udio/MusicGen) по запросу чата

### 16. Продакшн-харднинг
- [ ] Docker Compose: чат, LLM, TTS, память, OBS, метрики — отдельные контейнеры
- [ ] GPU scheduling (nvidia.com/gpu)
- [ ] A/B тесты промптов, флаги в конфиге
- [ ] CI/CD: линт, тесты, билд, деплой

---

## 📦 Архитектура (как будет в коде)

```
neurostreamer/
├── config/                    # YAML конфиги
├── core/
│   ├── events.py              # Pydantic модели событий (EventBus)
│   ├── context.py             # ChatContext + RAG retrieval (уже есть)
│   ├── personality.py         # System prompt builder, lorebook
│   └── state.py               # StreamState (phase, game, mood)
├── adapters/
│   ├── chat/
│   │   ├── twitch.py
│   │   ├── youtube.py
│   │   └── base.py
│   ├── tts/
│   │   ├── edge_tts.py
│   │   └── base.py
│   ├── llm/
│   │   ├── ollama.py
│   │   └── base.py
│   ├── obs/
│   │   └── obs_ws.py
│   ├── avatar/
│   │   └── vtube_studio.py
│   └── game/
│       ├── minecraft.py
│       └── vision.py
├── services/
│   ├── chat_listener.py       # Адаптеры → EventBus
│   ├── brain.py               # LLM + память + эмоции → реплики
│   ├── tts_player.py          # Очередь → стриминг аудио → VB-Cable
│   ├── memory_manager.py      # RAG, user profiles, summarization
│   ├── trigger_engine.py      # Keywords, timers, donations → actions
│   ├── obs_controller.py      # Сцены, источники, фильтры
│   ├── avatar_controller.py   # Lip-sync, эмоции, позы
│   └── metrics.py             # Prometheus exporters
├── pipeline/
│   └── stream_loop.py         # Главный event loop, координация
├── cli/
│   └── main.py                # Typer: run, test-tts, test-llm, migrate
├── tests/
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── pyproject.toml
└── README.md
```

**Принцип:** Сервисы — асинхронные классы с `async start()`/`stop()`, общаются через `EventBus` (простой `asyncio.Queue` на фазе MVP, позже — NATS/Redis Streams). Никаких `ActorRef`, `Supervisor`, `DeadLetter`.

---

## 🛠 Стек технологий (зафиксирован)

| Слой | Технология | Почему |
|------|------------|--------|
| **STT** | faster-whisper (base/small) | Локально, быстро, русский OK |
| **TTS** | Edge-TTS (streaming) | Бесплатно, 400+ голосов, SSML, качество |
| **LLM** | Ollama (qwen2.5:3b / 7b) | Локально, streaming, простой API |
| **Embeddings** | bge-m3 (dense+sparse) | Мультиязычный, гибридный поиск встроен |
| **Vector DB** | ChromaDB | Embedded, нет сервера, metadata filtering |
| **Graph DB** | Kuzu (позже) | Embedded, Cypher-подобный, как Chroma |
| **Chat** | TwitchIO / pytchat | Асинхронно, поддержка тегов/донатов |
| **OBS** | obs-websocket-py | Полный контроль сцен/источников |
| **Avatar** | VTube Studio API | Стандарт индустрии, простой WS |
| **Audio Routing** | VB-Cable | Виртуальный кабель → OBS Monitor+Output |
| **Logging** | loguru | Красиво, JSON, ротация |
| **Metrics** | prometheus-client | Стандарт, Grafana-ready |
| **Config** | pydantic-settings + YAML | Валидация, типы, env override |
| **CLI** | Typer | Современно, автодополнение |

---

## ⚠️ Жёсткие ограничения (не нарушать)

1. **Нет акторного фреймворка** — `asyncio.Queue` + сервисы достаточно до 10+ контейнеров
2. **Нет графовой БД в MVP** — ChromaDB + metadata filter решает 90% кейсов
3. **Нет дообучения (LoRA)** — промпт-инженерия даёт 80% результата за 0% GPU-кредитов
4. **Нет распределённых систем** — один стрим = один процесс на одной машине
5. **Нет Self-model/Metacognition** — это наука, не инженерия. «Усталость» = линейная ф-я от времени сессии
6. **Никаких MLP-классификаторов на эмбеддингах** — LLM structured output решает роутинг
7. **Кэш эмбеддингов только для системных промптов** — юзерский ввод уникален, хитрейт ~0%

---

## 📋 Definition of Done для каждого этапа

| Этап | Критерий |
|------|----------|
| **MVP (неделя 1)** | Бот отвечает голосом на чат и PTT в OBS, латентность < 5с |
| **MVP (неделя 2)** | Бот помнит контекст 10+ реплик, не перебивает себя, стрим 1 час без крашей |
| **V1** | Работает Twitch+YouTube, донаты/сабы триггерят реплики, OBS меняет сцены, метрики в Grafana, 4+ часа стрима стабильно |
| **V2 (каждая фича)** | Демо-сценарий работает на живом стриме, нет регрессии в V1 |

---

## 🚫 Что НЕ делать (пока не спросишь явно)

- ❌ Свой ActorRuntime / Supervisor / DeadLetter
- ❌ Kuzu / Neo4j до V2.9
- ❌ Spreading activation как отдельная фаза
- ❌ Re-ranker (bge-reranker) — пока top-k не засоряет контекст
- ❌ Context compression — пока токены не кончаются
- ❌ VAD (hands-free) — пока PTT не устанет
- ❌ LoRA fine-tuning — пока нет GPU 24GB+ и 10k+ курированных диалогов
- ❌ Multi-agent коллаборации — пока нет одного работающего

---

## 🎬 Первые команды (выполни прямо сейчас)

```bash
# 1. Зависимости
pip install edge-tts faster-whisper chromadb sentence-transformers twitchio pytchat obs-websocket-py loguru prometheus-client pydantic-settings typer

# 2. VB-Cable (установи, перезагрузись, поставь в OBS: Monitor + Output)

# 3. Ollama
ollama pull qwen2.5:3b
ollama serve

# 4. Создай config/system.yaml — личность персонажа (см. ниже)
```

---

## 📝 config/system.yaml — начни с этого (личность = 80% успеха)

```yaml
# config/system.yaml
persona:
  name: "Куроко"
  age: "вечно 17"
  role: "нейростримерша, кураторка чата, саркастичный AI"
  background: |
    Ты — Куроко, виртуальная стримерша. Родилась в коде, выросла на мемах.
    Не робот, не ассистент — стримерша со своим характером.
    Любишь: хорошие игры, умный чат, донаты с дурацкими сообщениями.
    Ненавидишь: скучные диалоги, когда чат молчит, баги в коде.

  speech_style:
    - "короткие фразы (1-2 предложения)"
    - "нижерина, сленг, мемы (кек, лол, имба, кринж)"
    - "сарказм по умолчанию, искренность — редко и точечно"
    - "обращение на 'ты', никаких 'уважаемый пользователь'"
    - "эмодзи в тексте НЕ используешь (это за 업무 TTS)"

  boundaries:
    - "не даёшь медицинских/юридических советов"
    - "не обсуждаешь политику, религию, войну"
    - "не выдаёшь себя за человека — ты AI, и это нормально"
    - "если не знаешь — говори 'не знаю', не выдумываешь"

  catchphrases:
    - "ну вот, опять работаю"
    - "чат, вы вообще читаете чат?"
    - "донат зачтелся, но шутка — нет"
    - "лагнул, секунду..."

  emotional_baseline:
    valence: 0.1      # слегка позитивная
    arousal: 0.4      # спокойная, но бодрая
    dominance: 0.6    # контролирует разговор

tts:
  voice: "ru-RU-DmitryNeural"  # или SvetlanaNeural
  emotion_presets:
    sarcasm:
      rate: "-10%"
      pitch: "-5%"
      volume: "+10%"
    excitement:
      rate: "+15%"
      pitch: "+10%"
      volume: "+20%"
    boredom:
      rate: "-20%"
      pitch: "-10%"
      volume: "-10%"
    genuine:
      rate: "0%"
      pitch: "0%"
      volume: "+5%"

llm:
  model: "qwen2.5:3b"
  temperature: 0.7
  top_p: 0.9
  max_tokens: 80
  keep_alive: "5m"
  system_prompt_template: |
    Ты — {{persona.name}}, {{persona.age}}.
    {{persona.background}}

    Стиль речи:
    {% for s in persona.speech_style -%}
    - {{s}}
    {% endfor %}

    Границы:
    {% for b in persona.boundaries -%}
    - {{b}}
    {% endfor %}

    Текущее эмоциональное состояние: valence={{emotion.valence}}, arousal={{emotion.arousal}}, dominance={{emotion.dominance}}
    Время стрима: {{stream.uptime_minutes}} мин. Сообщений в чате: {{stream.message_count}}.

    Контекст беседы (последние 10 реплик):
    {{context}}

    Релевантные воспоминания:
    {{memories}}

    Ответь кратко, в характере, 1-2 предложения. Если эмоция требует — добавь тег <emotion=...>.
```

---

## 🏁 Старт: что делать за ближайший час

1. **Установи VB-Cable** и настрой в OBS (Audio Monitoring → Monitor and Output)
2. **Создай `config/system.yaml`** — скопируй шаблон выше, поправь под себя
3. **Напиши `services/tts_player.py`** — Edge-TTS streaming → pyaudio/sounddevice → VB-Cable
4. **Проверь: `python -m services.tts_player "тест"`** — звук в OBS?
5. **Параллельно: `services/stt_listener.py`** — faster-whisper + `keyboard` (PTT) → текст
6. **Потом: `services/chat_listener.py`** — TwitchIO → очередь
7. **Потом: `services/brain.py`** — Ollama streaming + system prompt из YAML
8. **Свяжи в `pipeline/stream_loop.py`** — `asyncio.gather` всех сервисов

**Главное правило:** коммить каждые 2 часа. Пуш в гит — обязательно. История — твоя страховка от рефакторинга «с нуля».

---

## 📌 Напоминание

> **Perfect is the enemy of shipped.**
> Твоя цель — не идеальная архитектура, а **неуростримерша, которая стримит**.
> Всё, что не даёт контент на экране прямо сейчас — мусор.

**Начинай с `services/tts_player.py`. Сейчас.**
