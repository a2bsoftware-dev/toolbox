import numpy as np

class PerformanceMetrics:
    """
    Computes performance indices for NCS control quality assessment.
    """
    @staticmethod
    def compute_rmse(errors: list) -> float:
        """
        Calculates Root Mean Square Error.
        """
        if not errors:
            return 0.0
        return float(np.sqrt(np.mean(np.array(errors)**2)))
        
    @staticmethod
    def compute_mae(errors: list) -> float:
        """
        Calculates Mean Absolute Error.
        """
        if not errors:
            return 0.0
        return float(np.mean(np.abs(np.array(errors))))
        
    @staticmethod
    def compute_max_error(errors: list) -> float:
        """
        Calculates peak tracking consensus error.
        """
        if not errors:
            return 0.0
        return float(np.max(np.abs(np.array(errors))))
        
    @staticmethod
    def compute_energy(inputs: list, dt: float = 0.05) -> float:
        """
        Calculates control effort energy index: sum(||u_k||^2) * dt
        """
        if not inputs:
            return 0.0
        return float(np.sum(np.array(inputs)**2) * dt)
        
    @staticmethod
    def compute_settling_time(time_grid: list, errors: list, attack_end_time: float = 22.0, threshold: float = 1.5):
        """
        Calculates the recovery settling time after an attack window: the duration (in seconds)
        it takes for the error to return and remain below a threshold.

        Returns None if the error is still above threshold at the very end of the recorded
        window (i.e. it never actually settled - this must be distinguished from a real,
        finite settling time, otherwise a signal that never recovers reports a plausible-looking
        but false "settled at t=<end of window>" duration).
        """
        if not time_grid or not errors:
            return None

        post_attack_indices = [idx for idx, t in enumerate(time_grid) if t > attack_end_time]
        if not post_attack_indices:
            return 0.0

        if errors[post_attack_indices[-1]] > threshold:
            return None  # still not settled by the end of the recorded window

        settled_t = None
        # Find the last time the error exceeded the threshold after the attack ended
        for idx in reversed(post_attack_indices):
            if errors[idx] > threshold:
                settled_t = time_grid[idx]
                break

        if settled_t is not None:
            settling_val = settled_t - attack_end_time
            return max(0.0, settling_val)
        return 0.0  # Settled instantly
