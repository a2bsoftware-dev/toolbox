# Testing Guide: Secure NCS Desktop Toolbox

This document provides instructions on how to test the Networked Control System (NCS) simulation engines, solvers, and custom GUI modules.

---

## 📂 Testing Architecture Overview

Our test suite is organized into three primary layers:
1. **Headless Compilation Verification**: Checks syntax errors and import linkages across all modules recursively.
2. **Headless Simulation Runner**: Verifies discrete/continuous dynamics propagation, CARE/DARE solvers, and observer estimations without mounting a display.
3. **Module 4 Scenario Integration Tester**: Simulates comparative security scenarios (Ideal, Attacked, Defended), compiles statistics, and generates comparison plots.
4. **GUI Verification**: Boots the CustomTkinter MVC desktop interface.

---

## 1. Headless Compilation Scans

To confirm that there are no syntax errors or unresolved imports, run the compilation script:

```powershell
python .gemini/antigravity/brain/980c1b96-71d7-4408-81e5-153d64cf3697/scratch/verify_compilation.py
```

This script scans all subfolders recursively, compiling every `.py` file. A successful output confirms:
`All Python files compiled successfully!`

---

## 2. Headless Simulator Runner

To verify the mathematical dynamics, CARE/DARE gains synthesis, and state estimator correction loops, run the test runner script:

```powershell
python .gemini/antigravity/brain/980c1b96-71d7-4408-81e5-153d64cf3697/scratch/test_simulator.py
```

This script runs three automated test cases:
1. **Continuous Domain Propagation**: Validates exact ZOH matrix exponent discretization ($e^{M \cdot \Delta t}$).
2. **Discrete Domain Propagation**: Validates Euler discretization.
3. **Application Control Policy Fallbacks**: Simulates a system where `scipy.signal` is blocked by Windows Defender Application Control (WDAC), verifying that LQR/Kalman filters fall back gracefully to steady-state DARE matrices to prevent startup crashes.

---

## 3. Module 4 Integration & Scenario Tester

The script [Tester/tester.py](file:///c:/Users/ravis/Desktop/toolbox/Tester/tester.py) runs the complete multi-agent simulation comparison.

### Execution Command
Run all scenarios with default settings:
```powershell
python Tester/tester.py
```

### CLI Command Options
Modify simulation scenarios using the following CLI arguments:
* `-c`, `--config`: Specify custom JSON parameter configuration (default: `config.json`).
* `-s`, `--scenario`: Run a specific scenario (`ideal`, `attacked`, `defended`, or `all` to run all three).
* `-o`, `--output`: Define path to save comparison plot (default: `simulation_results.png`).
* `-l`, `--log-level`: Set shell verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`).

Example:
```powershell
python Tester/tester.py --scenario defended --log-level WARNING
```

### Interpreting Output Metrics

Upon completion, `tester.py` prints a comparison table to the console:
* **Consensus Error (Avg)**: The average position offset between followers and the leader. In a defended system, this value should be close to the ideal value (approx. `0.58m`), whereas an attacked system drifts (approx. `5.2m`).
* **Cloud Telemetry Err (Avg)**: The difference between the physical follower state and the state uploaded to the database. Defended systems reject cyber-tampering, resulting in low tracking errors.
* **Control Input Norm (Avg)**: The average control effort magnitude. Spikes indicate controller saturation under false data injection.
* **Closed-Loop Stability**: Confirms whether continuous s-plane eigenvalues remain strictly in the Left-Half Plane ($\text{Re}(\lambda) < 0$).

---

## 4. GUI & Desktop Application Verification

To test the interactive desktop dashboard:

1. **Boot App**:
   ```powershell
   python app.py
   ```
2. **Verify Solver Designer**:
   * Click on the **Controller Designer** tab in the sidebar.
   * Edit matrix values in the grid editor.
   * Click **Solve CARE/DARE** and verify that eigenvalues are updated and the stability label displays "Stable: True (Schur)".
3. **Verify Cyber Threats**:
   * Switch to the **Cyber Threats** tab in the sidebar.
   * Toggle **Differential Privacy (DP)**, **HMAC Cryptography**, and **Anomaly Detection**.
   * Run the simulation by pressing **Play** and observe particle colors change in the animator panel.
4. **Verify Save/Load & Reports**:
   * Save configuration parameters to `.toolbox` project database using **Save Project**.
   * Export the simulation runs using **Export PDF Report** or **Export CSV Log Sheet**.
