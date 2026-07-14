import numpy as np
import hmac
import hashlib
import json
import os
import logging

logger = logging.getLogger("NCS.Shield")

class SecureChannel:
    """
    Simulates a secure communication channel using HMAC-SHA256 signatures
    to ensure data integrity and block False Data Injection (FDI) attacks.
    """
    def __init__(self, secret_key: str = None, env_var: str = "NCS_SECRET_KEY"):
        """
        Initialize the secure channel. Resolves secret key from environment variable if available.
        """
        # Resolve secret key: Environment Variable > Passed Parameter > Hardcoded Default
        env_key = os.environ.get(env_var)
        if env_key:
            logger.info(f"Loaded cryptographic key from environment variable '{env_var}'")
            resolved_key = env_key
        elif secret_key:
            logger.info("Loaded cryptographic key from configuration file")
            resolved_key = secret_key
        else:
            logger.warning("No cryptographic key found! Falling back to default insecure key.")
            resolved_key = "super_secure_consensus_key"
            
        self.secret_key = resolved_key.encode('utf-8')

    def generate_packet(self, agent_id: int, state: np.ndarray, timestamp: float) -> dict:
        """
        Packs the agent state and signs it using HMAC-SHA256.
        """
        state_list = state.flatten().tolist()
        payload = {
            "agent_id": agent_id,
            "state": state_list,
            "timestamp": timestamp
        }
        
        # Serialize payload to create signature
        serialized_payload = json.dumps(payload, sort_keys=True).encode('utf-8')
        signature = hmac.new(self.secret_key, serialized_payload, hashlib.sha256).hexdigest()
        
        return {
            "payload": payload,
            "signature": signature
        }

    def verify_packet(self, packet: dict) -> bool:
        """
        Verifies the cryptographic signature of the packet. Log warnings on failure.
        """
        if not packet or "payload" not in packet or "signature" not in packet:
            logger.warning("Attempted to verify malformed or empty packet.")
            return False
            
        payload = packet["payload"]
        signature = packet["signature"]
        
        # Recalculate signature
        serialized_payload = json.dumps(payload, sort_keys=True).encode('utf-8')
        expected_signature = hmac.new(self.secret_key, serialized_payload, hashlib.sha256).hexdigest()
        
        # Compare in constant-time to avoid timing attacks
        is_valid = hmac.compare_digest(expected_signature, signature)
        if not is_valid:
            logger.warning(
                f"FDI ATTACK DETECTED! Cryptographic signature mismatch "
                f"for agent {payload.get('agent_id')} at time t={payload.get('timestamp')}"
            )
        return is_valid


class DifferentialPrivacy:
    """
    Implements the Laplace Mechanism for Differential Privacy to obfuscate 
    agent states, preserving privacy while maintaining global consensus.
    """
    def __init__(self, epsilon: float = 1.0, sensitivity: float = 0.1):
        """
        Initialize Differential Privacy parameters.
        
        Parameters:
        epsilon (float): Privacy budget (smaller epsilon means more privacy/noise).
        sensitivity (float): Maximum difference in state due to a single agent's change.
        """
        self.epsilon = epsilon
        self.sensitivity = sensitivity
        # Scale parameter of the Laplace distribution: b = sensitivity / epsilon
        self.b = sensitivity / epsilon if epsilon > 0 else 0.0

    def obfuscate_state(self, state: np.ndarray) -> np.ndarray:
        """
        Adds Laplace noise to the state vector.
        
        Parameters:
        state (np.ndarray): Clean state vector.
        
        Returns:
        np.ndarray: Obfuscated state vector.
        """
        if self.b == 0.0:
            return np.copy(state)
            
        state = np.array(state, dtype=float)
        # Generate Laplace noise with the same shape as state
        noise = np.random.laplace(0.0, self.b, size=state.shape)
        return state + noise
