import numpy as np
import scipy.linalg
import scipy.signal

class LQRController:
    """
    Synthesizes LQR controller feedback gains (CARE/DARE) and solves corresponding Lyapunov equations.
    """
    def __init__(self, A: np.ndarray, B: np.ndarray, Q_lqr: np.ndarray, R_lqr: np.ndarray, domain: str = "discrete"):
        self.A = A
        self.B = B
        self.Q_lqr = Q_lqr
        self.R_lqr = R_lqr
        self.domain = domain.lower()
        self.K_fb = None
        self.P_lyap = None
        self.compute_gain()
        
    def compute_gain(self):
        try:
            if self.domain == "continuous":
                # Continuous-time Riccati (CARE): A^T * P + P * A - P * B * R^-1 * B^T * P + Q = 0
                P_are = scipy.linalg.solve_continuous_are(self.A, self.B, self.Q_lqr, self.R_lqr)
                self.K_fb = np.linalg.inv(self.R_lqr) @ self.B.T @ P_are
                
                # Continuous-time Lyapunov: A_cl^T * P + P * A_cl = -I
                A_cl = self.A - self.B @ self.K_fb
                self.P_lyap = scipy.linalg.solve_continuous_lyapunov(A_cl.T, -np.eye(self.A.shape[0]))
            else:
                # Discrete-time Riccati (DARE)
                P_are = scipy.linalg.solve_discrete_are(self.A, self.B, self.Q_lqr, self.R_lqr)
                self.K_fb = np.linalg.inv(self.R_lqr + self.B.T @ P_are @ self.B) @ (self.B.T @ P_are @ self.A)
                
                # Discrete-time Lyapunov: A_cl^T * P * A_cl - P = -I
                A_cl = self.A - self.B @ self.K_fb
                self.P_lyap = scipy.linalg.solve_discrete_lyapunov(A_cl.T, np.eye(self.A.shape[0]))
        except Exception as e:
            n = self.A.shape[0]
            m = self.B.shape[1]
            self.K_fb = np.zeros((m, n))
            self.P_lyap = np.eye(n)
            
    def compute_control(self, x_target: np.ndarray, x_current: np.ndarray, u_feedforward: np.ndarray) -> np.ndarray:
        n = self.A.shape[0]
        m = self.B.shape[1]
        error = x_current.reshape(n, 1) - x_target.reshape(n, 1)
        u_fb = -self.K_fb @ error
        return u_fb + u_feedforward.reshape(m, 1)

    def verify_stability(self):
        """
        Verify stability of closed-loop system A_cl = A - B*K_fb.
        Returns: is_stable, eigvals, stability_index (spectral radius for discrete, max real part for continuous).
        """
        A_cl = self.A - self.B @ self.K_fb
        eigvals = np.linalg.eigvals(A_cl)
        if self.domain == "continuous":
            max_real = np.max(eigvals.real)
            is_stable = bool(max_real < 0.0)
            return is_stable, eigvals, max_real
        else:
            spectral_radius = np.max(np.abs(eigvals))
            is_stable = bool(spectral_radius < 1.0)
            return is_stable, eigvals, spectral_radius


class PIDController:
    """
    Standard PID consensus tracking controller.
    """
    def __init__(self, kp: float = 2.0, ki: float = 0.05, kd: float = 0.5):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.integral_error = np.zeros((2, 1))
        
    def reset(self):
        self.integral_error = np.zeros((2, 1))
        
    def compute_control(self, x_target: np.ndarray, x_current: np.ndarray, u_feedforward: np.ndarray, dt: float = 0.05) -> np.ndarray:
        e_pos = x_current[[0, 2]].reshape(2, 1) - x_target[[0, 2]].reshape(2, 1)
        e_vel = x_current[[1, 3]].reshape(2, 1) - x_target[[1, 3]].reshape(2, 1)
        
        self.integral_error += e_pos * dt
        u_fb = -self.kp * e_pos - self.ki * self.integral_error - self.kd * e_vel
        return u_fb + u_feedforward.reshape(2, 1)


class PolePlacementController:
    """
    Controller that uses Scipy's pole placement algorithm to synthesize custom closed-loop poles.
    """
    def __init__(self, A_d: np.ndarray, B_d: np.ndarray, desired_poles: list):
        self.A_d = A_d
        self.B_d = B_d
        self.desired_poles = desired_poles
        self.K_fb = None
        self.compute_gain()
        
    def compute_gain(self):
        try:
            # Desired poles must be complex conjugates or real
            poles = np.array(self.desired_poles, dtype=complex)
            res = scipy.signal.place_poles(self.A_d, self.B_d, poles)
            self.K_fb = res.gain_matrix
        except Exception as e:
            # Fallback to LQR or zeros
            self.K_fb = np.zeros((2, 4))
            
    def compute_control(self, x_target: np.ndarray, x_current: np.ndarray, u_feedforward: np.ndarray) -> np.ndarray:
        error = x_current.reshape(4, 1) - x_target.reshape(4, 1)
        u_fb = -self.K_fb @ error
        return u_fb + u_feedforward.reshape(2, 1)
