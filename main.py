import numpy as np
import matplotlib.pyplot as plt
from Controller.controller import Controller
from Tester.testerAttack import testAttackSimulation

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
last_received_leader_state = np.copy(leader_state)

for t in range(time_steps):

    if t > 100:
        leader_state[0] += 0.5 * dt 
        leader_state[1] = 0.5 

    # Activate the attack halfway through the simulation
    hacker.attack_active = t > 250
    
    # Simulate a False Data Injection (FDI) attack
    corrupted_leader_state = hacker.false_data_injection(leader_state, offset=10.0)
    
    # (Optional) Simulate Denial of Service (DoS) attack instead:
    # corrupted_leader_state = hacker.denial_of_service(leader_state, last_received_leader_state, drop_rate=0.8)
    # last_received_leader_state = np.copy(corrupted_leader_state)

    # Follower calculates thrust based on the corrupted data
    u = follower.compute_control_input(corrupted_leader_state)

    follower.update_physics(u, dt)

    history_follower_pos.append(follower.x[0])
    history_leader_pos.append(leader_state[0])
    history_corrupted_pos.append(corrupted_leader_state[0])

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
# At time step 0, the black dashed line (Leader) should be at 10, and the blue solid line (Follower) should be at 0.
# Over the first 100 time steps, the blue line should steeply curve upward and smoothly merge with the black line. This proves your $K$ matrix successfully calculated the exact thrust needed to close the 10-meter gap.
# At time step 100, the Leader starts moving forward (the black line will slope upwards). The Follower's blue line should perfectly track this slope without lagging behind or oscillating wildly.
