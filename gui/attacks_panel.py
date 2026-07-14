import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox

class AttacksPanel(ctk.CTkScrollableFrame):
    """
    Threat configuration panel (Phase 5/8) containing attack vector checkboxes
    and cybersecurity defense mechanism toggles.
    """
    def __init__(self, parent, config: dict, on_update_callback, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        
        self.config = config
        self.on_update = on_update_callback
        
        self.setup_widgets()
        self.load_configuration(config)
        
    def setup_widgets(self):
        title_font = ctk.CTkFont(family="Helvetica", size=12, weight="bold")
        lbl_font = ctk.CTkFont(family="Helvetica", size=11)
        
        # 1. Section: Attack Vectors
        ctk.CTkLabel(self, text="🚨 Active Cyber Attack Vectors", font=title_font, text_color="#ef4444").pack(anchor="w", pady=(5, 2))
        
        # FDI
        self.fdi_var = tk.BooleanVar(value=True)
        self.fdi_cb = ctk.CTkCheckBox(self, text="False Data Injection (FDI)", font=lbl_font, variable=self.fdi_var,
                                       fg_color="#ef4444", hover_color="#dc2626")
        self.fdi_cb.pack(anchor="w", pady=2)
        
        fdi_frame = ctk.CTkFrame(self, fg_color="transparent")
        fdi_frame.pack(fill="x", padx=15, pady=2)
        ctk.CTkLabel(fdi_frame, text="Active (s):", font=lbl_font, width=70, anchor="w").pack(side="left")
        self.fdi_start = ctk.CTkEntry(fdi_frame, width=50, height=20, fg_color="#1e293b")
        self.fdi_start.pack(side="left")
        ctk.CTkLabel(fdi_frame, text=" to ", font=lbl_font).pack(side="left")
        self.fdi_end = ctk.CTkEntry(fdi_frame, width=50, height=20, fg_color="#1e293b")
        self.fdi_end.pack(side="left")
        
        fdi_offset_frame = ctk.CTkFrame(self, fg_color="transparent")
        fdi_offset_frame.pack(fill="x", padx=15, pady=2)
        ctk.CTkLabel(fdi_offset_frame, text="Offset (x,y):", font=lbl_font, width=70, anchor="w").pack(side="left")
        self.fdi_offset = ctk.CTkEntry(fdi_offset_frame, width=120, height=20, fg_color="#1e293b")
        self.fdi_offset.pack(side="left")
        
        # DoS
        self.dos_var = tk.BooleanVar(value=True)
        self.dos_cb = ctk.CTkCheckBox(self, text="Denial of Service (DoS)", font=lbl_font, variable=self.dos_var,
                                       fg_color="#ef4444", hover_color="#dc2626")
        self.dos_cb.pack(anchor="w", pady=(10, 2))
        
        dos_frame = ctk.CTkFrame(self, fg_color="transparent")
        dos_frame.pack(fill="x", padx=15, pady=2)
        ctk.CTkLabel(dos_frame, text="Active (s):", font=lbl_font, width=70, anchor="w").pack(side="left")
        self.dos_start = ctk.CTkEntry(dos_frame, width=50, height=20, fg_color="#1e293b")
        self.dos_start.pack(side="left")
        ctk.CTkLabel(dos_frame, text=" to ", font=lbl_font).pack(side="left")
        self.dos_end = ctk.CTkEntry(dos_frame, width=50, height=20, fg_color="#1e293b")
        self.dos_end.pack(side="left")
        
        # Delay
        self.delay_var = tk.BooleanVar(value=False)
        self.delay_cb = ctk.CTkCheckBox(self, text="Network Delay Attack", font=lbl_font, variable=self.delay_var,
                                         fg_color="#ef4444", hover_color="#dc2626")
        self.delay_cb.pack(anchor="w", pady=(10, 2))
        
        delay_frame = ctk.CTkFrame(self, fg_color="transparent")
        delay_frame.pack(fill="x", padx=15, pady=2)
        ctk.CTkLabel(delay_frame, text="Active (s):", font=lbl_font, width=70, anchor="w").pack(side="left")
        self.delay_start = ctk.CTkEntry(delay_frame, width=50, height=20, fg_color="#1e293b")
        self.delay_start.pack(side="left")
        ctk.CTkLabel(delay_frame, text=" to ", font=lbl_font).pack(side="left")
        self.delay_end = ctk.CTkEntry(delay_frame, width=50, height=20, fg_color="#1e293b")
        self.delay_end.pack(side="left")
        
        # Replay
        self.replay_var = tk.BooleanVar(value=False)
        self.replay_cb = ctk.CTkCheckBox(self, text="Packet Replay Attack", font=lbl_font, variable=self.replay_var,
                                          fg_color="#ef4444", hover_color="#dc2626")
        self.replay_cb.pack(anchor="w", pady=(10, 2))
        
        replay_frame = ctk.CTkFrame(self, fg_color="transparent")
        replay_frame.pack(fill="x", padx=15, pady=2)
        ctk.CTkLabel(replay_frame, text="Active (s):", font=lbl_font, width=70, anchor="w").pack(side="left")
        self.replay_start = ctk.CTkEntry(replay_frame, width=50, height=20, fg_color="#1e293b")
        self.replay_start.pack(side="left")
        ctk.CTkLabel(replay_frame, text=" to ", font=lbl_font).pack(side="left")
        self.replay_end = ctk.CTkEntry(replay_frame, width=50, height=20, fg_color="#1e293b")
        self.replay_end.pack(side="left")
        
        # 2. Section: Defense Shields
        ctk.CTkLabel(self, text="🛡️ Cyber Security Shields", font=title_font, text_color="#10b981").pack(anchor="w", pady=(15, 2))
        
        self.hmac_var = tk.BooleanVar(value=True)
        self.hmac_cb = ctk.CTkCheckBox(self, text="HMAC-SHA256 Signatures", font=lbl_font, variable=self.hmac_var,
                                        fg_color="#10b981", hover_color="#059669")
        self.hmac_cb.pack(anchor="w", pady=2)
        
        self.dp_var = tk.BooleanVar(value=True)
        self.dp_cb = ctk.CTkCheckBox(self, text="Differential Privacy Noise", font=lbl_font, variable=self.dp_var,
                                      fg_color="#10b981", hover_color="#059669")
        self.dp_cb.pack(anchor="w", pady=2)
        
        dp_frame = ctk.CTkFrame(self, fg_color="transparent")
        dp_frame.pack(fill="x", padx=15, pady=2)
        ctk.CTkLabel(dp_frame, text="Privacy Budget (ε):", font=lbl_font, width=120, anchor="w").pack(side="left")
        self.dp_epsilon = ctk.CTkEntry(dp_frame, width=60, height=20, fg_color="#1e293b")
        self.dp_epsilon.pack(side="left")
        
        self.anomaly_var = tk.BooleanVar(value=True)
        self.anomaly_cb = ctk.CTkCheckBox(self, text="Anomaly Detection (IDS)", font=lbl_font, variable=self.anomaly_var,
                                           fg_color="#10b981", hover_color="#059669")
        self.anomaly_cb.pack(anchor="w", pady=2)
        
        self.trust_var = tk.BooleanVar(value=True)
        self.trust_cb = ctk.CTkCheckBox(self, text="Reputation Trust Filter", font=lbl_font, variable=self.trust_var,
                                         fg_color="#10b981", hover_color="#059669")
        self.trust_cb.pack(anchor="w", pady=2)
        
        self.apply_btn = ctk.CTkButton(self, text="Save Security Toggles", fg_color="#10b981",
                                        hover_color="#059669", text_color="#0a0e17", font=ctk.CTkFont(weight="bold"),
                                        command=self.on_apply_clicked)
        self.apply_btn.pack(fill="x", pady=15)
        
    def load_configuration(self, config: dict):
        self.config = config
        
        # Load attacks
        att = config["attacks"]
        self.fdi_var.set(att.get("enable_fdi", True))
        self.fdi_start.delete(0, "end")
        self.fdi_start.insert(0, str(att["fdi"]["start_time"]))
        self.fdi_end.delete(0, "end")
        self.fdi_end.insert(0, str(att["fdi"]["end_time"]))
        self.fdi_offset.delete(0, "end")
        self.fdi_offset.insert(0, ", ".join(map(str, att["fdi"]["offset"])))
        
        self.dos_var.set(att.get("enable_dos", True))
        self.dos_start.delete(0, "end")
        self.dos_start.insert(0, str(att["dos"]["start_time"]))
        self.dos_end.delete(0, "end")
        self.dos_end.insert(0, str(att["dos"]["end_time"]))
        
        self.delay_var.set(att.get("enable_delay", False))
        self.delay_start.delete(0, "end")
        self.delay_start.insert(0, str(att.get("delay", {}).get("start_time", 50.0)))
        self.delay_end.delete(0, "end")
        self.delay_end.insert(0, str(att.get("delay", {}).get("end_time", 60.0)))
        
        self.replay_var.set(att.get("enable_replay", False))
        self.replay_start.delete(0, "end")
        self.replay_start.insert(0, str(att.get("replay", {}).get("start_time", 60.0)))
        self.replay_end.delete(0, "end")
        self.replay_end.insert(0, str(att.get("replay", {}).get("end_time", 70.0)))
        
        # Load defenses
        sec = config["security"]
        self.hmac_var.set(sec.get("enable_hmac", True))
        self.dp_var.set(sec.get("enable_dp", True))
        self.dp_epsilon.delete(0, "end")
        self.dp_epsilon.insert(0, str(sec.get("dp_epsilon", 1.5)))
        self.anomaly_var.set(sec.get("enable_anomaly", True))
        self.trust_var.set(sec.get("enable_trust", True))
        
    def on_apply_clicked(self):
        try:
            # Parse FDI offset
            offset_parts = self.fdi_offset.get().split(",")
            offset = [float(o.strip()) for o in offset_parts]
            if len(offset) != 4:
                raise ValueError("FDI offset must contain exactly 4 values.")
                
            # Update config dict
            self.config["attacks"]["enable_fdi"] = bool(self.fdi_cb.get())
            self.config["attacks"]["fdi"]["start_time"] = float(self.fdi_start.get())
            self.config["attacks"]["fdi"]["end_time"] = float(self.fdi_end.get())
            self.config["attacks"]["fdi"]["offset"] = offset
            
            self.config["attacks"]["enable_dos"] = bool(self.dos_cb.get())
            self.config["attacks"]["dos"]["start_time"] = float(self.dos_start.get())
            self.config["attacks"]["dos"]["end_time"] = float(self.dos_end.get())
            
            self.config["attacks"]["enable_delay"] = bool(self.delay_cb.get())
            self.config["attacks"]["delay"]["start_time"] = float(self.delay_start.get())
            self.config["attacks"]["delay"]["end_time"] = float(self.delay_end.get())
            
            self.config["attacks"]["enable_replay"] = bool(self.replay_cb.get())
            self.config["attacks"]["replay"]["start_time"] = float(self.replay_start.get())
            self.config["attacks"]["replay"]["end_time"] = float(self.replay_end.get())
            
            self.config["security"]["enable_hmac"] = bool(self.hmac_cb.get())
            self.config["security"]["enable_dp"] = bool(self.dp_cb.get())
            self.config["security"]["dp_epsilon"] = float(self.dp_epsilon.get())
            self.config["security"]["enable_anomaly"] = bool(self.anomaly_cb.get())
            self.config["security"]["enable_trust"] = bool(self.trust_cb.get())
            
            # Fire update notification callback
            self.on_update(self.config)
            
        except Exception as e:
            messagebox.showerror("Cyber Config Error", f"Failed to save settings: {e}")
