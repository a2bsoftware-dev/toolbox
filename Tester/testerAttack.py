import numpy as np
import random

class testAttackSimulation:
    def __init__(self):
   
        self.attack_active = True

    def false_data_injection(self, true_leader_state, offset=5.0):
        """
        FDI Attack: Adds a fake offset to the leader's position.
        """
        if not self.attack_active:
            return true_leader_state
            
        malicious_offset = np.array([offset, 0.0])
        corrupted_state = true_leader_state + malicious_offset
        
        return corrupted_state

    def denial_of_service(self, true_leader_state, last_known_state, drop_rate=0.8):
        """
        DoS Attack: Simulates packet loss. 
        If a packet is dropped, the drone only has the old data to look at.
        """
        if not self.attack_active:
            return true_leader_state

        if random.random() < drop_rate:
            return last_known_state
        else:
            return true_leader_state


