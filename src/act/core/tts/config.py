from dataclasses import dataclass
from pathlib import Path
import yaml


@dataclass
class TTSConfig:
    engine: str
    fallback: str | None
    engines: dict[str, dict]
    audio: dict

    @classmethod
    def load(cls, path: Path) -> "TTSConfig":
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)["tts"]
        if not data.get("engine"):
            raise ValueError("config/tts.yaml: не задан tts.engine")
        return cls(
            engine=data["engine"],
            fallback=data.get("fallback"),
            engines=data.get("engines", {}),
            audio=data.get("audio", {}),
        )

    def engine_kwargs(self, name: str) -> dict:
        return dict(self.engines.get(name) or {})