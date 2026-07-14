import json
from engine.simulator import NCSSimulator
from utils.config import load_config
import copy

config_secure = load_config()

config_insecure = copy.deepcopy(config_secure)
config_insecure["security"]["enable_hmac"] = False
config_insecure["security"]["enable_anomaly"] = False
config_insecure["attacks"]["enable_fdi"] = True
config_insecure["attacks"]["enable_dos"] = False

sim_sec = NCSSimulator(config_secure)
for _ in range(500):
    sim_sec.step()

sim_insec = NCSSimulator(config_insecure)
for _ in range(500):
    sim_insec.step()

fdi_start_idx = int(12.0 / config_secure["system"]["dt"])
fdi_end_idx = int(22.0 / config_secure["system"]["dt"])

err_sec_fdi = max(sim_sec.history["tracking_errors"][0][fdi_start_idx:fdi_end_idx])
err_insec_fdi = max(sim_insec.history["tracking_errors"][0][fdi_start_idx:fdi_end_idx])

print(f"Secure Max Error during FDI: {err_sec_fdi}")
print(f"Insecure Max Error during FDI: {err_insec_fdi}")

