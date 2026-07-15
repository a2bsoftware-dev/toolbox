import numpy as np
from collections import deque

class AttackSimulator:
    """
    Simulates cyber-layer attacks on telemetry packet routing.
    """
    def __init__(self, fdi_offset: list = None, replay_window_size: int = 40, delay_steps: int = 5):
        self.fdi_offset = np.array(fdi_offset) if fdi_offset is not None else np.array([15.0, 0.0, -15.0, 0.0])
        self.replay_window_size = replay_window_size
        self.delay_steps = delay_steps
        
        # Cache queues for delay and replay attacks
        self.delay_queues = {}
        self.replay_cache = {}
        self.replay_active_index = {}
        
    def reset(self):
        self.delay_queues = {}
        self.replay_cache = {}
        self.replay_active_index = {}
        
    def apply_fdi(self, packet: dict, is_defended: bool) -> dict:
        """
        False Data Injection (FDI): injects bias offset in transit.
        """
        import copy
        corrupted = copy.deepcopy(packet)
        if "payload" in corrupted and is_defended:
            corrupted["payload"]["state"] = (np.array(corrupted["payload"]["state"]) + self.fdi_offset).tolist()
        else:
            corrupted["state"] = (np.array(corrupted["state"]) + self.fdi_offset).tolist()
        return corrupted
        
    def apply_delay(self, agent_id: int, packet: dict) -> dict:
        """
        Delay Attack: buffers packets and returns the packet from N steps ago.
        """
        if agent_id not in self.delay_queues:
            self.delay_queues[agent_id] = deque(maxlen=self.delay_steps + 1)
            
        self.delay_queues[agent_id].append(packet)
        
        # If queue is full, return delayed packet; else return None (effectively packet loss/ZOH)
        if len(self.delay_queues[agent_id]) > self.delay_steps:
            return self.delay_queues[agent_id][0]
        return None
        
    def apply_replay(self, agent_id: int, packet: dict, is_attack_active: bool) -> dict:
        """
        Replay Attack: caches clean telemetry, then loops recorded values during attack.
        """
        if agent_id not in self.replay_cache:
            self.replay_cache[agent_id] = []
            self.replay_active_index[agent_id] = 0
            
        if not is_attack_active:
            # Cache valid packet
            self.replay_cache[agent_id].append(packet)
            if len(self.replay_cache[agent_id]) > self.replay_window_size:
                self.replay_cache[agent_id].pop(0)
            return packet
        else:
            # Playback cached packets
            cache = self.replay_cache[agent_id]
            if len(cache) == 0:
                return packet # Fallback if empty
            idx = self.replay_active_index[agent_id]
            replayed_packet = cache[idx % len(cache)]
            self.replay_active_index[agent_id] += 1
            return replayed_packet
