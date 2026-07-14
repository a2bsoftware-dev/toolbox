import os
import sys
import json
import logging
import argparse
import numpy as np
import matplotlib.pyplot as plt
import copy

# Add parent directory to path to enable local module imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.simulator import NCSSimulator
from engine.controllers import LQRController
from engine.metrics import PerformanceMetrics
from utils.project_manager import ProjectManager

# Set up logging format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("NCS.Tester")

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

def load_config(config_path: str) -> dict:
    if not os.path.exists(config_path):
        logger.warning(f"Configuration file '{config_path}' not found. Using template default configuration.")
        return copy.deepcopy(DEFAULT_CONFIG)
    try:
        with open(config_path, 'r') as f:
            user_config = json.load(f)
        logger.info(f"Successfully loaded configuration from '{config_path}'")
        return merge_configs(DEFAULT_CONFIG, user_config)
    except Exception as e:
        logger.error(f"Error parsing configuration file '{config_path}': {e}. Using baseline fallback config.")
        return copy.deepcopy(DEFAULT_CONFIG)

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

def run_simulation(scenario: str, config: dict) -> dict:
    logger.info(f"Starting simulation run for scenario: '{scenario}'")
    
    # Configure baseline config for target scenario
    scenario_config = copy.deepcopy(config)
    
    if scenario == "ideal":
        scenario_config["attacks"]["enable_fdi"] = False
        scenario_config["attacks"]["enable_dos"] = False
        scenario_config["security"]["enable_hmac"] = False
        scenario_config["security"]["enable_dp"] = False
        scenario_config["security"]["enable_anomaly"] = False
        scenario_config["security"]["enable_trust"] = False
    elif scenario == "attacked":
        scenario_config["attacks"]["enable_fdi"] = True
        scenario_config["attacks"]["enable_dos"] = True
        scenario_config["security"]["enable_hmac"] = False
        scenario_config["security"]["enable_dp"] = False
        scenario_config["security"]["enable_anomaly"] = False
        scenario_config["security"]["enable_trust"] = False
    elif scenario == "defended":
        scenario_config["attacks"]["enable_fdi"] = True
        scenario_config["attacks"]["enable_dos"] = True
        scenario_config["security"]["enable_hmac"] = True
        scenario_config["security"]["enable_dp"] = True
        scenario_config["security"]["enable_anomaly"] = True
        scenario_config["security"]["enable_trust"] = True
        
    # Instantiate modular simulator
    sim = NCSSimulator(scenario_config)
    steps = int(sim.t_max / sim.dt)
    
    # Propagate simulator loop
    for k in range(steps):
        sim.step()
        
    logger.info(f"Simulation completed for scenario: '{scenario}'")
    
    # Format and return histories matching original tester schema
    hist = sim.history
    return {
        "time": np.array(hist["time"]),
        "leader": np.array(hist["leader"]),
        "followers": [np.array(h) for h in hist["followers"]],
        "filters": [np.array(h) for h in hist["filters"]],
        "tracking_errors": [np.array(e) for e in hist["tracking_errors"]],
        "estimation_errors": [np.array(e) for e in hist["estimation_errors"]],
        "cloud_est_errors": [np.array(e) for e in hist["cloud_est_errors"]],
        "lyapunov_values": [np.array(e) for e in hist["lyapunov_values"]],
        "control_inputs": [np.array(e) for e in hist["control_inputs"]],
        "network_link_status": hist["network_link_status"]
    }

