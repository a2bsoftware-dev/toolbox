import numpy as np
import scipy.linalg as la

class Controller:
    def __init__(self,A,B,initial_state):
        self.A = np.array(A)
        self.B = np.array(B)
        self.x = np.array(initial_state)

        self.K = self.design_controller()

    def design_controller(self):
        Q = np.eye(self.A.shape[0]) * 10
        R = np.eye(self.B.shape[1]) * 1
        P = la.solve_continuous_are(self.A, self.B, Q, R)

        K = la.inv(R) @ self.B.T @ P
        return K

    def compute_control_input(self,x_leader):
        error = self.x - x_leader
        u = -self.K @ error
        return u

    def update_physics(self,u,dt):

        dx = (self.A @ self.x) + (self.B @ u)
        self.x += dt * dx



import matplotlib.pyplot as plt


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

for t in range(time_steps):

    if t > 100:
        leader_state[0] += 0.5 * dt 
        leader_state[1] = 0.5 


    u = follower.compute_control_input(leader_state)

    follower.update_physics(u, dt)


    history_follower_pos.append(follower.x[0])
    history_leader_pos.append(leader_state[0])

plt.figure(figsize=(10, 5))
plt.plot(history_leader_pos, label="Leader Position", linestyle="--", color="black")
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