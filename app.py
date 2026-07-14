import os
import json
import logging
from gui.main_window import MainWindow

# Default fallback configuration dict
DEFAULT_CONFIG = {
    "system": {
        "damping": 0.1,
        "dt": 0.05,
        "t_max": 45.0,
        "max_accel": 10.0,
        "max_speed": 15.0
    },
    "noises": {
        "process_noise_diag": [0.0005, 0.005, 0.0005, 0.005],
        "measure_noise_diag": [0.02, 0.02]
    },
    "lqr": {
        "Q_lqr_diag": [10.0, 1.0, 10.0, 1.0],
        "R_lqr_diag": [0.5, 0.5]
    },
    "security": {
        "secret_key_env_var": "NCS_SECRET_KEY",
        "default_secret_key": "super_secure_consensus_key",
        "dp_epsilon": 1.5,
        "dp_sensitivity": 0.15,
        "anomaly_threshold": 5.0,
        "enable_hmac": True,
        "enable_dp": True,
        "enable_anomaly": True,
        "enable_trust": True
    },
    "simulation": {
        "n_followers": 3,
        "initial_positions": [
            [-6.0, 0.0, -6.0, 0.0],
            [6.0,  0.0, -6.0, 0.0],
            [0.0,  0.0,  6.0, 0.0]
        ],
        "leader_orbit_radius": 10.0,
        "leader_orbit_omega": 0.15
    },
    "controller": {
        "type": "LQR",
        "desired_poles": [0.91, 0.91, 0.85, 0.85],
        "pid": {
            "kp": 2.0,
            "ki": 0.05,
            "kd": 0.5
        }
    },
    "observer": {
        "type": "Kalman",
        "desired_poles": [0.8, 0.8, 0.75, 0.75]
    },
    "attacks": {
        "enable_fdi": True,
        "fdi": {
            "start_time": 12.0,
            "end_time": 22.0,
            "offset": [15.0, 0.0, -15.0, 0.0]
        },
        "enable_dos": True,
        "dos": {
            "start_time": 28.0,
            "end_time": 38.0
        },
        "enable_delay": False,
        "delay": {
            "start_time": 50.0,
            "end_time": 60.0,
            "steps": 5
        },
        "enable_replay": False,
        "replay": {
            "start_time": 60.0,
            "end_time": 70.0,
            "window_size": 40
        }
    }
}

import copy

def merge_configs(default: dict, user: dict) -> dict:
    """
    Recursively merges user configuration values into the default configuration template.
    """
    merged = copy.deepcopy(default)
    for k, v in user.items():
        if isinstance(v, dict) and k in merged and isinstance(merged[k], dict):
            merged[k] = merge_configs(merged[k], v)
        else:
            merged[k] = copy.deepcopy(v)
    return merged

def load_config(config_path: str = "config.json") -> dict:
    if not os.path.exists(config_path):
        return copy.deepcopy(DEFAULT_CONFIG)
    try:
        with open(config_path, "r") as f:
            user_config = json.load(f)
        return merge_configs(DEFAULT_CONFIG, user_config)
    except Exception:
        return copy.deepcopy(DEFAULT_CONFIG)

def main():
    logging.basicConfig(level=logging.INFO)
    
    # Load configuration parameters
    config = load_config()
    
    # Launch main CustomTkinter window
    app = MainWindow(config)
    app.mainloop()

if __name__ == "__main__":
    main()
