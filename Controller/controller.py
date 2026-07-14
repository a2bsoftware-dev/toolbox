import numpy as np
from scipy.linalg import solve_discrete_are, solve_discrete_lyapunov

class LQRController:
    """
    An LQR-based state-feedback controller for tracking control
    in a Leader-Follower Networked Control System.
    """
    def __init__(self, A_d, B_d, Q_lqr=None, R_lqr=None):
        """
        Initialize the LQR controller by synthesizing the gain matrix K.
        
        Parameters:
        A_d (np.ndarray): Discrete state transition matrix (n x n)
        B_d (np.ndarray): Discrete input matrix (n x m)
        Q_lqr (np.ndarray, optional): LQR state penalty matrix (n x n). Defaults to identity.
        R_lqr (np.ndarray, optional): LQR control penalty matrix (m x m). Defaults to identity.
        """
        self.A_d = np.array(A_d, dtype=float)
        self.B_d = np.array(B_d, dtype=float)
        
        n = self.A_d.shape[0]
        m = self.B_d.shape[1]
        
        if Q_lqr is None:
            # Penalize position error more than velocity error by default
            self.Q_lqr = np.diag([10.0, 1.0, 10.0, 1.0]) if n == 4 else np.eye(n)
        else:
            self.Q_lqr = np.array(Q_lqr, dtype=float)
            
        if R_lqr is None:
            self.R_lqr = np.eye(m) * 1.0
        else:
            self.R_lqr = np.array(R_lqr, dtype=float)
            
        # Synthesize feedback gain matrix K_fb
        self.K_fb = self._synthesize_gain()

        # Synthesize Lyapunov stability matrix P_lyap solving: A_cl^T * P * A_cl - P = -I
        A_cl = self.A_d - self.B_d @ self.K_fb
        Q_lyap = np.eye(n)
        self.P_lyap = solve_discrete_lyapunov(A_cl, Q_lyap)

    def _synthesize_gain(self):
        """
        Solves the Discrete Algebraic Riccati Equation (DARE) to compute optimal feedback gain.
        """
        # P = A_d^T * P * A_d - A_d^T * P * B_d * (R + B_d^T * P * B_d)^-1 * B_d^T * P * A_d + Q
        P = solve_discrete_are(self.A_d, self.B_d, self.Q_lqr, self.R_lqr)
        # K_fb = (R + B_d^T * P * B_d)^-1 * B_d^T * P * A_d
        K_fb = np.linalg.inv(self.R_lqr + self.B_d.T @ P @ self.B_d) @ (self.B_d.T @ P @ self.A_d)
        return K_fb

    def compute_control(self, x_L, x_hat, u_L=None):
        """
        Compute control input u_i[k] for the follower to track the leader.
        
        Parameters:
        x_L (np.ndarray): State of the leader (n x 1) or flat array.
        x_hat (np.ndarray): Estimated state of the follower (n x 1) or flat array.
        u_L (np.ndarray, optional): Feedforward control input of the leader. Defaults to zeros.
        
        Returns:
        np.ndarray: Control command vector u_i[k] (m x 1)
        """
        n = self.A_d.shape[0]
        m = self.B_d.shape[1]
        
        x_L = np.array(x_L, dtype=float).reshape(n, 1)
        x_hat = np.array(x_hat, dtype=float).reshape(n, 1)
        
        if u_L is None:
            u_L = np.zeros((m, 1))
        else:
            u_L = np.array(u_L, dtype=float).reshape(m, 1)
            
        # Tracking error estimate: e_hat = x_hat - x_L
        # Feedback control law: u = u_L - K_fb * e_hat = u_L + K_fb * (x_L - x_hat)
        u_fb = self.K_fb @ (x_L - x_hat)
        return u_L + u_fb

    def verify_stability(self):
        """
        Verify the Schur stability of the closed-loop system matrix: A_cl = A_d - B_d * K_fb
        
        Returns:
        bool: True if stable (all eigenvalues inside unit circle), False otherwise.
        np.ndarray: Eigenvalues of the closed-loop system matrix.
        float: Spectral radius (maximum magnitude of eigenvalues).
        """
        A_cl = self.A_d - self.B_d @ self.K_fb
        eigenvalues = np.linalg.eigvals(A_cl)
        spectral_radius = np.max(np.abs(eigenvalues))
        is_stable = spectral_radius < 1.0
        return is_stable, eigenvalues, spectral_radius
