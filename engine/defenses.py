import os
import hmac
import hashlib
import json
import numpy as np

class SecureChannel:
    """
    Implements cryptographic integrity checks using HMAC-SHA256 signatures.
    """
    def __init__(self, secret_key: str = "super_secure_consensus_key"):
        self.secret_key = secret_key.encode('utf-8')
        
    def generate_packet(self, agent_id: int, state: np.ndarray, timestamp: float) -> dict:
        state_list = state.flatten().tolist()
        payload = {
            "agent_id": agent_id,
            "state": state_list,
            "timestamp": timestamp
        }
        payload_str = json.dumps(payload, sort_keys=True)
        signature = hmac.new(self.secret_key, payload_str.encode('utf-8'), hashlib.sha256).hexdigest()
        return {
            "payload": payload,
            "signature": signature
        }
        
    def verify_packet(self, packet: dict) -> bool:
        if not packet or "payload" not in packet or "signature" not in packet:
            return False
        payload_str = json.dumps(packet["payload"], sort_keys=True)
        expected_sig = hmac.new(self.secret_key, payload_str.encode('utf-8'), hashlib.sha256).hexdigest()
        return hmac.compare_digest(packet["signature"], expected_sig)


class DifferentialPrivacy:
    """
    Applies Gaussian differential privacy perturbation to the agent's telemetry.
    """
    def __init__(self, epsilon: float = 1.5, sensitivity: float = 0.15):
        self.epsilon = epsilon
        self.sensitivity = sensitivity
        
    def obfuscate_state(self, state: np.ndarray) -> np.ndarray:
        if self.epsilon <= 0:
            return np.copy(state)
        # Standard deviation for Gaussian noise based on epsilon and sensitivity
        sigma = self.sensitivity * np.sqrt(2 * np.log(1.25 / 0.1)) / self.epsilon
        noise = np.random.normal(0, sigma, size=state.shape)
        return state + noise


class AnomalyDetector:
    """
    Monitors state residual deviations to flag False Data Injection attacks.
    """
    def __init__(self, threshold: float = 5.0):
        self.threshold = threshold
        self.is_alarm_active = False
        
    def check_anomaly(self, x_received: np.ndarray, x_predicted: np.ndarray) -> bool:
        """
        Returns True if an anomaly (tampered state) is detected.
        """
        residual = np.linalg.norm(x_received.flatten() - x_predicted.flatten())
        if residual > self.threshold:
            self.is_alarm_active = True
            return True # Anomaly detected
        self.is_alarm_active = False
        return False


class TrustFilter:
    """
    Maintains a trust score [0.0, 1.0] for each network node based on message consistency.
    """
    def __init__(self, n_agents: int, decay_rate: float = 0.2, recovery_rate: float = 0.05):
        self.decay_rate = decay_rate
        self.recovery_rate = recovery_rate
        self.trust_scores = {i: 1.0 for i in range(n_agents + 1)}
        
    def update_trust(self, agent_id: int, is_anomalous: bool):
        if is_anomalous:
            self.trust_scores[agent_id] = max(0.0, self.trust_scores[agent_id] - self.decay_rate)
        else:
            self.trust_scores[agent_id] = min(1.0, self.trust_scores[agent_id] + self.recovery_rate)
            
    def is_trusted(self, agent_id: int, cutoff: float = 0.5) -> bool:
        return self.trust_scores.get(agent_id, 1.0) >= cutoff
