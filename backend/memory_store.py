import time


class MemoryStore:
    """
    Working memory buffer — holds memory units per concept.
    Each unit: { concept, frequency, recency_score, keyword_flag, last_seen }
    """

    def __init__(self):
        self.working_memory: dict[str, dict] = {}
        self.persistent_memory: dict[str, dict] = {}
        self.interaction_count = 0
        self.last_relevant: list[dict] = []

    def update(self, concepts: list[dict]):
        """Add or update concepts in working memory."""
        now = time.time()
        self.interaction_count += 1

        for c in concepts:
            key = c["concept"]
            if key in self.working_memory:
                self.working_memory[key]["frequency"] += 1
                self.working_memory[key]["last_seen"] = now
            else:
                self.working_memory[key] = {
                    "concept": key,
                    "frequency": 1,
                    "keyword_flag": c["keyword_flag"],
                    "last_seen": now,
                }

        self._update_recency_scores(now)

    def _update_recency_scores(self, now: float):
        """Recompute recency for all units (normalized 0–1)."""
        if not self.working_memory:
            return
        times = [v["last_seen"] for v in self.working_memory.values()]
        oldest = min(times)
        newest = max(times)
        span = newest - oldest if newest != oldest else 1.0

        for key, unit in self.working_memory.items():
            unit["recency_score"] = (unit["last_seen"] - oldest) / span

    def get_unit(self, concept: str) -> dict | None:
        return self.working_memory.get(concept)

    def remove(self, concept: str):
        self.working_memory.pop(concept, None)

    def promote_to_persistent(self, concept: str):
        if concept in self.working_memory:
            self.persistent_memory[concept] = self.working_memory.pop(concept)

    def all_working(self) -> list[dict]:
        return list(self.working_memory.values())

    def all_persistent(self) -> list[dict]:
        return list(self.persistent_memory.values())

    def search_memory(self, query: str) -> list[dict]:
        """Search persistent + working memory for relevant concepts."""
        q = query.lower()
        results = []
        seen = set()

        # If query is very short, reuse last relevant context
        if len(q.split()) <= 3 and self.last_relevant:
            return self.last_relevant

        for store in [self.persistent_memory, self.working_memory]:
            for key, unit in store.items():
                if key in seen:
                    continue
                if (
                    key in q
                    or q in key
                    or any(word in key for word in q.split() if len(word) > 3)
                ):
                    results.append(unit)
                    seen.add(key)

        self.last_relevant = results if results else self.last_relevant
        return results
