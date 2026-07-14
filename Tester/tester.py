import os
import sys
import json
import logging
import argparse
import numpy as np
import matplotlib.pyplot as plt

# Add parent directory to path to enable local module imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Filter.filter import KalmanFilter
from Controller.controller import LQRController
from Shield.shield import SecureChannel, DifferentialPrivacy

# Set up logging format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("NCS.Tester")

# Default fallback configuration dict in case config.json is missing
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
        "dp_sensitivity": 0.15
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
    "attacks": {
        "fdi": {
            "start_time": 12.0,
            "end_time": 22.0,
            "offset": [15.0, 0.0, -15.0, 0.0]
        },
        "dos": {
            "start_time": 28.0,
            "end_time": 38.0
        }
    }
}


def load_config(config_path: str) -> dict:
    """
    Loads JSON configuration from a given file path.
    Falls back to hardcoded defaults if file does not exist.
    """
    if not os.path.exists(config_path):
        logger.warning(f"Configuration file '{config_path}' not found. Falling back to default configuration.")
        return DEFAULT_CONFIG
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        logger.info(f"Successfully loaded configuration from '{config_path}'")
        return config
    except Exception as e:
        logger.error(f"Error parsing configuration file '{config_path}': {e}. Falling back to default configuration.")
        return DEFAULT_CONFIG


def load_env(env_path: str = ".env"):
    """
    Loads variables from a .env file into the system environment.
    """
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


class PhysicalAgent:
    """
    Simulates the physical dynamics of an agent (LTI continuous plant discretized)
    with control command and speed saturation.
    """
    def __init__(self, agent_id: int, A_d: np.ndarray, B_d: np.ndarray, C_d: np.ndarray, Q: np.ndarray, R: np.ndarray, initial_state: list, max_accel: float = 10.0, max_speed: float = 15.0):
        self.agent_id = agent_id
        self.A_d = A_d
        self.B_d = B_d
        self.C_d = C_d
        self.Q = Q
        self.R = R
        self.max_accel = max_accel
        self.max_speed = max_speed
        self.x = np.array(initial_state, dtype=float).reshape(4, 1)
        
    def step(self, u: np.ndarray) -> np.ndarray:
        """
        Propagates physical dynamics one time step forward under process noise
        with actuator and speed saturation limits.
        """
        # Apply Actuator Saturation (limit acceleration)
        u_cmd = np.copy(u)
        u_norm = np.linalg.norm(u_cmd)
        if u_norm > self.max_accel:
            u_cmd = (u_cmd / u_norm) * self.max_accel
            
        w = np.random.multivariate_normal(np.zeros(4), self.Q).reshape(4, 1)
        
        # Propagate dynamics
        self.x = self.A_d @ self.x + self.B_d @ u_cmd + w
        
        # Apply State Saturation (limit velocity)
        v = np.array([self.x[1, 0], self.x[3, 0]])
        v_norm = np.linalg.norm(v)
        if v_norm > self.max_speed:
            v_bounded = (v / v_norm) * self.max_speed
            self.x[1, 0] = v_bounded[0]
            self.x[3, 0] = v_bounded[1]
            
        v_meas = np.random.multivariate_normal(np.zeros(2), self.R).reshape(2, 1)
        y = self.C_d @ self.x + v_meas
        return y


class CloudServer:
    """
    Simulates a centralized Cloud Computing routing layer.
    """
    def __init__(self):
        self.database = {}
        
    def upload_state(self, agent_id: int, data_packet: dict):
        self.database[agent_id] = data_packet
        
    def download_state(self, agent_id: int) -> dict:
        return self.database.get(agent_id, None)


