import numpy as np
import scipy.linalg
import scipy.signal

class LQRController:
    """
    Synthesizes discrete LQR controller feedback gains and solves the discrete Lyapunov equation.
    """
    def __init__(self, A_d: np.ndarray, B_d: np.ndarray, Q_lqr: np.ndarray, R_lqr: np.ndarray):
        self.A_d = A_d
        self.B_d = B_d
        self.Q_lqr = Q_lqr
        self.R_lqr = R_lqr
        self.K_fb = None
        self.P_lyap = None
        self.compute_gain()
        
    def compute_gain(self):
        """
        Solves the Discrete Algebraic Riccati Equation (DARE):
        A_d^T P A_d - P - A_d^T P B_d (R + B_d^T P B_d)^-1 B_d^T P A_d + Q = 0
        and computes the state feedback gain K_fb:
        K_fb = (R + B_d^T P B_d)^-1 B_d^T P A_d
        """
        try:
            P_are = scipy.linalg.solve_discrete_are(self.A_d, self.B_d, self.Q_lqr, self.R_lqr)
            self.K_fb = np.linalg.inv(self.R_lqr + self.B_d.T @ P_are @ self.B_d) @ (self.B_d.T @ P_are @ self.A_d)
            
            # Solve Lyapunov Equation: A_cl^T P_lyap A_cl - P_lyap = -I
            A_cl = self.A_d - self.B_d @ self.K_fb
            self.P_lyap = scipy.linalg.solve_discrete_lyapunov(A_cl.T, np.eye(4))
        except Exception as e:
            # Fallback to simple identity matrix in case LQR fails
            self.K_fb = np.zeros((2, 4))
            self.P_lyap = np.eye(4)
            
    def compute_control(self, x_target: np.ndarray, x_current: np.ndarray, u_feedforward: np.ndarray) -> np.ndarray:
        """
        Computes the state feedback control output command:
        u = u_feedforward - K_fb * (x_current - x_target)
        """
        error = x_current.reshape(4, 1) - x_target.reshape(4, 1)
        u_fb = -self.K_fb @ error
        return u_fb + u_feedforward.reshape(2, 1)

    def verify_stability(self):
        """
        Checks whether the closed-loop matrix A_cl = A_d - B_d * K_fb is Schur stable
        and calculates eigenvalues.
        """
        A_cl = self.A_d - self.B_d @ self.K_fb
        eigvals = np.linalg.eigvals(A_cl)
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
