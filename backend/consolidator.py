from backend.importance_scorer import compute_importance
from backend.rl_environment import MemoryEnv
import numpy as np


def consolidate(memory_store, rl_agent) -> list[dict]:
    """
    Run the RL agent over all working memory units.
    Based on decisions: promote, reinforce, or remove.
    Returns a log of decisions made.
    """
    env = MemoryEnv()
    units = memory_store.all_working()
    if not units:
        return []

    max_freq = max(u["frequency"] for u in units)
    log = []

    for unit in units:
        freq_norm = unit["frequency"] / max(max_freq, 1)
        recency = unit.get("recency_score", 0.0)
        importance = compute_importance(unit, max_freq)

        state = np.array([freq_norm, recency, importance], dtype=np.float32)
        env.set_state(freq_norm, recency, importance)

        action = rl_agent.choose_action(state)
        _, reward, _, _, info = env.step(action)
        rl_agent.learn(state, action, reward, state)  # single-step, next=same

        action_name = env.action_name(action)

        if action == 1:  # STORE → promote to persistent
            memory_store.promote_to_persistent(unit["concept"])
        elif action == 0:  # REMOVE
            memory_store.remove(unit["concept"])
        # action == 2 → REINFORCE, stays in working memory

        log.append({
            "concept": unit["concept"],
            "importance": importance,
            "action": action_name,
            "reward": reward,
        })

    return log