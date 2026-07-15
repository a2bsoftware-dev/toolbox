import os
import json
import logging
import copy

logger = logging.getLogger("NCS.Config")

# Default template configuration dictionary
DEFAULT_CONFIG = {
    "system": {
        "damping": 0.1,
        "dt": 0.05,
        "t_max": 45.0,
        "max_accel": 10.0,
        "max_speed": 15.0,
        "model_domain": "continuous"
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
        "replay_threshold": 0.5,
        "trust_decay_rate": 0.2,
        "trust_recovery_rate": 0.05,
        "trust_cutoff": 0.5,
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

def merge_configs(default: dict, user: dict) -> dict:
    merged = copy.deepcopy(default)
    for k, v in user.items():
        if isinstance(v, dict) and k in merged and isinstance(merged[k], dict):
            merged[k] = merge_configs(merged[k], v)
        else:
            merged[k] = copy.deepcopy(v)
    return merged

def normalize_simulation_duration(config: dict) -> dict:
    """
    Extends t_max so the simulation always runs 10s past the latest end_time among
    attacks the user actually has enabled. Without this, an attack window configured
    later than t_max (e.g. the default Delay/Replay windows at 50-70s) would never
    actually fire, since the simulation would already have stopped. Only ever grows
    t_max - never shrinks a duration the user configured to be longer.
    """
    attacks = config.get("attacks", {})
    end_times = []
    for key in ("fdi", "dos", "delay", "replay"):
        if attacks.get(f"enable_{key}", False):
            end_time = attacks.get(key, {}).get("end_time")
            if end_time is not None:
                end_times.append(end_time)
    if end_times:
        required = max(end_times) + 10.0
        if config["system"]["t_max"] < required:
            config["system"]["t_max"] = required
    return config

def load_config(config_path: str = "config.json") -> dict:
    if not os.path.exists(config_path):
        logger.warning(f"Configuration file '{config_path}' not found. Using template default configuration.")
        return normalize_simulation_duration(copy.deepcopy(DEFAULT_CONFIG))
    try:
        with open(config_path, 'r') as f:
            user_config = json.load(f)
        logger.info(f"Successfully loaded configuration from '{config_path}'")
        return normalize_simulation_duration(merge_configs(DEFAULT_CONFIG, user_config))
    except Exception as e:
        logger.error(f"Error parsing configuration file '{config_path}': {e}. Using baseline fallback config.")
        return normalize_simulation_duration(copy.deepcopy(DEFAULT_CONFIG))

def load_env(env_path: str = ".env"):
    if os.path.exists(env_path):
        try:
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#') or '=' not in line:
                        continue
                    key, val = line.split('=', 1)
                    os.environ[key.strip()] = val.strip()
            logger.info(f"Loaded environment variables from '{env_path}'")
        except Exception as e:
            logger.error(f"Error loading environment file '{env_path}': {e}")
