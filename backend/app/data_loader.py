import json
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


class KnowledgeBase:
    def __init__(self) -> None:
        self.roots: dict[str, dict[str, Any]] = {}
        self.patterns: dict[str, dict[str, Any]] = {}
        self.words: dict[str, dict[str, Any]] = {}
        self.aliases: dict[str, str] = {}
        self.quiz_templates: dict[str, dict[str, Any]] = {}

        self.words_by_root: dict[str, list[dict[str, Any]]] = {}
        self.words_by_pattern: dict[str, list[dict[str, Any]]] = {}

    def load(self) -> None:
        self.roots = self._load_json("roots.json")
        self.patterns = self._load_json("patterns.json")
        self.words = self._load_json("words.json")
        self.aliases = self._load_json("aliases.json")
        self.quiz_templates = self._load_json("quiz_templates.json")

        self._ensure_ids()
        self._build_indexes()

    def _load_json(self, filename: str) -> Any:
        file_path = DATA_DIR / filename

        if not file_path.exists():
            raise FileNotFoundError(f"Missing data file: {file_path}")

        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)

    def _ensure_ids(self) -> None:
        for root_id, root in self.roots.items():
            root["id"] = root.get("id", root_id)

        for pattern_id, pattern in self.patterns.items():
            pattern["id"] = pattern.get("id", pattern_id)

        for word_id, word in self.words.items():
            word["id"] = word.get("id", word_id)

        for template_id, template in self.quiz_templates.items():
            template["id"] = template.get("id", template_id)

    def _build_indexes(self) -> None:
        self.words_by_root = {}
        self.words_by_pattern = {}

        for word in self.words.values():
            root_id = word.get("root_id")
            pattern_id = word.get("pattern_id")

            if root_id:
                self.words_by_root.setdefault(root_id, []).append(word)

            if pattern_id:
                self.words_by_pattern.setdefault(pattern_id, []).append(word)

    def get_word(self, word_id: str) -> dict[str, Any] | None:
        return self.words.get(word_id)

    def get_root(self, root_id: str) -> dict[str, Any] | None:
        return self.roots.get(root_id)

    def get_pattern(self, pattern_id: str) -> dict[str, Any] | None:
        return self.patterns.get(pattern_id)


kb = KnowledgeBase()