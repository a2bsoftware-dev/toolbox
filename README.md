# Secure Cloud-Based Multi-Agent Control Toolbox

A modular, centralized **Leader-Follower Networked Control System (NCS)** simulation environment. This toolbox simulates a fleet of independent linear time-invariant (LTI) physical plants (e.g., drones or vehicles) coordinating under physical disturbances and measurement noise. It also contains an attack simulator (FDI and DoS) and corresponding cyber defense mechanisms (Encryption and Differential Privacy).

---

## 📖 Mathematical Formulation

### 1. Plant Dynamics & Discretization
Each agent $i$ is modeled as a continuous-time double integrator with drag (damping coefficient $d$):
$$\dot{x}_i(t) = A x_i(t) + B u_i(t) + w_i(t)$$
$$y_i(t) = C x_i(t) + v_i(t)$$

Where:
- State $x_i(t) = [p_x, v_x, p_y, v_y]^T \in \mathbb{R}^4$ represent position and velocity in $x$ and $y$ dimensions.
- Control input $u_i(t) = [a_x, a_y]^T \in \mathbb{R}^2$ represent acceleration commands.
- $w_i(t) \sim \mathcal{N}(0, Q_c)$ is the continuous process noise (wind/disturbances).
- $y_i(t) \in \mathbb{R}^2$ is the measured positions.
- $v_i(t) \sim \mathcal{N}(0, R_c)$ is the measurement noise (GPS inaccuracies).

The system matrices are:
$$A = \begin{bmatrix} 0 & 1 & 0 & 0 \\ 0 & -d & 0 & 0 \\ 0 & 0 & 0 & 1 \\ 0 & 0 & 0 & -d \end{bmatrix}, \quad B = \begin{bmatrix} 0 & 0 \\ 1 & 0 \\ 0 & 0 \\ 0 & 1 \end{bmatrix}, \quad C = \begin{bmatrix} 1 & 0 & 0 & 0 \\ 0 & 0 & 1 & 0 \end{bmatrix}$$

Using a simulation step size $\Delta t$, the discretized dynamics are:
$$x_i[k+1] = A_d x_i[k] + B_d u_i[k] + w_i[k]$$
$$y_i[k] = C_d x_i[k] + v_i[k]$$
where:
$$A_d = e^{A \Delta t} \approx I + A \Delta t = \begin{bmatrix} 1 & \Delta t & 0 & 0 \\ 0 & 1 - d\Delta t & 0 & 0 \\ 0 & 0 & 1 & \Delta t \\ 0 & 0 & 0 & 1 - d\Delta t \end{bmatrix}$$
$$B_d = \int_0^{\Delta t} e^{A \tau} B d\tau \approx B \Delta t = \begin{bmatrix} 0 & 0 \\ \Delta t & 0 \\ 0 & 0 \\ 0 & \Delta t \end{bmatrix}$$
$$C_d = C$$

---

### 2. Module 2: Observer Design (Kalman Filter)
Since we only measure position directly ($y_i = [p_{x,noisy}, p_{y,noisy}]^T$), and our measurements are noisy, each agent runs a discrete-time **Kalman Filter** to estimate its full state $\hat{x}_i$:

1. **Prediction Step**:
   $$\hat{x}_i^-[k] = A_d \hat{x}_i[k-1] + B_d u_i[k-1]$$
   $$P_i^-[k] = A_d P_i[k-1] A_d^T + Q$$

2. **Measurement Update Step**:
   $$K[k] = P_i^-[k] C_d^T (C_d P_i^-[k] C_d^T + R)^{-1}$$
   $$\hat{x}_i[k] = \hat{x}_i^-[k] + K[k](y_i[k] - C_d \hat{x}_i^-[k])$$
   $$P_i[k] = (I - K[k] C_d) P_i^-[k]$$

Where:
- $Q$ is the process noise covariance matrix.
- $R$ is the measurement noise covariance matrix.
- $P_i[k]$ is the estimation error covariance matrix.

---

### 3. Module 1: Controller & Stability Analysis
The followers track a dynamic leader $L$ whose state $x_L[k]$ is updated and routed via the Cloud.
The consensus tracking control input $u_i[k]$ for follower $i$ is computed using the estimated state $\hat{x}_i[k]$:
$$u_i[k] = K_{fb} (x_L[k] - \hat{x}_i[k])$$
where $K_{fb} \in \mathbb{R}^{2 \times 4}$ is synthesized via LQR (Linear Quadratic Regulator) to stabilize the tracking error:
$$e_i[k] = x_i[k] - x_L[k]$$

Stability is verified analytically by ensuring all eigenvalues of the closed-loop state matrix $A_{cl} = A_d - B_d K_{fb}$ lie strictly inside the unit circle:
$$\max_j |\lambda_j(A_{cl})| < 1$$

---

### 4. Module 3: Attack Injection
The communication network is vulnerable to cyber threats:
1. **False Data Injection (FDI)**: The adversary intercepts and adds a malicious offset $x_{attack}$ to the state vectors stored/transmitted by the cloud.
   $$x_{cloud, i}[k] = x_i[k] + x_{attack}$$
2. **Denial of Service (DoS)**: The adversary drops transmission packets, preventing state updates. The cloud or agents hold the last received state (zero-order hold).

---

### 5. Module 4: Cyber Defense & Mitigation
1. **Cryptographic Authentication**: Simulated public-private key handshake and signatures. If a packet is tampered with (FDI), the signature verification fails and the packet is rejected.
2. **Differential Privacy (DP)**: Obfuscates agent locations to protect privacy. Before uploading state estimates to the cloud, the agent injects zero-mean Laplace noise:
   $$\tilde{x}_i[k] = \hat{x}_i[k] + \eta_i[k], \quad \eta_i[k] \sim \text{Laplace}(0, b)$$
   where $b$ is the scale parameter determined by the privacy budget $\epsilon$.

---

## 📂 Repository Structure

- `Controller/controller.py`: Module 1 - Control design, tracking calculation, and Lyapunov/eigenvalue stability analysis.
- `Filter/filter.py`: Module 2 - Discrete Kalman Filter implementation.
- `Shield/shield.py`: Module 4 - Cryptographic handshake and Differential Privacy noise addition.
- `Tester/tester.py`: Module 3 - Attack simulation, master loop orchestrator, and Matplotlib plotting.

---

## 🚀 Getting Started

### Prerequisites
Make sure you have Python 3 and the following scientific libraries installed:
```bash
pip install numpy scipy matplotlib
```

### Running the Simulation
Execute the master script to run all 3 scenarios (Ideal, Attacked, and Defended) and generate graphs:
```bash
python Tester/tester.py
```
This will output a set of visual charts comparing tracking error and estimation precision across all scenarios.