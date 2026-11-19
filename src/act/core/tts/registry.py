from act.core.tts.base import TTSEngine

_REGISTRY: dict[str, type] = {}


def register(name: str, cls: type) -> None:
    _REGISTRY[name] = cls


def _ensure_registered() -> None:
    if _REGISTRY:
        return
    from act.core.tts.kokoro_engine import KokoroEngine
    from act.core.tts.silero_engine import SileroEngine
    # from core.tts.edge_engine import EdgeEngine
    register("kokoro", KokoroEngine)
    register("silero", SileroEngine)
    # register("edge", EdgeEngine)


def create_engine(name: str, **kwargs) -> TTSEngine:
    _ensure_registered()
    if name not in _REGISTRY:
        raise ValueError(
            f"Неизвестный TTS-движок: {name}. "
            f"Доступны: {sorted(_REGISTRY)}"
        )
    return _REGISTRY[name](**kwargs)


def list_engines() -> list[str]:
    _ensure_registered()
    return sorted(_REGISTRY)