import numpy as np

class KalmanFilter:
    """
    An implementation of a Discrete-Time Kalman Filter for state estimation
    of a single agent in a double-integrator plant with environmental noise.
    """
    def __init__(self, A_d, B_d, C_d, Q, R, x0=None, P0=None):
        """
        Initialize the Kalman Filter.
        
        Parameters:
        A_d (np.ndarray): State transition matrix (n x n)
        B_d (np.ndarray): Control input matrix (n x m)
        C_d (np.ndarray): Observation matrix (r x n)
        Q (np.ndarray): Process noise covariance matrix (n x n)
        R (np.ndarray): Measurement noise covariance matrix (r x r)
        x0 (np.ndarray, optional): Initial state estimate (n x 1). Defaults to zeros.
        P0 (np.ndarray, optional): Initial error covariance matrix (n x n). Defaults to identity.
        """
        self.A_d = np.array(A_d, dtype=float)
        self.B_d = np.array(B_d, dtype=float)
        self.C_d = np.array(C_d, dtype=float)
        self.Q = np.array(Q, dtype=float)
        self.R = np.array(R, dtype=float)
        
        n = self.A_d.shape[0]
        self.x = np.zeros((n, 1)) if x0 is None else np.array(x0, dtype=float).reshape(n, 1)
        self.P = np.eye(n) * 1.0 if P0 is None else np.array(P0, dtype=float)
        
        # Predicted state and covariance (prior)
        self.x_prior = np.copy(self.x)
        self.P_prior = np.copy(self.P)

    def predict(self, u):
        """
        Prediction step of the Kalman Filter.
        Computes the a priori state estimate and error covariance.
        
        Parameters:
        u (np.ndarray): Control input command vector (m x 1) or flat array.
        
        Returns:
        np.ndarray: Predicted state estimate (n x 1)
        """
        m = self.B_d.shape[1]
        u = np.array(u, dtype=float).reshape(m, 1)
        
        # x_prior = A_d * x + B_d * u
        self.x_prior = self.A_d @ self.x + self.B_d @ u
        # P_prior = A_d * P * A_d^T + Q
        self.P_prior = self.A_d @ self.P @ self.A_d.T + self.Q
        
        # Set current state and covariance to the prior in case update is not called
        self.x = np.copy(self.x_prior)
        self.P = np.copy(self.P_prior)
        
        return self.x_prior

    def update(self, y):
        """
        Correction / Measurement Update step of the Kalman Filter.
        Computes the a posteriori state estimate and error covariance.
        
        Parameters:
        y (np.ndarray): Noisy sensor measurement telemetry (r x 1) or flat array.
        
        Returns:
        np.ndarray: Updated state estimate (n x 1)
        """
        r = self.C_d.shape[0]
        y = np.array(y, dtype=float).reshape(r, 1)
        
        # Innovation (measurement residual)
        innovation = y - self.C_d @ self.x_prior
        
        # Innovation covariance
        S = self.C_d @ self.P_prior @ self.C_d.T + self.R
        
        # Optimal Kalman Gain
        K = self.P_prior @ self.C_d.T @ np.linalg.inv(S)
        
        # Update state estimate (a posteriori)
        self.x = self.x_prior + K @ innovation
        
        # Update error covariance (a posteriori)
        n = self.A_d.shape[0]
        I = np.eye(n)
        self.P = (I - K @ self.C_d) @ self.P_prior
        
        return self.x

    def get_state(self):
        """
        Get the current state estimate as a flat array.
        """
        return self.x.flatten()

    def get_covariance(self):
        """
        Get the current error covariance.
        """
        return self.P