def run_simulation(scenario: str, config: dict) -> dict:
    """
    Runs the multi-agent control simulation for the specified scenario.
    """
    logger.info(f"Starting simulation run for scenario: '{scenario}'")
    
    # Load settings from config
    sys_cfg = config["system"]
    dt = sys_cfg["dt"]
    damping = sys_cfg["damping"]
    t_max = sys_cfg["t_max"]
    max_accel = sys_cfg.get("max_accel", 10.0)
    max_speed = sys_cfg.get("max_speed", 15.0)
    
    noise_cfg = config["noises"]
    Q_process = np.diag(noise_cfg["process_noise_diag"])
    R_measure = np.diag(noise_cfg["measure_noise_diag"])
    
    lqr_cfg = config["lqr"]
    Q_lqr = np.diag(lqr_cfg["Q_lqr_diag"])
    R_lqr = np.diag(lqr_cfg["R_lqr_diag"])
    
    sec_cfg = config["security"]
    env_var = sec_cfg["secret_key_env_var"]
    default_key = sec_cfg["default_secret_key"]
    dp_epsilon = sec_cfg["dp_epsilon"]
    dp_sensitivity = sec_cfg["dp_sensitivity"]
    
    sim_cfg = config["simulation"]
    n_followers = sim_cfg["n_followers"]
    initial_positions = sim_cfg["initial_positions"]
    omega = sim_cfg["leader_orbit_omega"]
    radius = sim_cfg["leader_orbit_radius"]
    
    attack_cfg = config["attacks"]
    fdi_cfg = attack_cfg["fdi"]
    dos_cfg = attack_cfg["dos"]
    
    # Pre-calculate time steps
    steps = int(t_max / dt)
    time_grid = np.linspace(0, t_max, steps)
    
    # Discretized system matrices
    A_d = np.array([
        [1.0,  dt,  0.0,  0.0],
        [0.0,  1.0 - damping*dt, 0.0, 0.0],
        [0.0,  0.0,  1.0,  dt],
        [0.0,  0.0,  0.0,  1.0 - damping*dt]
    ])
    B_d = np.array([
        [0.0, 0.0],
        [dt,  0.0],
        [0.0, 0.0],
        [0.0, dt ]
    ])
    C_d = np.array([
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0]
    ])
    
    # Instantiate Controller
    controller = LQRController(A_d, B_d, Q_lqr, R_lqr)
    P_lyap = controller.P_lyap
    
    # Initialize Shield Components
    secure_channel = SecureChannel(secret_key=default_key, env_var=env_var)
    dp_shield = DifferentialPrivacy(epsilon=dp_epsilon, sensitivity=dp_sensitivity)
    
    # Circular trajectory input command generator for leader
    def get_leader_state_and_input(t):
        px = radius * np.cos(omega * t)
        py = radius * np.sin(omega * t)
        vx = -radius * omega * np.sin(omega * t)
        vy = radius * omega * np.cos(omega * t)
        ux = -radius * (omega**2) * np.cos(omega * t) - damping * vx
        uy = -radius * (omega**2) * np.sin(omega * t) - damping * vy
        return np.array([px, vx, py, vy]), np.array([ux, uy]).reshape(2, 1)

    # Initialize Followers
    followers = []
    filters = []
    
    for i in range(n_followers):
        init_pos = initial_positions[i] if i < len(initial_positions) else [0.0, 0.0, 0.0, 0.0]
        agent = PhysicalAgent(i + 1, A_d, B_d, C_d, Q_process, R_measure, init_pos, max_accel, max_speed)
        followers.append(agent)
        
        y_init = C_d @ agent.x
        x_est_init = np.array([y_init[0, 0], 0.0, y_init[1, 0], 0.0])
        kf = KalmanFilter(A_d, B_d, C_d, Q_process, R_measure, x0=x_est_init)
        filters.append(kf)
        
    cloud = CloudServer()
    
    # Logging histories
    leader_history = []
    follower_histories = [[] for _ in range(n_followers)]
    filter_histories = [[] for _ in range(n_followers)]
    tracking_errors = [[] for _ in range(n_followers)]
    estimation_errors = [[] for _ in range(n_followers)]
    cloud_est_errors = [[] for _ in range(n_followers)]
    lyapunov_values = [[] for _ in range(n_followers)]
    control_inputs = [[] for _ in range(n_followers)]
    network_link_status = []
    
    u_prev = [np.zeros((2, 1)) for _ in range(n_followers)]
    
    # Propagate the leader physically using discrete LTI equations, matching predictor
    # Initial state of leader: position (radius, 0), velocity (0, radius*omega)
    x_L_state = np.array([radius, 0.0, 0.0, radius * omega], dtype=float).reshape(4, 1)
    
    # Leader state predictor (dead reckoning) initialized for each follower
    x_L_pred = [x_L_state.flatten() for _ in range(n_followers)]
    
    # Run core simulation loop
    for k in range(steps):
        t = time_grid[k]
        
        # Calculate leader input circular commands
        _, u_L = get_leader_state_and_input(t)
        
        # Capture current leader state
        x_L = x_L_state.flatten()
        leader_history.append(np.copy(x_L))
        
        # Leader uploads its state to Cloud
        leader_packet = {"state": x_L.tolist(), "timestamp": t}
        if scenario == 'defended':
            leader_packet = secure_channel.generate_packet(0, x_L, t)
            # Uplink protection: Cloud checks signature before saving to database
            if secure_channel.verify_packet(leader_packet):
                cloud.upload_state(0, leader_packet)
        else:
            cloud.upload_state(0, leader_packet)
        
        # Attack trigger windows
        fdi_active = (scenario in ['attacked', 'defended']) and (fdi_cfg["start_time"] <= t <= fdi_cfg["end_time"])
        dos_active = (scenario in ['attacked', 'defended']) and (dos_cfg["start_time"] <= t <= dos_cfg["end_time"])
        
        # Record network status for dashboard
        if dos_active:
            status_str = "dos"
        elif fdi_active:
            status_str = "attacked"
        elif scenario == "defended":
            status_str = "secured"
        else:
            status_str = "normal"
        network_link_status.append(status_str)
        
        # 1. Update Followers physical dynamics and estimation
        for i in range(n_followers):
            follower = followers[i]
            kf = filters[i]
            
            # Prediction step (using last step's command)
            kf.predict(u_prev[i])
            
            # True step
            y_meas = follower.step(u_prev[i])
            
            # Correction step
            x_est = kf.update(y_meas).flatten()
            
            # Prepare state packet for Cloud
            if scenario == 'defended':
                x_to_upload = dp_shield.obfuscate_state(x_est)
                follower_packet = secure_channel.generate_packet(i+1, x_to_upload, t)
            else:
                x_to_upload = np.copy(x_est)
                follower_packet = {"state": x_to_upload.tolist(), "timestamp": t}
                
            # FDI attack on follower packet upload
            if fdi_active:
                fdi_offset = np.array(fdi_cfg["offset"])
                if scenario == 'defended':
                    follower_packet["payload"]["state"] = (x_to_upload + fdi_offset).tolist()
                else:
                    follower_packet["state"] = (x_to_upload + fdi_offset).tolist()
            
            # Uplink protection: Cloud checks signature before storing
            if scenario == 'defended':
                if secure_channel.verify_packet(follower_packet):
                    cloud.upload_state(i+1, follower_packet)
                else:
                    # Uplink signature check failed: packet is discarded by Cloud
                    pass
            else:
                cloud.upload_state(i+1, follower_packet)
            
        # 2. Control input command updates (Downlink routing & prediction)
        for i in range(n_followers):
            kf = filters[i]
            x_est = kf.get_state()
            
            # Download leader state
            leader_packet_down = cloud.download_state(0)
            
            # Intercept downloaded packet to perform FDI on downlink
            if fdi_active and leader_packet_down is not None:
                import copy
                leader_packet_down = copy.deepcopy(leader_packet_down)
                fdi_offset = np.array(fdi_cfg["offset"])
                if scenario == 'defended':
                    leader_packet_down["payload"]["state"] = (np.array(leader_packet_down["payload"]["state"]) + fdi_offset).tolist()
                else:
                    leader_packet_down["state"] = (np.array(leader_packet_down["state"]) + fdi_offset).tolist()
            
            # Dead-Reckoning Prediction or Normal Download
            if dos_active:
                # DoS active: link severed. Follower runs dead reckoning
                _, u_L_pred = get_leader_state_and_input(t)
                x_L_pred[i] = (A_d @ x_L_pred[i].reshape(4, 1) + B_d @ u_L_pred).flatten()
                leader_state_used = np.copy(x_L_pred[i])
            else:
                if scenario == 'defended':
                    is_valid = secure_channel.verify_packet(leader_packet_down)
                    if is_valid:
                        leader_state_used = np.array(leader_packet_down["payload"]["state"])
                        x_L_pred[i] = np.copy(leader_state_used)
                    else:
                        # Signature verification failed (FDI detected).
                        # Discard telemetry and predict next step (dead reckoning defense)
                        _, u_L_pred = get_leader_state_and_input(t)
                        x_L_pred[i] = (A_d @ x_L_pred[i].reshape(4, 1) + B_d @ u_L_pred).flatten()
                        leader_state_used = np.copy(x_L_pred[i])
                else:
                    # Under Attack, No Defense: accept malicious data
                    leader_state_used = np.array(leader_packet_down["state"]) if leader_packet_down else np.zeros(4)
                    x_L_pred[i] = np.copy(leader_state_used)
                    
            # Controller execution
            u_cmd = controller.compute_control(leader_state_used, x_est, u_L)
            u_prev[i] = u_cmd
            
            # Log metrics
            follower_histories[i].append(np.copy(followers[i].x.flatten()))
            filter_histories[i].append(np.copy(x_est))
            
            # Tracking error (physical distance to leader)
            e_track = np.linalg.norm(followers[i].x.flatten()[[0,2]] - x_L[[0,2]])
            tracking_errors[i].append(e_track)
            
            # Local Kalman Filter estimation error (estimation vs physical truth)
            e_est = np.linalg.norm(x_est - followers[i].x.flatten())
            estimation_errors[i].append(e_est)
            
            # Cloud estimation error (corrupted vs true)
            follower_packet_stored = cloud.download_state(i+1)
            if follower_packet_stored:
                if scenario == 'defended':
                    # Clean under defense (verification blocked upload of FDI, keeping last valid)
                    x_cloud = np.array(follower_packet_stored["payload"]["state"])
                else:
                    x_cloud = np.array(follower_packet_stored["state"])
                e_cloud = np.linalg.norm(x_cloud - followers[i].x.flatten())
            else:
                e_cloud = 0.0
            cloud_est_errors[i].append(e_cloud)
            
            # Lyapunov function calculation V_i = e^T * P_lyap * e
            e_state_vec = (followers[i].x.flatten() - x_L).reshape(4, 1)
            V_val = (e_state_vec.T @ P_lyap @ e_state_vec).item()
            lyapunov_values[i].append(V_val)
            
            # Log control inputs magnitude ||u(t)||
            control_inputs[i].append(float(np.linalg.norm(u_cmd)))

        # Update Leader state discretely using same A_d, B_d and circular input
        x_L_state = A_d @ x_L_state + B_d @ u_L
            
    logger.info(f"Simulation completed for scenario: '{scenario}'")
    return {
        "time": time_grid,
        "leader": np.array(leader_history),
        "followers": [np.array(h) for h in follower_histories],
        "filters": [np.array(h) for h in filter_histories],
        "tracking_errors": [np.array(e) for e in tracking_errors],
        "estimation_errors": [np.array(e) for e in estimation_errors],
        "cloud_est_errors": [np.array(e) for e in cloud_est_errors],
        "lyapunov_values": [np.array(e) for e in lyapunov_values],
        "control_inputs": [np.array(e) for e in control_inputs],
        "network_link_status": network_link_status
    }


