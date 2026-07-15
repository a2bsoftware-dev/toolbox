import os
import logging
import numpy as np
import copy

from engine.agents import PhysicalAgent
from engine.controllers import LQRController, PIDController, PolePlacementController
from engine.observers import KalmanFilter, LuenbergerObserver
from engine.attacks import AttackSimulator
from engine.defenses import SecureChannel, DifferentialPrivacy, TrustFilter
from engine.detection import IntrusionDetectionSystem
from engine.metrics import PerformanceMetrics
from engine.model import continuous_matrices, euler_discrete_matrices, zoh_discretize
from utils.logger import EventLogger

logger = logging.getLogger("NCS.Simulator")

class NCSSimulator:
    """
    Main stateful simulator coordinating agents, filters, controllers, threats, and defenses.
    Now supports continuous-time models, exact ZOH discretization, Intrusion Detection,
    Performance Metrics, and Event Logging.
    """
    def __init__(self, config: dict):
        self.config = copy.deepcopy(config)
        self.reset()
        
    def reset(self):
        # 1. System Parameters
        sys_cfg = self.config["system"]
        self.dt = sys_cfg["dt"]
        self.damping = sys_cfg["damping"]
        self.t_max = sys_cfg["t_max"]
        self.max_accel = sys_cfg.get("max_accel", 10.0)
        self.max_speed = sys_cfg.get("max_speed", 15.0)
        self.model_domain = sys_cfg.get("model_domain", "continuous").lower()
        
        # 2. Define Continuous-Time System Model
        self.A_cont, self.B_cont, self.C_cont = continuous_matrices(self.damping)

        # 3. Discretize for simulation step
        if self.model_domain == "discrete":
            # Interpret configuration values directly as discrete-time
            self.A_d, self.B_d = euler_discrete_matrices(self.damping, self.dt)
        else:
            # Discretize continuous-time model using ZOH matrix exponentiation
            self.A_d, self.B_d = zoh_discretize(self.A_cont, self.B_cont, self.dt)

        self.C_d = np.copy(self.C_cont)
        
        # 4. Noise Parameters
        noise_cfg = self.config["noises"]
        self.Q_process = np.diag(noise_cfg["process_noise_diag"])
        self.R_measure = np.diag(noise_cfg["measure_noise_diag"])
        
        # 5. Controller & Observer Options
        lqr_cfg = self.config["lqr"]
        self.Q_lqr = np.diag(lqr_cfg["Q_lqr_diag"])
        self.R_lqr = np.diag(lqr_cfg["R_lqr_diag"])
        
        self.controller_type = self.config["controller"].get("type", "LQR").upper()
        self.observer_type = self.config["observer"].get("type", "KALMAN").upper()
        
        # 6. Agent Configurations
        sim_cfg = self.config["simulation"]
        self.n_followers = sim_cfg["n_followers"]
        self.initial_positions = sim_cfg["initial_positions"]
        self.omega = sim_cfg["leader_orbit_omega"]
        self.radius = sim_cfg["leader_orbit_radius"]
        
        # 7. Security & Defense Shields
        sec_cfg = self.config["security"]
        env_var_name = sec_cfg.get("secret_key_env_var", "NCS_SECRET_KEY")
        self.secret_key = os.environ.get(env_var_name) or sec_cfg.get("default_secret_key", "super_secure_consensus_key")
        if not os.environ.get(env_var_name):
            logger.warning(
                f"'{env_var_name}' is not set; using the default_secret_key from config.json "
                "(this value is checked into version control - set the env var for real deployments)."
            )
        self.dp_epsilon = sec_cfg.get("dp_epsilon", 1.5)
        self.dp_sensitivity = sec_cfg.get("dp_sensitivity", 0.15)
        self.anomaly_threshold = sec_cfg.get("anomaly_threshold", 5.0)
        # These were previously hardcoded class defaults with no way to tune them from config;
        # exposing them here does not change behavior (fallbacks match the prior hardcoded values).
        self.replay_threshold = sec_cfg.get("replay_threshold", 0.5)
        self.trust_decay_rate = sec_cfg.get("trust_decay_rate", 0.2)
        self.trust_recovery_rate = sec_cfg.get("trust_recovery_rate", 0.05)
        self.trust_cutoff = sec_cfg.get("trust_cutoff", 0.5)

        self.shield_hmac = sec_cfg.get("enable_hmac", True)
        self.shield_dp = sec_cfg.get("enable_dp", True)
        self.shield_anomaly = sec_cfg.get("enable_anomaly", True)
        self.shield_trust = sec_cfg.get("enable_trust", True)

        # Instantiate Security Components
        self.secure_channel = SecureChannel(secret_key=self.secret_key)
        self.dp_shield = DifferentialPrivacy(epsilon=self.dp_epsilon, sensitivity=self.dp_sensitivity)
        self.trust_filter = TrustFilter(n_agents=self.n_followers, decay_rate=self.trust_decay_rate, recovery_rate=self.trust_recovery_rate)

        # Instantiate Intrusion Detection (IDS) & Event Logger
        self.ids = IntrusionDetectionSystem(fdi_threshold=self.anomaly_threshold, replay_threshold=self.replay_threshold)
        self.event_logger = EventLogger()
        self.event_logger.log_event(0.0, "Simulator Initialized successfully.")
        
        # Initialize Controller
        if self.controller_type == "PID":
            pid_cfg = self.config["controller"].get("pid", {"kp": 2.0, "ki": 0.05, "kd": 0.5})
            self.controller = PIDController(kp=pid_cfg["kp"], ki=pid_cfg["ki"], kd=pid_cfg["kd"])
        elif self.controller_type == "POLE_PLACEMENT":
            poles = self.config["controller"].get("desired_poles", [0.91, 0.91, 0.85, 0.85])
            self.controller = PolePlacementController(self.A_d, self.B_d, poles)
        else:
            # LQR Controller supports CARE or DARE based on domain selection
            if self.model_domain == "continuous":
                self.controller = LQRController(self.A_cont, self.B_cont, self.Q_lqr, self.R_lqr, domain="continuous")
            else:
                self.controller = LQRController(self.A_d, self.B_d, self.Q_lqr, self.R_lqr, domain="discrete")
                
        self.P_lyap = self.controller.P_lyap if hasattr(self.controller, 'P_lyap') and self.controller.P_lyap is not None else np.eye(4)
        
        # Initialize Followers
        self.followers = []
        self.filters = []
        for i in range(self.n_followers):
            init_pos = self.initial_positions[i] if i < len(self.initial_positions) else [0.0, 0.0, 0.0, 0.0]
            agent = PhysicalAgent(i + 1, self.A_d, self.B_d, self.C_d, self.Q_process, self.R_measure, init_pos, self.max_accel, self.max_speed)
            self.followers.append(agent)
            
            y_init = self.C_d @ agent.x
            x_est_init = np.array([y_init[0, 0], 0.0, y_init[1, 0], 0.0])
            
            if self.observer_type == "LUENBERGER":
                obs_poles = self.config["observer"].get("desired_poles", [0.8, 0.8, 0.75, 0.75])
                kf = LuenbergerObserver(self.A_d, self.B_d, self.C_d, obs_poles, x0=x_est_init)
            else:
                kf = KalmanFilter(self.A_d, self.B_d, self.C_d, self.Q_process, self.R_measure, x0=x_est_init)
            self.filters.append(kf)
            
        # Cloud Database
        self.cloud_db = {}
        
        # Threat Configurations Setup
        attack_cfg = self.config.get("attacks", {})
        self.fdi_cfg = attack_cfg.get("fdi", {"start_time": 12.0, "end_time": 22.0, "offset": [15.0, 0.0, -15.0, 0.0]})
        self.dos_cfg = attack_cfg.get("dos", {"start_time": 28.0, "end_time": 38.0})
        self.delay_cfg = attack_cfg.get("delay", {"start_time": 50.0, "end_time": 60.0, "steps": 5})
        self.replay_cfg = attack_cfg.get("replay", {"start_time": 60.0, "end_time": 70.0, "window_size": 40})
        
        # Toggles
        self.attack_fdi_active_switch = attack_cfg.get("enable_fdi", True)
        self.attack_dos_active_switch = attack_cfg.get("enable_dos", True)
        self.attack_delay_active_switch = attack_cfg.get("enable_delay", False)
        self.attack_replay_active_switch = attack_cfg.get("enable_replay", False)
        
        self.attack_simulator = AttackSimulator(
            fdi_offset=self.fdi_cfg.get("offset", [15.0, 0.0, -15.0, 0.0]),
            replay_window_size=self.replay_cfg.get("window_size", 40),
            delay_steps=self.delay_cfg.get("steps", 5)
        )
        
        # Track previous states of attacks to log state transitions
        self._prev_fdi_active = False
        self._prev_dos_active = False
        
        # Leader State Initialization
        self.x_L_state = np.array([self.radius, 0.0, 0.0, self.radius * self.omega], dtype=float).reshape(4, 1)
        self.x_L_pred = [self.x_L_state.flatten() for _ in range(self.n_followers)]
        self.u_prev = [np.zeros((2, 1)) for _ in range(self.n_followers)]
        
        # Simulation Counters & Logs
        self.t = 0.0
        self.current_step_idx = 0
        self.packets_sent = 0
        self.packets_lost = 0
        
        self.history = {
            "time": [],
            "leader": [],
            "followers": [[] for _ in range(self.n_followers)],
            "filters": [[] for _ in range(self.n_followers)],
            "tracking_errors": [[] for _ in range(self.n_followers)],
            "estimation_errors": [[] for _ in range(self.n_followers)],
            "cloud_est_errors": [[] for _ in range(self.n_followers)],
            "lyapunov_values": [[] for _ in range(self.n_followers)],
            "control_inputs": [[] for _ in range(self.n_followers)],
            "network_link_status": []
        }
        
    def get_leader_input(self, t):
        ux = -self.radius * (self.omega**2) * np.cos(self.omega * t) - self.damping * self.x_L_state[1, 0]
        uy = -self.radius * (self.omega**2) * np.sin(self.omega * t) - self.damping * self.x_L_state[3, 0]
        return np.array([ux, uy]).reshape(2, 1)
        
    def step(self) -> dict:
        """
        Advances the simulation by one timestep dt.
        """
        # Determine active attacks at time self.t
        fdi_active = self.attack_fdi_active_switch and (self.fdi_cfg["start_time"] <= self.t <= self.fdi_cfg["end_time"])
        dos_active = self.attack_dos_active_switch and (self.dos_cfg["start_time"] <= self.t <= self.dos_cfg["end_time"])
        delay_active = self.attack_delay_active_switch and (self.delay_cfg["start_time"] <= self.t <= self.delay_cfg["end_time"])
        replay_active = self.attack_replay_active_switch and (self.replay_cfg["start_time"] <= self.t <= self.replay_cfg["end_time"])
        
        # Event Logging transitions
        if fdi_active and not self._prev_fdi_active:
            self.event_logger.log_event(self.t, "FDI Attack START (Uplink/Downlink bias).")
        elif not fdi_active and self._prev_fdi_active:
            self.event_logger.log_event(self.t, "FDI Attack END. Re-establishing link verification.")
            
        if dos_active and not self._prev_dos_active:
            self.event_logger.log_event(self.t, "DoS Attack START (Link severed).")
        elif not dos_active and self._prev_dos_active:
            self.event_logger.log_event(self.t, "DoS Attack END. Restoring cloud connection.")
            
        self._prev_fdi_active = fdi_active
        self._prev_dos_active = dos_active
        
        # Determine status string for canvas colors
        if dos_active:
            status_str = "dos"
        elif fdi_active:
            status_str = "attacked"
        elif delay_active:
            status_str = "delayed"
        elif replay_active:
            status_str = "replayed"
        elif self.shield_hmac:
            status_str = "secured"
        else:
            status_str = "normal"
        self.history["network_link_status"].append(status_str)
        
        # Leader Reference Input
        u_L = self.get_leader_input(self.t)
        x_L = self.x_L_state.flatten()
        self.history["leader"].append(np.copy(x_L))
        self.history["time"].append(self.t)
        
        # Upload Leader state to Cloud
        leader_packet = {"state": x_L.tolist(), "timestamp": self.t}
        if self.shield_hmac:
            leader_packet = self.secure_channel.generate_packet(0, x_L, self.t)
            # Uplink protection: Cloud checks signature before saving
            if self.secure_channel.verify_packet(leader_packet):
                self.cloud_db[0] = leader_packet
                self.packets_sent += 1
        else:
            self.cloud_db[0] = leader_packet
            self.packets_sent += 1
            
        # 1. Update followers physical step and upload to cloud
        for i in range(self.n_followers):
            follower = self.followers[i]
            kf = self.filters[i]
            
            # Predict & Update
            kf.predict(self.u_prev[i])
            y_meas = follower.step(self.u_prev[i])
            x_est = kf.update(y_meas).flatten()
            
            # Form packet
            if self.shield_hmac:
                x_to_upload = self.dp_shield.obfuscate_state(x_est) if self.shield_dp else np.copy(x_est)
                follower_packet = self.secure_channel.generate_packet(i+1, x_to_upload, self.t)
            else:
                x_to_upload = np.copy(x_est)
                follower_packet = {"state": x_to_upload.tolist(), "timestamp": self.t}
                
            # Intercept packet upload (Uplink attack)
            if fdi_active:
                follower_packet = self.attack_simulator.apply_fdi(follower_packet, self.shield_hmac)
                
            if delay_active:
                follower_packet = self.attack_simulator.apply_delay(i+1, follower_packet)
                
            follower_packet = self.attack_simulator.apply_replay(i+1, follower_packet, replay_active)
            
            # Uplink storage with optional HMAC verification
            if self.shield_hmac:
                if follower_packet is not None:
                    if self.secure_channel.verify_packet(follower_packet):
                        self.cloud_db[i+1] = follower_packet
                        self.packets_sent += 1
            else:
                if follower_packet is not None:
                    self.cloud_db[i+1] = follower_packet
                    self.packets_sent += 1
                    
        # 2. Downlink routing, prediction, and control action execution
        for i in range(self.n_followers):
            kf = self.filters[i]
            x_est = kf.get_state()
            
            # Download Leader Packet
            leader_packet_down = self.cloud_db.get(0, None)
            
            # Downlink attacks
            if fdi_active and leader_packet_down is not None:
                leader_packet_down = self.attack_simulator.apply_fdi(leader_packet_down, self.shield_hmac)
                
            if delay_active and leader_packet_down is not None:
                leader_packet_down = self.attack_simulator.apply_delay(0, leader_packet_down)
                
            if leader_packet_down is not None:
                leader_packet_down = self.attack_simulator.apply_replay(0, leader_packet_down, replay_active)
                
            # ZOH prediction fallback on DoS
            if dos_active or leader_packet_down is None:
                self.packets_lost += 1
                # Dead reckoning prediction
                self.x_L_pred[i] = (self.A_d @ self.x_L_pred[i].reshape(4, 1) + self.B_d @ u_L).flatten()
                leader_state_used = np.copy(self.x_L_pred[i])
            else:
                # Defense validation
                if self.shield_hmac:
                    is_sig_ok = self.secure_channel.verify_packet(leader_packet_down)

                    if is_sig_ok:
                        leader_state_used = np.array(leader_packet_down["payload"]["state"])
                        
                        # Anomaly residual detection (IDS)
                        predicted = (self.A_d @ self.x_L_pred[i].reshape(4, 1) + self.B_d @ u_L).flatten()
                        
                        # Let the IDS calculate FDI and Replay probabilities
                        fdi_prob = self.ids.detect_fdi(leader_state_used, predicted)
                        replay_prob = self.ids.detect_replay(0, leader_state_used)
                        
                        # Flag anomaly if probability exceeds 50%
                        is_anomalous = (fdi_prob > 0.5 or replay_prob > 0.5)
                        
                        if self.shield_anomaly:
                            if self.shield_trust:
                                self.trust_filter.update_trust(0, is_anomalous)
                                
                            if is_anomalous or (self.shield_trust and not self.trust_filter.is_trusted(0, cutoff=self.trust_cutoff)):
                                # Reject tampered packet, use dead reckoning
                                self.x_L_pred[i] = predicted
                                leader_state_used = np.copy(self.x_L_pred[i])
                                self.event_logger.log_event(self.t, f"IDS Alert: Anomalous telemetry rejected (prob: {max(fdi_prob, replay_prob)*100:.1f}%).")
                            else:
                                self.x_L_pred[i] = np.copy(leader_state_used)
                        else:
                            self.x_L_pred[i] = np.copy(leader_state_used)
                    else:
                        # Cryptographic signature failed (downlink FDI detected)
                        # Reject packet, use dead reckoning
                        self.x_L_pred[i] = (self.A_d @ self.x_L_pred[i].reshape(4, 1) + self.B_d @ u_L).flatten()
                        leader_state_used = np.copy(self.x_L_pred[i])
                else:
                    # Unshielded: accept whatever is downloaded
                    leader_state_used = np.array(leader_packet_down["state"]) if "state" in leader_packet_down else np.zeros(4)
                    self.x_L_pred[i] = np.copy(leader_state_used)
                    
            # Compute Control Input u(t)
            u_cmd = self.controller.compute_control(leader_state_used, x_est, u_L)
            self.u_prev[i] = u_cmd
            
            # Log Histories
            self.history["followers"][i].append(np.copy(self.followers[i].x.flatten()))
            self.history["filters"][i].append(np.copy(x_est))
            
            # Errors logging
            e_track = np.linalg.norm(self.followers[i].x.flatten()[[0,2]] - x_L[[0,2]])
            self.history["tracking_errors"][i].append(e_track)
            
            e_est = np.linalg.norm(x_est - self.followers[i].x.flatten())
            self.history["estimation_errors"][i].append(e_est)
            
            # Cloud error
            follower_packet_stored = self.cloud_db.get(i+1, None)
            if follower_packet_stored:
                if self.shield_hmac:
                    x_cloud = np.array(follower_packet_stored["payload"]["state"])
                else:
                    x_cloud = np.array(follower_packet_stored["state"])
                e_cloud = np.linalg.norm(x_cloud - self.followers[i].x.flatten())
            else:
                e_cloud = 0.0
            self.history["cloud_est_errors"][i].append(e_cloud)
            
            # Lyapunov V(t)
            e_state_vec = (self.followers[i].x.flatten() - x_L).reshape(4, 1)
            V_val = (e_state_vec.T @ self.P_lyap @ e_state_vec).item()
            self.history["lyapunov_values"][i].append(V_val)
            
            # Control command magnitude
            self.history["control_inputs"][i].append(float(np.linalg.norm(u_cmd)))

        # Update physical leader state space
        self.x_L_state = self.A_d @ self.x_L_state + self.B_d @ u_L
        
        # Increment time
        self.t += self.dt
        self.current_step_idx += 1
        
        # Return package of current frame data
        return {
            "time": self.t - self.dt,
            "leader": self.history["leader"][-1],
            "followers": [self.history["followers"][i][-1] for i in range(self.n_followers)],
            "filters": [self.history["filters"][i][-1] for i in range(self.n_followers)],
            "tracking_errors": [self.history["tracking_errors"][i][-1] for i in range(self.n_followers)],
            "estimation_errors": [self.history["estimation_errors"][i][-1] for i in range(self.n_followers)],
            "cloud_est_errors": [self.history["cloud_est_errors"][i][-1] for i in range(self.n_followers)],
            "lyapunov_values": [self.history["lyapunov_values"][i][-1] for i in range(self.n_followers)],
            "control_inputs": [self.history["control_inputs"][i][-1] for i in range(self.n_followers)],
            "network_status": status_str
        }
