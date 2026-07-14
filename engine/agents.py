import numpy as np

class PhysicalAgent:
    """
    Simulates the physical dynamics of an agent (LTI continuous plant discretized)
    with control command and speed saturation.
    """
    def __init__(self, agent_id: int, A_d: np.ndarray, B_d: np.ndarray, C_d: np.ndarray, 
                 Q: np.ndarray, R: np.ndarray, initial_state: list, 
                 max_accel: float = 10.0, max_speed: float = 15.0):
        self.agent_id = agent_id
        self.A_d = A_d
        self.B_d = B_d
        self.C_d = C_d
        self.Q = Q
        self.R = R
        self.max_accel = max_accel
        self.max_speed = max_speed
        self.x = np.array(initial_state, dtype=float).reshape(4, 1)
        
    def step(self, u: np.ndarray) -> np.ndarray:
        """
        Propagates physical dynamics one time step forward under process noise
        with actuator and speed saturation limits.
        """
        # Apply Actuator Saturation (limit acceleration)
        u_cmd = np.copy(u)
        u_norm = np.linalg.norm(u_cmd)
        if u_norm > self.max_accel:
            u_cmd = (u_cmd / u_norm) * self.max_accel
            
        w = np.random.multivariate_normal(np.zeros(4), self.Q).reshape(4, 1)
        
        # Propagate dynamics
        self.x = self.A_d @ self.x + self.B_d @ u_cmd + w
        
        # Apply State Saturation (limit velocity)
        v = np.array([self.x[1, 0], self.x[3, 0]])
        v_norm = np.linalg.norm(v)
        if v_norm > self.max_speed:
            v_bounded = (v / v_norm) * self.max_speed
            self.x[1, 0] = v_bounded[0]
            self.x[3, 0] = v_bounded[1]
            
        v_meas = np.random.multivariate_normal(np.zeros(2), self.R).reshape(2, 1)
        y = self.C_d @ self.x + v_meas
        return y
