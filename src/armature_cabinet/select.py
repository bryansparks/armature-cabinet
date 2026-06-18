"""Select skills whose ``when`` overlaps a task string (the woodshop model).

Pure and deterministic: no I/O, no network, no LLM. Returns ranked skill ids
that ``compile_agent(include=...)`` consumes.
"""
from __future__ import annotations
import re

from .model import AgentPackage

# Function words only — never domain/content nouns. Tunable.
_STOPWORDS = frozenset({
    "a", "an", "the", "this", "that", "these", "those",
    "for", "to", "of", "in", "on", "at", "by", "from", "into", "with", "without",
    "and", "or", "but", "as", "than", "then", "so",
    "is", "are", "be", "been", "being", "was", "were",
    "has", "have", "had", "do", "does", "did",
    "can", "could", "should", "would", "may", "might", "will", "shall",
    "it", "its", "they", "their", "them", "we", "you", "your",
    "what", "which", "who", "whom", "when", "where", "why", "how",
    "needs", "need", "needed", "requires", "require", "required", "requiring",
    "set", "get", "go", "use", "using", "used",
})

_TOKEN = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> set[str]:
    """Lowercase, split on non-alphanumeric, drop stopwords and single-char tokens."""
    return {t for t in _TOKEN.findall(text.lower())
            if len(t) > 1 and t not in _STOPWORDS}


def select_skills(pkg: AgentPackage, task: str) -> list[str]:
    """Ids of skills whose ``when`` shares >=1 content keyword with ``task``,
    ranked by overlap count desc; ties broken by source order in ``pkg.skills``.
    Skills with no ``when`` are never selected.
    """
    task_toks = tokenize(task)
    if not task_toks:
        return []
    ranked: list[tuple[int, int, str]] = []  # (score, source_index, id)
    for idx, s in enumerate(pkg.skills):
        if not s.when:
            continue
        score = len(task_toks & tokenize(s.when))
        if score >= 1:
            ranked.append((score, idx, s.id))
    ranked.sort(key=lambda t: (-t[0], t[1]))
    return [sid for _, _, sid in ranked]