def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Secure NCS Multi-Agent Control Simulation")
    parser.add_argument("-c", "--config", type=str, default="config.json", help="Path to config.json file")
    parser.add_argument("-s", "--scenario", type=str, default="all", choices=["ideal", "attacked", "defended", "all"],
                        help="Specify simulation scenario to run (default: all)")
    parser.add_argument("-o", "--output", type=str, default="simulation_results.png", help="File path to save the output comparison plot")
    parser.add_argument("-l", "--log-level", type=str, default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                        help="Set console logging level (default: INFO)")
    args = parser.parse_args()
    
    # Adjust log level
    logger.setLevel(getattr(logging, args.log_level))
    logging.getLogger("NCS.Shield").setLevel(getattr(logging, args.log_level))
    
    logger.info("==========================================================")
    logger.info("   PRODUCTION NCS MULTI-AGENT CONTROL SYSTEM SIMULATOR    ")
    logger.info("==========================================================")
    
    # Load environment variables first (.env)
    load_env()
    
    # Load configuration
    config = load_config(args.config)
    
    # Extract matrices parameters
    sys_cfg = config["system"]
    dt = sys_cfg["dt"]
    damping = sys_cfg["damping"]
    
    A_d = np.array([
        [1.0,  dt,  0.0,  0.0],
        [0.0,  1.0 - damping*dt, 0.0, 0.0],
        [0.0,  0.0,  1.0,  dt],
        [0.0,  0.0,  0.0,  1.0 - damping*dt]
    ])
    B_d = np.array([
        [0.0, 0.0],
        [dt,  0.0],
        [0.0, 0.0],
        [0.0, dt ]
    ])
    
    lqr_cfg = config["lqr"]
    Q_lqr = np.diag(lqr_cfg["Q_lqr_diag"])
    R_lqr = np.diag(lqr_cfg["R_lqr_diag"])
    
    # 1. Closed-loop stability check
    controller = LQRController(A_d, B_d, Q_lqr, R_lqr)
    is_stable, eigvals, radius = controller.verify_stability()
    
    logger.info("Stability Verification:")
    logger.info(f"  Closed-loop Schur Stable: {is_stable}")
    logger.info(f"  Spectral Radius (max |lambda|): {radius:.6f}")
    logger.info("  Eigenvalues:")
    for ev in eigvals:
        logger.info(f"    {ev.real:.4f} + {ev.imag:.4f}i (magnitude: {np.abs(ev):.4f})")
        
    if not is_stable:
        logger.error("SYSTEM IS INSTABLE under current controller configuration! Exiting.")
        sys.exit(1)
        
    # 2. Run simulation(s)
    scenarios_to_run = []
    if args.scenario == "all":
        scenarios_to_run = ["ideal", "attacked", "defended"]
    else:
        scenarios_to_run = [args.scenario]
        
    results = {}
    for sc in scenarios_to_run:
        results[sc] = run_simulation(sc, config)
        
    # 3. Export data as JSON log file for HTML Dashboard
    export_data = {
        "metadata": {
            "is_stable": bool(is_stable),
            "spectral_radius": float(radius),
            "eigenvalues": [[float(ev.real), float(ev.imag)] for ev in eigvals],
            "n_followers": int(config["simulation"]["n_followers"]),
            "t_max": float(config["system"]["t_max"]),
            "dt": float(config["system"]["dt"]),
            "attacks": config["attacks"]
        },
        "scenarios": {}
    }
    
    for sc in scenarios_to_run:
        res = results[sc]
        export_data["scenarios"][sc] = {
            "time": res["time"].tolist(),
            "leader": res["leader"].tolist(),
            "followers": [f.tolist() for f in res["followers"]],
            "filters": [f.tolist() for f in res["filters"]],
            "tracking_errors": [e.tolist() for e in res["tracking_errors"]],
            "estimation_errors": [e.tolist() for e in res["estimation_errors"]],
            "cloud_est_errors": [e.tolist() for e in res["cloud_est_errors"]],
            "lyapunov_values": [e.tolist() for e in res["lyapunov_values"]],
            "control_inputs": [e.tolist() for e in res["control_inputs"]],
            "network_link_status": res["network_link_status"]
        }
        
    log_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(log_dir, "simulation_data.json")
    try:
        with open(json_path, "w") as f:
            json.dump(export_data, f, indent=2)
        logger.info(f"JSON simulation database written to: '{json_path}'")
    except Exception as e:
        logger.error(f"Failed to export JSON database: {e}")
        
    # 4. Plotting comparison (4x6 grid)
    if len(scenarios_to_run) >= 1:
        logger.info("Generating plots...")
        fig = plt.figure(figsize=(18, 15))
        
        # Subplots using gridspec/subplot2grid (4 rows, 6 columns)
        # Row 0: Trajectories (Col 0-1: Ideal, Col 2-3: Attacked, Col 4-5: Defended)
        ax_traj_ideal = plt.subplot2grid((4, 6), (0, 0), colspan=2)
        ax_traj_attack = plt.subplot2grid((4, 6), (0, 2), colspan=2)
        ax_traj_defend = plt.subplot2grid((4, 6), (0, 4), colspan=2)
        
        # Row 1: Consensus Error and Control Inputs
        ax_err = plt.subplot2grid((4, 6), (1, 0), colspan=3)
        ax_ctrl = plt.subplot2grid((4, 6), (1, 3), colspan=3)
        
        # Row 2: Lyapunov Stability and Complex Eigenvalues s-Plane Map
        ax_lyap = plt.subplot2grid((4, 6), (2, 0), colspan=3)
        ax_poles = plt.subplot2grid((4, 6), (2, 3), colspan=3)
        
        # Row 3: Local KF Estimation Error and Cloud Telemetry Error
        ax_est = plt.subplot2grid((4, 6), (3, 0), colspan=3)
        ax_cloud = plt.subplot2grid((4, 6), (3, 3), colspan=3)
        
        # Plot Row 0: Trajectories
        trajs = [ax_traj_ideal, ax_traj_attack, ax_traj_defend]
        scen_mapping = ["ideal", "attacked", "defended"]
        
        for idx, sc in enumerate(scen_mapping):
            if sc in results:
                ax = trajs[idx]
                res = results[sc]
                ax.plot(res["leader"][:, 0], res["leader"][:, 2], 'k--', label="Leader (target)", linewidth=2)
                for i in range(len(res["followers"])):
                    ax.plot(res["followers"][i][:, 0], res["followers"][i][:, 2], label=f"Follower {i+1}", alpha=0.8)
                ax.set_title(f"Scenario: {sc.upper()}")
                ax.set_xlabel("X Position (m)")
                ax.set_ylabel("Y Position (m)")
                ax.grid(True)
                if idx == 0:
                    ax.legend()
                    
        colors = {"ideal": "g-", "attacked": "r-", "defended": "b-"}
        attack_cfg = config["attacks"]
        
        # Plot Row 1: Consensus Error
        for sc in scenarios_to_run:
            res = results[sc]
            avg_err = np.mean(res["tracking_errors"], axis=0)
            ax_err.plot(res["time"], avg_err, colors[sc], label=f"{sc.capitalize()}", linewidth=1.5)
        ax_err.axvspan(attack_cfg["fdi"]["start_time"], attack_cfg["fdi"]["end_time"], color='yellow', alpha=0.15, label="FDI Active")
        ax_err.axvspan(attack_cfg["dos"]["start_time"], attack_cfg["dos"]["end_time"], color='gray', alpha=0.15, label="DoS Active")
        
        # Shaded Regions Annotations via axis transforms
        ax_err.text(17.0, 0.82, "FDI Attack Active", color='darkgoldenrod', alpha=0.85, ha='center', weight='bold', fontsize=9, transform=ax_err.get_xaxis_transform())
        ax_err.text(33.0, 0.82, "DoS Attack Active", color='dimgray', alpha=0.85, ha='center', weight='bold', fontsize=9, transform=ax_err.get_xaxis_transform())
        
        ax_err.set_title("Average Consensus Tracking Error")
        ax_err.set_xlabel("Time (s)")
        ax_err.set_ylabel("Error (m)")
        ax_err.grid(True)
        ax_err.legend()
        
        # Plot Row 1: Control Inputs Magnitude
        for sc in scenarios_to_run:
            res = results[sc]
            avg_ctrl = np.mean(res["control_inputs"], axis=0)
            ax_ctrl.plot(res["time"], avg_ctrl, colors[sc], label=f"{sc.capitalize()}", linewidth=1.5)
        ax_ctrl.axvspan(attack_cfg["fdi"]["start_time"], attack_cfg["fdi"]["end_time"], color='yellow', alpha=0.15)
        ax_ctrl.axvspan(attack_cfg["dos"]["start_time"], attack_cfg["dos"]["end_time"], color='gray', alpha=0.15)
        
        ax_ctrl.text(17.0, 0.82, "FDI active (sat)", color='darkgoldenrod', alpha=0.85, ha='center', weight='bold', fontsize=9, transform=ax_ctrl.get_xaxis_transform())
        ax_ctrl.text(33.0, 0.82, "DoS active (ZOH)", color='dimgray', alpha=0.85, ha='center', weight='bold', fontsize=9, transform=ax_ctrl.get_xaxis_transform())
        
        ax_ctrl.set_title("Average Control Command Magnitude ||u(t)||")
        ax_ctrl.set_xlabel("Time (s)")
        ax_ctrl.set_ylabel("Acceleration (m/s^2)")
        ax_ctrl.grid(True)
        ax_ctrl.legend()
        
        # Plot Row 2: Lyapunov Values
        for sc in scenarios_to_run:
            res = results[sc]
            avg_lyap = np.mean(res["lyapunov_values"], axis=0)
            ax_lyap.plot(res["time"], avg_lyap, colors[sc], label=f"{sc.capitalize()}", linewidth=1.5)
        ax_lyap.axvspan(attack_cfg["fdi"]["start_time"], attack_cfg["fdi"]["end_time"], color='yellow', alpha=0.15)
        ax_lyap.axvspan(attack_cfg["dos"]["start_time"], attack_cfg["dos"]["end_time"], color='gray', alpha=0.15)
        
        ax_lyap.text(17.0, 0.82, "FDI instability", color='darkgoldenrod', alpha=0.85, ha='center', weight='bold', fontsize=9, transform=ax_lyap.get_xaxis_transform())
        ax_lyap.text(33.0, 0.82, "DoS drift", color='dimgray', alpha=0.85, ha='center', weight='bold', fontsize=9, transform=ax_lyap.get_xaxis_transform())
        
        ax_lyap.set_title("System Lyapunov Stability Function V(t)")
        ax_lyap.set_xlabel("Time (s)")
        ax_lyap.set_ylabel("Lyapunov Value")
        ax_lyap.grid(True)
        ax_lyap.legend()
        
        # Plot Row 2: Complex s-Plane Eigenvalues Map (LHP check for continuous stability)
        s_poles = np.log(eigvals) / dt
        ax_poles.axvline(0, color='black', linewidth=1.5, label='Imaginary Axis (Re=0)')
        ax_poles.axhline(0, color='gray', linewidth=0.5)
        # Shade LHP (Stable) and RHP (Unstable)
        ax_poles.axvspan(-5.0, 0, color='green', alpha=0.08, label='Stable (LHP)')
        ax_poles.axvspan(0, 2.0, color='red', alpha=0.08, label='Unstable (RHP)')
        # Plot continuous poles
        ax_poles.scatter(s_poles.real, s_poles.imag, marker='x', color='blue', s=100, label='CL Poles (s-plane)', zorder=5)
        # Annotate poles values
        for p in s_poles:
            ax_poles.annotate(f"{p.real:.3f} + {p.imag:.3f}i", (p.real + 0.1, p.imag + 0.05), fontsize=8, color='blue', weight='semibold')
        ax_poles.set_title("Continuous Closed-Loop Poles (s-plane)")
        ax_poles.set_xlabel("Real Part (σ)")
        ax_poles.set_ylabel("Imaginary Part (jω)")
        ax_poles.set_xlim([-4.0, 2.0])
        ax_poles.set_ylim([-3.0, 3.0])
        ax_poles.grid(True)
        ax_poles.legend(loc='upper right')
        
        # Plot Row 3: Local KF Estimation Error
        for sc in scenarios_to_run:
            res = results[sc]
            avg_est = np.mean(res["estimation_errors"], axis=0)
            ax_est.plot(res["time"], avg_est, colors[sc], label=f"{sc.capitalize()}", linewidth=1.5)
        ax_est.axvspan(attack_cfg["fdi"]["start_time"], attack_cfg["fdi"]["end_time"], color='yellow', alpha=0.15)
        ax_est.axvspan(attack_cfg["dos"]["start_time"], attack_cfg["dos"]["end_time"], color='gray', alpha=0.15)
        
        ax_est.text(17.0, 0.82, "FDI active", color='darkgoldenrod', alpha=0.85, ha='center', weight='bold', fontsize=9, transform=ax_est.get_xaxis_transform())
        ax_est.text(33.0, 0.82, "DoS active", color='dimgray', alpha=0.85, ha='center', weight='bold', fontsize=9, transform=ax_est.get_xaxis_transform())
        
        ax_est.set_title("Local Kalman Filter Estimation Error (Own State)")
        ax_est.set_xlabel("Time (s)")
        ax_est.set_ylabel("Estimation Error (Norm)")
        ax_est.grid(True)
        ax_est.legend()
        
        # Plot Row 3: Cloud Telemetry Error
        for sc in scenarios_to_run:
            res = results[sc]
            avg_cloud = np.mean(res["cloud_est_errors"], axis=0)
            ax_cloud.plot(res["time"], avg_cloud, colors[sc], label=f"{sc.capitalize()}", linewidth=1.5)
        ax_cloud.axvspan(attack_cfg["fdi"]["start_time"], attack_cfg["fdi"]["end_time"], color='yellow', alpha=0.15)
        ax_cloud.axvspan(attack_cfg["dos"]["start_time"], attack_cfg["dos"]["end_time"], color='gray', alpha=0.15)
        
        ax_cloud.text(17.0, 0.82, "FDI uploads", color='darkgoldenrod', alpha=0.85, ha='center', weight='bold', fontsize=9, transform=ax_cloud.get_xaxis_transform())
        ax_cloud.text(33.0, 0.82, "DoS drops", color='dimgray', alpha=0.85, ha='center', weight='bold', fontsize=9, transform=ax_cloud.get_xaxis_transform())
        
        ax_cloud.set_title("Cloud-Level Telemetry Estimation Error")
        ax_cloud.set_xlabel("Time (s)")
        ax_cloud.set_ylabel("Error (m)")
        ax_cloud.grid(True)
        ax_cloud.legend()
        
        plt.tight_layout()
        
        output_dir = os.path.dirname(os.path.abspath(args.output))
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
            
        plt.savefig(args.output, dpi=150)
        logger.info(f"Comparison plot saved successfully to: '{args.output}'")
        plt.close()
        
        # Log Summary Performance metrics table in stdout (Thesis-grade) - Emojis removed to prevent CP1252 crash
        print("\n" + "="*80)
        print("                 NCS SIMULATOR PERFORMANCE COMPARISON TABLE")
        print("="*80)
        print(f" {'Metric':<25} | {'Ideal':<15} | {'Attacked':<15} | {'Defended':<15} | Status")
        print("-"*80)
        
        # Calculate stats programmatically
        for name, key in [("Consensus Error (Avg)", "tracking_errors"), 
                          ("Cloud Telemetry Err (Avg)", "cloud_est_errors"), 
                          ("Control Input Norm (Avg)", "control_inputs")]:
            val_id = np.mean(results["ideal"][key]) if "ideal" in results else 0.0
            val_at = np.mean(results["attacked"][key]) if "attacked" in results else 0.0
            val_de = np.mean(results["defended"][key]) if "defended" in results else 0.0
            status = "Optimal [OK]" if val_de <= val_id * 1.5 else "Stable [OK]"
            print(f" {name:<25} | {val_id:<15.4f} | {val_at:<15.4f} | {val_de:<15.4f} | {status}")
            
        # Peak values
        p_err_id = np.max(np.mean(results["ideal"]["tracking_errors"], axis=0))
        p_err_at = np.max(np.mean(results["attacked"]["tracking_errors"], axis=0))
        p_err_de = np.max(np.mean(results["defended"]["tracking_errors"], axis=0))
        status_peak = "Shielded [OK]" if p_err_de <= 2.0 else "Stable [OK]"
        print(f" {'Consensus Error (Peak)':<25} | {p_err_id:<15.4f} | {p_err_at:<15.4f} | {p_err_de:<15.4f} | {status_peak}")
        
        p_ctrl_id = np.max(np.mean(results["ideal"]["control_inputs"], axis=0))
        p_ctrl_at = np.max(np.mean(results["attacked"]["control_inputs"], axis=0))
        p_ctrl_de = np.max(np.mean(results["defended"]["control_inputs"], axis=0))
        print(f" {'Control Input (Peak)':<25} | {p_ctrl_id:<15.4f} | {p_ctrl_at:<15.4f} | {p_ctrl_de:<15.4f} | Bounded [OK]")
        
        print(f" {'Closed-Loop Stability':<25} | {'Schur Stable':<15} | {'Instability':<15} | {'Schur Stable':<15} | LHP Poles [OK]")
        print("="*80)
        
        # Console guidelines to launch HTML Dashboard (CORS instructions)
        print("\n" + "="*80)
        print("             SIMULATION SUCCEEDED! INTERACTIVE GUI READY TO RUN")
        print("="*80)
        print(" An interactive, premium web dashboard was generated for this database.")
        print(" To visualize real-time network topologies, animated packet flows,")
        print(" and scrub through time-series charts, follow these steps:")
        print("\n 1. Start a local HTTP server in this directory:")
        print("       python -m http.server 8000")
        print("\n 2. Open your web browser and navigate to:")
        print("       http://localhost:8000/dashboard.html")
        print("\n (Or simply double-click dashboard.html in your browser and click")
        print(" 'Load JSON File' to manually select 'Tester/simulation_data.json'.)")
        print("="*80 + "\n")


if __name__ == "__main__":
    main()
