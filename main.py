import argparse
import sys
import logging

def run_gui():
    from gui.main_window import MainWindow
    from utils.config import load_config, load_env

    logging.basicConfig(level=logging.INFO)
    load_env()
    config = load_config()
    app = MainWindow(config)
    app.mainloop()

def run_cli(unknown_args):
    # Pass unknown args down to Tester's CLI
    sys.argv = [sys.argv[0]] + unknown_args
    from Tester.tester import main as tester_main
    tester_main()

def run_basic_test():
    import numpy as np
    import matplotlib.pyplot as plt
    from Controller.controller import Controller
    from Tester.testerAttack import testAttackSimulation
    from Shield.shield import SecureChannel, DifferentialPrivacy
    from utils.config import load_env

    load_env()

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
    history_corrupted_pos = []
    hacker = testAttackSimulation()
    shield_channel = SecureChannel(secret_key="test_key")
    shield_dp = DifferentialPrivacy(epsilon=1.5, sensitivity=0.1)
    
    last_received_leader_state = np.copy(leader_state)

    for t in range(time_steps):

        if t > 100:
            leader_state[0] += 0.5 * dt 
            leader_state[1] = 0.5 

        # --- SENDER (Leader) ---
        noisy_leader_state = shield_dp.obfuscate_state(leader_state)
        packet = shield_channel.generate_packet(agent_id=0, state=noisy_leader_state, timestamp=t*dt)

        # --- NETWORK & HACKER ---
        hacker.attack_active = t > 250
        
        # Hacker attempts FDI
        corrupted_state = hacker.false_data_injection(noisy_leader_state, offset=10.0)
        packet["payload"]["state"] = corrupted_state.flatten().tolist()
        
        # Hacker attempts DoS (packet dropping)
        # Using 1 for True, 0 for False to mimic dropping a packet
        if hacker.denial_of_service(1, 0, drop_rate=0.6) == 0:
            packet_received = None
            packet_state_for_plot = last_received_leader_state
        else:
            packet_received = packet
            packet_state_for_plot = corrupted_state

        # --- RECEIVER (Follower) ---
        if packet_received is None:
            # Packet dropped (DoS)
            accepted_state = last_received_leader_state
        else:
            # Packet arrived! Verify signature (FDI check)
            if shield_channel.verify_packet(packet_received):
                accepted_state = np.array(packet_received["payload"]["state"])
                last_received_leader_state = np.copy(accepted_state)
            else:
                # Intrusion Detected! Reject tampered data.
                accepted_state = last_received_leader_state

        # Follower calculates thrust based on the accepted data
        u = follower.compute_control_input(accepted_state)
        follower.update_physics(u, dt)

        history_follower_pos.append(follower.x[0])
        history_leader_pos.append(leader_state[0])
        history_corrupted_pos.append(packet_state_for_plot[0])

    plt.figure(figsize=(10, 5))
    plt.plot(history_leader_pos, label="True Leader Position", linestyle="--", color="black")
    plt.plot(history_corrupted_pos, label="Corrupted Leader (Hacked)", linestyle=":", color="red")
    plt.plot(history_follower_pos, label="Follower Position", color="blue")
    plt.title("Module 1 Test: Drone Tracking")
    plt.xlabel("Time Steps")
    plt.ylabel("Position (Meters)")
    plt.legend()
    plt.grid(True)
    plt.show()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="A2B Toolbox Unified Launcher")
    parser.add_argument("--mode", type=str, choices=["gui", "cli", "test"], default="gui",
                        help="Select 'gui' for the main application, 'cli' for full simulation, or 'test' for the basic drone tracking test.")
    
    args, unknown = parser.parse_known_args()
    
    if args.mode == "gui":
        run_gui()
    elif args.mode == "cli":
        run_cli(unknown)
    elif args.mode == "test":
        run_basic_test()
