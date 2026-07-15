import numpy as np
import scipy.linalg as la

def continuous_matrices(damping: float) -> tuple:
    """
    Returns the continuous-time (A, B, C) double-integrator-with-drag plant model
    shared by the simulator and every GUI panel that needs to preview/edit it.
    """
    A = np.array([
        [0.0, 1.0, 0.0, 0.0],
        [0.0, -damping, 0.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
        [0.0, 0.0, 0.0, -damping]
    ])
    B = np.array([
        [0.0, 0.0],
        [1.0, 0.0],
        [0.0, 0.0],
        [0.0, 1.0]
    ])
    C = np.array([
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0]
    ])
    return A, B, C

def euler_discrete_matrices(damping: float, dt: float) -> tuple:
    """
    Returns the (A_d, B_d) first-order Euler discretization of the plant model,
    used when the simulator/GUI is configured to interpret parameters as discrete-time directly.
    """
    A_d = np.array([
        [1.0, dt, 0.0, 0.0],
        [0.0, 1.0 - damping * dt, 0.0, 0.0],
        [0.0, 0.0, 1.0, dt],
        [0.0, 0.0, 0.0, 1.0 - damping * dt]
    ])
    B_d = np.array([
        [0.0, 0.0],
        [dt, 0.0],
        [0.0, 0.0],
        [0.0, dt]
    ])
    return A_d, B_d

def zoh_discretize(A: np.ndarray, B: np.ndarray, dt: float) -> tuple:
    """
    Computes exact Zero-Order Hold (ZOH) discretization for a continuous state-space model:
    x_dot = A*x + B*u  ==>  x[k+1] = A_d*x[k] + B_d*u[k]
    Using matrix exponential block form.
    """
    n = A.shape[0]
    m = B.shape[1]
    M = np.zeros((n + m, n + m))
    M[:n, :n] = A
    M[:n, n:] = B
    M_exp = la.expm(M * dt)
    A_d = M_exp[:n, :n]
    B_d = M_exp[:n, n:]
    return A_d, B_d
