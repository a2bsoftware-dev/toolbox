import logging

class EventLogger:
    """
    Stateful logger capturing timeline events during simulation play
    (e.g., '12.00s: FDI Attack Active on Uplink').
    """
    def __init__(self):
        self.events = []
        
    def reset(self):
        self.events = []
        
    def log_event(self, t: float, msg: str):
        event_str = f"{t:.2f}s: {msg}"
        self.events.append(event_str)
        # Log to standard logger too
        logging.getLogger("NCS.Event").info(event_str)
        
    def get_timeline(self) -> list:
        return self.events
