import gymnasium as gym
from gymnasium import spaces
import numpy as np


class MemoryEnv(gym.Env):
    """
    Custom Gymnasium environment for memory consolidation.

    State:  [frequency_norm, recency_score, importance_score]
    Actions: 0=Remove, 1=Store, 2=Reinforce
    Reward:  +1 correct, -1 incorrect
    """

    metadata = {"render_modes": []}

    def __init__(self):
        super().__init__()
        self.observation_space = spaces.Box(
            low=0.0, high=1.0, shape=(3,), dtype=np.float32
        )
        self.action_space = spaces.Discrete(3)
        self.state = np.zeros(3, dtype=np.float32)

    def set_state(self, freq_norm: float, recency: float, importance: float):
        self.state = np.array([freq_norm, recency, importance], dtype=np.float32)

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        self.state = self.observation_space.sample()
        return self.state, {}

    def step(self, action: int):
        importance = float(self.state[2])

        # Define correct action by importance threshold
        if importance >= 0.65:
            correct_action = 1   # STORE
        elif importance >= 0.35:
            correct_action = 2   # REINFORCE
        else:
            correct_action = 0   # REMOVE

        reward = 1.0 if action == correct_action else -1.0
        terminated = True
        truncated = False
        return self.state, reward, terminated, truncated, {"correct": correct_action}

    def action_name(self, action: int) -> str:
        return {0: "REMOVE", 1: "STORE", 2: "REINFORCE"}[action]