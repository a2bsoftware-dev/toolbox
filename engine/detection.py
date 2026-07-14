import numpy as np

class IntrusionDetectionSystem:
    """
    Intrusion Detection System (IDS) monitoring telemetry anomalies.
    Computes residual deviations to calculate the probability of an active cyber attack.
    """
    def __init__(self, fdi_threshold: float = 4.0, replay_threshold: float = 0.5):
        self.fdi_threshold = fdi_threshold
        self.replay_threshold = replay_threshold
        self.last_states = {}
        
    def reset(self):
        self.last_states = {}
        
    def detect_fdi(self, x_received: np.ndarray, x_predicted: np.ndarray) -> float:
        """
        Computes residual error between received state and model-based prediction.
        Returns a probability of FDI attack [0.0, 1.0].
        """
        residual = np.linalg.norm(x_received.flatten() - x_predicted.flatten())
        if residual >= self.fdi_threshold:
            # High certainty of FDI if residual exceeds threshold
            return min(1.0, 0.5 + (residual - self.fdi_threshold) / self.fdi_threshold)
        return max(0.0, (residual / self.fdi_threshold) * 0.3)
        
    def detect_replay(self, agent_id: int, x_received: np.ndarray) -> float:
        """
        Detects replay attacks by monitoring state variance. If the state is
        suspiciously static or matches historical values exactly under noise, it flags it.
        """
        x_flat = x_received.flatten()
        if agent_id not in self.last_states:
            self.last_states[agent_id] = []
            
        # Check against cached states
        matches = 0
        for cached in self.last_states[agent_id]:
            diff = np.linalg.norm(x_flat - cached)
            if diff < self.replay_threshold:
                matches += 1
                
        # Cache current state
        self.last_states[agent_id].append(np.copy(x_flat))
        if len(self.last_states[agent_id]) > 30:
            self.last_states[agent_id].pop(0)
            
        if len(self.last_states[agent_id]) < 10:
            return 0.0 # Insufficient data
            
        # Replay probability increases with redundant static matches
        match_ratio = matches / len(self.last_states[agent_id])
        if match_ratio > 0.4:
            return min(1.0, (match_ratio - 0.4) / 0.4)
        return 0.0
        
    def detect_dos(self, packet_received: bool) -> float:
        """
        Returns DoS attack probability (1.0 if packet is missing, 0.0 otherwise).
        """
        return 0.0 if packet_received else 1.0