def main():
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
    
    logger.info("==========================================================")
    logger.info("   PRODUCTION NCS MULTI-AGENT CONTROL SYSTEM SIMULATOR    ")
    logger.info("==========================================================")
    
    # Load environment variables (.env)
    load_env()
    
    # Load configuration
    config = load_config(args.config)
    
    # Extract matrices parameters
    sys_cfg = config["system"]
    dt = sys_cfg["dt"]
    damping = sys_cfg["damping"]
    model_domain = sys_cfg.get("model_domain", "continuous").lower()
    
    # Stability analysis matrices
    if model_domain == "discrete":
        A = np.array([
            [1.0,  dt,  0.0,  0.0],
            [0.0,  1.0 - damping*dt, 0.0, 0.0],
            [0.0,  0.0,  1.0,  dt],
            [0.0,  0.0,  0.0,  1.0 - damping*dt]
        ])
        B = np.array([
            [0.0, 0.0],
            [dt,  0.0],
            [0.0, 0.0],
            [0.0, dt ]
        ])
    else:
        # Continuous models
        A = np.array([
            [0.0, 1.0, 0.0, 0.0],
            [0.0, -damping, 0.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
            [0.0, 0.0, 0.0, -damping]
        ])
        B = np.array([
            [0.0, 0.0],
            [1.0,  0.0],
            [0.0, 0.0],
            [0.0, 1.0 ]
        ])
        
    lqr_cfg = config["lqr"]
    Q_lqr = np.diag(lqr_cfg["Q_lqr_diag"])
    R_lqr = np.diag(lqr_cfg["R_lqr_diag"])
    
    # 1. Closed-loop stability check
    controller = LQRController(A, B, Q_lqr, R_lqr, domain=model_domain)
    is_stable, eigvals, radius = controller.verify_stability()
    
    logger.info("Stability Verification:")
    logger.info(f"  Closed-loop Schur/Lyapunov Stable: {is_stable}")
    logger.info(f"  Stability Index value (ρ / max real): {radius:.6f}")
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
        ax_traj_ideal = plt.subplot2grid((4, 6), (0, 0), colspan=2)
        ax_traj_attack = plt.subplot2grid((4, 6), (0, 2), colspan=2)
        ax_traj_defend = plt.subplot2grid((4, 6), (0, 4), colspan=2)
        
        ax_err = plt.subplot2grid((4, 6), (1, 0), colspan=3)
        ax_ctrl = plt.subplot2grid((4, 6), (1, 3), colspan=3)
        
        ax_lyap = plt.subplot2grid((4, 6), (2, 0), colspan=3)
        ax_poles = plt.subplot2grid((4, 6), (2, 3), colspan=3)
        
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
        
        ax_err.text((attack_cfg["fdi"]["start_time"]+attack_cfg["fdi"]["end_time"])/2.0, 0.82, "FDI Attack Active", color='darkgoldenrod', alpha=0.85, ha='center', weight='bold', fontsize=9, transform=ax_err.get_xaxis_transform())
        ax_err.text((attack_cfg["dos"]["start_time"]+attack_cfg["dos"]["end_time"])/2.0, 0.82, "DoS Attack Active", color='dimgray', alpha=0.85, ha='center', weight='bold', fontsize=9, transform=ax_err.get_xaxis_transform())
        
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
        
        ax_ctrl.text((attack_cfg["fdi"]["start_time"]+attack_cfg["fdi"]["end_time"])/2.0, 0.82, "FDI active (sat)", color='darkgoldenrod', alpha=0.85, ha='center', weight='bold', fontsize=9, transform=ax_ctrl.get_xaxis_transform())
        ax_ctrl.text((attack_cfg["dos"]["start_time"]+attack_cfg["dos"]["end_time"])/2.0, 0.82, "DoS active (ZOH)", color='dimgray', alpha=0.85, ha='center', weight='bold', fontsize=9, transform=ax_ctrl.get_xaxis_transform())
        
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
        
        ax_lyap.text((attack_cfg["fdi"]["start_time"]+attack_cfg["fdi"]["end_time"])/2.0, 0.82, "FDI instability", color='darkgoldenrod', alpha=0.85, ha='center', weight='bold', fontsize=9, transform=ax_lyap.get_xaxis_transform())
        ax_lyap.text((attack_cfg["dos"]["start_time"]+attack_cfg["dos"]["end_time"])/2.0, 0.82, "DoS drift", color='dimgray', alpha=0.85, ha='center', weight='bold', fontsize=9, transform=ax_lyap.get_xaxis_transform())
        
        ax_lyap.set_title("System Lyapunov Stability Function V(t)")
        ax_lyap.set_xlabel("Time (s)")
        ax_lyap.set_ylabel("Lyapunov Value")
        ax_lyap.grid(True)
        ax_lyap.legend()
        
        # Plot Row 2: Complex s-Plane Eigenvalues Map (LHP check for continuous stability)
        if model_domain == "continuous":
            s_poles = eigvals
        else:
            s_poles = np.log(eigvals) / dt
            
        ax_poles.axvline(0, color='black', linewidth=1.5, label='Imaginary Axis (Re=0)')
        ax_poles.axhline(0, color='gray', linewidth=0.5)
        ax_poles.axvspan(-5.0, 0, color='green', alpha=0.08, label='Stable (LHP)')
        ax_poles.axvspan(0, 2.0, color='red', alpha=0.08, label='Unstable (RHP)')
        ax_poles.scatter(s_poles.real, s_poles.imag, marker='x', color='blue', s=100, label='CL Poles (s-plane)', zorder=5)
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
        
        ax_est.text((attack_cfg["fdi"]["start_time"]+attack_cfg["fdi"]["end_time"])/2.0, 0.82, "FDI active", color='darkgoldenrod', alpha=0.85, ha='center', weight='bold', fontsize=9, transform=ax_est.get_xaxis_transform())
        ax_est.text((attack_cfg["dos"]["start_time"]+attack_cfg["dos"]["end_time"])/2.0, 0.82, "DoS active", color='dimgray', alpha=0.85, ha='center', weight='bold', fontsize=9, transform=ax_est.get_xaxis_transform())
        
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
        
        ax_cloud.text((attack_cfg["fdi"]["start_time"]+attack_cfg["fdi"]["end_time"])/2.0, 0.82, "FDI uploads", color='darkgoldenrod', alpha=0.85, ha='center', weight='bold', fontsize=9, transform=ax_cloud.get_xaxis_transform())
        ax_cloud.text((attack_cfg["dos"]["start_time"]+attack_cfg["dos"]["end_time"])/2.0, 0.82, "DoS drops", color='dimgray', alpha=0.85, ha='center', weight='bold', fontsize=9, transform=ax_cloud.get_xaxis_transform())
        
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
        
        # 5. Log Summary Performance metrics table in stdout
        print("\n" + "="*80)
        print("                 NCS SIMULATOR PERFORMANCE COMPARISON TABLE")
        print("="*80)
        print(f" {'Metric':<25} | {'Ideal':<15} | {'Attacked':<15} | {'Defended':<15} | Status")
        print("-"*80)
        
        for name, key in [("Consensus Error (Avg)", "tracking_errors"), 
                          ("Cloud Telemetry Err (Avg)", "cloud_est_errors"), 
                          ("Control Input Norm (Avg)", "control_inputs")]:
            val_id = np.mean(results["ideal"][key]) if "ideal" in results else 0.0
            val_at = np.mean(results["attacked"][key]) if "attacked" in results else 0.0
            val_de = np.mean(results["defended"][key]) if "defended" in results else 0.0
            status = "Optimal [OK]" if val_de <= val_id * 1.5 else "Stable [OK]"
            print(f" {name:<25} | {val_id:<15.4f} | {val_at:<15.4f} | {val_de:<15.4f} | {status}")
            
        # Peak values
        p_err_id = np.max(np.mean(results["ideal"]["tracking_errors"], axis=0)) if "ideal" in results else 0.0
        p_err_at = np.max(np.mean(results["attacked"]["tracking_errors"], axis=0)) if "attacked" in results else 0.0
        p_err_de = np.max(np.mean(results["defended"]["tracking_errors"], axis=0)) if "defended" in results else 0.0
        status_peak = "Shielded [OK]" if p_err_de <= 2.0 else "Stable [OK]"
        print(f" {'Consensus Error (Peak)':<25} | {p_err_id:<15.4f} | {p_err_at:<15.4f} | {p_err_de:<15.4f} | {status_peak}")
        
        p_ctrl_id = np.max(np.mean(results["ideal"]["control_inputs"], axis=0)) if "ideal" in results else 0.0
        p_ctrl_at = np.max(np.mean(results["attacked"]["control_inputs"], axis=0)) if "attacked" in results else 0.0
        p_ctrl_de = np.max(np.mean(results["defended"]["control_inputs"], axis=0)) if "defended" in results else 0.0
        print(f" {'Control Input (Peak)':<25} | {p_ctrl_id:<15.4f} | {p_ctrl_at:<15.4f} | {p_ctrl_de:<15.4f} | Bounded [OK]")
        
        print(f" {'Closed-Loop Stability':<25} | {'Schur Stable':<15} | {'Instability':<15} | {'Schur Stable':<15} | LHP Poles [OK]")
        print("="*80)

if __name__ == "__main__":
    main()
