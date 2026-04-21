import numpy as np


class QLearningAgent:
    """
    Tabular Q-learning agent with discretized state space.
    State bins: [freq_norm, recency, importance] each in 5 bins → 125 states.
    Actions: 0=Remove, 1=Store, 2=Reinforce
    """

    BINS = 5
    N_ACTIONS = 3

    def __init__(self, alpha=0.1, gamma=0.9, epsilon=0.3):
        self.alpha = alpha       # learning rate
        self.gamma = gamma       # discount factor
        self.epsilon = epsilon   # exploration rate
        self.q_table = np.zeros((self.BINS, self.BINS, self.BINS, self.N_ACTIONS))
        self.total_reward = 0.0
        self.steps = 0

    def _discretize(self, state: np.ndarray) -> tuple:
        bins = np.linspace(0, 1, self.BINS + 1)[1:-1]
        return tuple(int(np.digitize(s, bins)) for s in state)

    def choose_action(self, state: np.ndarray) -> int:
        if np.random.rand() < self.epsilon:
            return np.random.randint(self.N_ACTIONS)
        s = self._discretize(state)
        return int(np.argmax(self.q_table[s]))

    def learn(self, state: np.ndarray, action: int, reward: float, next_state: np.ndarray):
        s = self._discretize(state)
        ns = self._discretize(next_state)
        best_next = np.max(self.q_table[ns])
        self.q_table[s][action] += self.alpha * (
            reward + self.gamma * best_next - self.q_table[s][action]
        )
        self.total_reward += reward
        self.steps += 1
        # Decay epsilon over time
        self.epsilon = max(0.05, self.epsilon * 0.995)

    def stats(self) -> dict:
        return {
            "steps": self.steps,
            "epsilon": round(self.epsilon, 4),
            "avg_reward": round(self.total_reward / max(self.steps, 1), 4),
        }