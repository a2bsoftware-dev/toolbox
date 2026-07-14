import numpy as np
import scipy.linalg as la
from scipy.linalg import solve_discrete_are, solve_discrete_lyapunov

class LQRController:
    """
    An LQR-based state-feedback controller for tracking control
    in a Leader-Follower Networked Control System (Discrete-Time).
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


class Controller:
    """
    Continuous-Time LQR state-feedback controller from the main branch.
    """
    def __init__(self, A, B, initial_state):
        self.A = np.array(A)
        self.B = np.array(B)
        self.x = np.array(initial_state)

        self.K = self.design_controller()

    def design_controller(self):
        Q = np.eye(self.A.shape[0]) * 10
        R = np.eye(self.B.shape[1]) * 1
        P = la.solve_continuous_are(self.A, self.B, Q, R)

        K = la.inv(R) @ self.B.T @ P
        return K

    def compute_control_input(self, x_leader):
        error = self.x - x_leader
        u = -self.K @ error
        return u

    def update_physics(self, u, dt):
        dx = (self.A @ self.x) + (self.B @ u)
        self.x += dt * dx


if __name__ == "__main__":
    import matplotlib.pyplot as plt

    A = [[0, 1],
         [0, 0]]
    B = [[0],
         [1]]

    follower = Controller(A, B, initial_state=[0.0, 0.0])

    leader_state = np.array([10.0, 0.0])

    time_steps = 500
    dt = 0.1

    history_follower_pos = []
    history_leader_pos = []

    for t in range(time_steps):
        if t > 100:
            leader_state[0] += 0.5 * dt 
            leader_state[1] = 0.5 

        u = follower.compute_control_input(leader_state)
        follower.update_physics(u, dt)

        history_follower_pos.append(follower.x[0])
        history_leader_pos.append(leader_state[0])

    plt.figure(figsize=(10, 5))
    plt.plot(history_leader_pos, label="Leader Position", linestyle="--", color="black")
    plt.plot(history_follower_pos, label="Follower Position", color="blue")
    plt.title("Module 1 Test: Drone Tracking")
    plt.xlabel("Time Steps")
    plt.ylabel("Position (Meters)")
    plt.legend()
    plt.grid(True)
    plt.show()
