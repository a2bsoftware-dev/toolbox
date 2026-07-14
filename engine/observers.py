import numpy as np
import scipy.signal

class KalmanFilter:
    """
    Implements a discrete-time Linear Kalman Filter observer for 2D position-velocity tracking.
    """
    def __init__(self, A_d: np.ndarray, B_d: np.ndarray, C_d: np.ndarray, 
                 Q: np.ndarray, R: np.ndarray, x0: np.ndarray = None):
        self.A_d = A_d
        self.B_d = B_d
        self.C_d = C_d
        self.Q = Q
        self.R = R
        self.x_est = x0.reshape(4, 1) if x0 is not None else np.zeros((4, 1))
        self.P = np.eye(4) * 0.1
        
    def predict(self, u: np.ndarray):
        """
        Prediction Phase:
        x_est_minus = A_d * x_est_prev + B_d * u
        P_minus = A_d * P_prev * A_d^T + Q
        """
        self.x_est = self.A_d @ self.x_est + self.B_d @ u.reshape(2, 1)
        self.P = self.A_d @ self.P @ self.A_d.T + self.Q
        
    def update(self, y: np.ndarray) -> np.ndarray:
        """
        Correction Phase:
        K = P_minus * C_d^T * (C_d * P_minus * C_d^T + R)^-1
        x_est = x_est_minus + K * (y - C_d * x_est_minus)
        P = (I - K * C_d) * P_minus
        """
        y_meas = y.reshape(2, 1)
        S = self.C_d @ self.P @ self.C_d.T + self.R
        K_gain = self.P @ self.C_d.T @ np.linalg.inv(S)
        
        innovation = y_meas - self.C_d @ self.x_est
        self.x_est = self.x_est + K_gain @ innovation
        self.P = (np.eye(4) - K_gain @ self.C_d) @ self.P
        return self.x_est
        
    def get_state(self) -> np.ndarray:
        return self.x_est.flatten()


class LuenbergerObserver:
    """
    Implements a discrete-time Luenberger Observer:
    x_est[k+1] = A_d*x_est[k] + B_d*u[k] + L*(y[k] - C_d*x_est[k])
    The gain matrix L is computed by placing eigenvalues of A_d - L*C_d.
    """
    def __init__(self, A_d: np.ndarray, B_d: np.ndarray, C_d: np.ndarray, 
                 desired_observer_poles: list, x0: np.ndarray = None):
        self.A_d = A_d
        self.B_d = B_d
        self.C_d = C_d
        self.x_est = x0.reshape(4, 1) if x0 is not None else np.zeros((4, 1))
        self.L = None
        self.desired_poles = desired_observer_poles
        self.compute_gain()
        
    def compute_gain(self):
        """
        Uses duality to perform pole placement for observer gain L:
        Place poles of A_d^T - C_d^T * L_T
        """
        try:
            poles = np.array(self.desired_poles, dtype=complex)
            res = scipy.signal.place_poles(self.A_d.T, self.C_d.T, poles)
            self.L = res.gain_matrix.T
        except Exception as e:
            # Fallback to simple default gain matrix
            self.L = np.zeros((4, 2))
            self.L[0, 0] = 0.5
            self.L[2, 1] = 0.5
            
    def predict(self, u: np.ndarray):
        # Propagation is handled together with correction in the update step for ZOH Luenberger,
        # but to keep API compatibility with Kalman, we save the control input u.
        self.last_u = u.reshape(2, 1)
        
    def update(self, y: np.ndarray) -> np.ndarray:
        y_meas = y.reshape(2, 1)
        # x_est[k+1] = A_d*x_est[k] + B_d*u[k] + L*(y[k] - C_d*x_est[k])
        innovation = y_meas - self.C_d @ self.x_est
        self.x_est = self.A_d @ self.x_est + self.B_d @ self.last_u + self.L @ innovation
        return self.x_est
        
    def get_state(self) -> np.ndarray:
        return self.x_est.flatten()
