import customtkinter as ctk
import tkinter as tk

class AttacksDefensesPanel(ctk.CTkScrollableFrame):
    """
    Threat configuration panel containing attack vector checkboxes/parameters
    and cybersecurity defense mechanism switches.
    """
    def __init__(self, parent, on_update_callback, **kwargs):
        super().__init__(parent, **kwargs)
        self.on_update = on_update_callback
        
        self.configure(fg_color="#0f172a") # Slate-900 background
        
        self.setup_widgets()
        
    def setup_widgets(self):
        title_font = ctk.CTkFont(family="Helvetica", size=13, weight="bold")
        lbl_font = ctk.CTkFont(family="Helvetica", size=11)
        
        # 1. Section: Attack Vectors
        ctk.CTkLabel(self, text="🚨 Attack Vectors", font=title_font, text_color="#ef4444").pack(anchor="w", pady=(5, 5))
        
        # FDI Checkbox & parameters
        self.fdi_var = tk.BooleanVar(value=True)
        self.fdi_cb = ctk.CTkCheckBox(self, text="False Data Injection (FDI)", font=lbl_font, variable=self.fdi_var,
                                       fg_color="#ef4444", hover_color="#dc2626", command=self.trigger_update)
        self.fdi_cb.pack(anchor="w", pady=2)
        
        fdi_frame = ctk.CTkFrame(self, fg_color="transparent")
        fdi_frame.pack(fill="x", padx=15, pady=2)
        ctk.CTkLabel(fdi_frame, text="Interval (s):", font=lbl_font, width=70, anchor="w").pack(side="left")
        self.fdi_start = ctk.CTkEntry(fdi_frame, width=50, height=20)
        self.fdi_start.pack(side="left")
        ctk.CTkLabel(fdi_frame, text=" to ", font=lbl_font).pack(side="left")
        self.fdi_end = ctk.CTkEntry(fdi_frame, width=50, height=20)
        self.fdi_end.pack(side="left")
        
        fdi_offset_frame = ctk.CTkFrame(self, fg_color="transparent")
        fdi_offset_frame.pack(fill="x", padx=15, pady=2)
        ctk.CTkLabel(fdi_offset_frame, text="Offset (x,y):", font=lbl_font, width=70, anchor="w").pack(side="left")
        self.fdi_offset = ctk.CTkEntry(fdi_offset_frame, width=120, height=20)
        self.fdi_offset.pack(side="left")
        
        # DoS Checkbox & parameters
        self.dos_var = tk.BooleanVar(value=True)
        self.dos_cb = ctk.CTkCheckBox(self, text="Denial of Service (DoS)", font=lbl_font, variable=self.dos_var,
                                       fg_color="#ef4444", hover_color="#dc2626", command=self.trigger_update)
        self.dos_cb.pack(anchor="w", pady=(10, 2))
        
        dos_frame = ctk.CTkFrame(self, fg_color="transparent")
        dos_frame.pack(fill="x", padx=15, pady=2)
        ctk.CTkLabel(dos_frame, text="Interval (s):", font=lbl_font, width=70, anchor="w").pack(side="left")
        self.dos_start = ctk.CTkEntry(dos_frame, width=50, height=20)
        self.dos_start.pack(side="left")
        ctk.CTkLabel(dos_frame, text=" to ", font=lbl_font).pack(side="left")
        self.dos_end = ctk.CTkEntry(dos_frame, width=50, height=20)
        self.dos_end.pack(side="left")
        
        # Delay Checkbox & parameters
        self.delay_var = tk.BooleanVar(value=False)
        self.delay_cb = ctk.CTkCheckBox(self, text="Delay Attack", font=lbl_font, variable=self.delay_var,
                                         fg_color="#ef4444", hover_color="#dc2626", command=self.trigger_update)
        self.delay_cb.pack(anchor="w", pady=(10, 2))
        
        delay_frame = ctk.CTkFrame(self, fg_color="transparent")
        delay_frame.pack(fill="x", padx=15, pady=2)
        ctk.CTkLabel(delay_frame, text="Interval (s):", font=lbl_font, width=70, anchor="w").pack(side="left")
        self.delay_start = ctk.CTkEntry(delay_frame, width=50, height=20)
        self.delay_start.pack(side="left")
        ctk.CTkLabel(delay_frame, text=" to ", font=lbl_font).pack(side="left")
        self.delay_end = ctk.CTkEntry(delay_frame, width=50, height=20)
        self.delay_end.pack(side="left")
        
        delay_steps_frame = ctk.CTkFrame(self, fg_color="transparent")
        delay_steps_frame.pack(fill="x", padx=15, pady=2)
        ctk.CTkLabel(delay_steps_frame, text="Steps (1-10):", font=lbl_font, width=70, anchor="w").pack(side="left")
        self.delay_steps = ctk.CTkEntry(delay_steps_frame, width=50, height=20)
        self.delay_steps.pack(side="left")
        
        # Replay Checkbox & parameters
        self.replay_var = tk.BooleanVar(value=False)
        self.replay_cb = ctk.CTkCheckBox(self, text="Replay Attack", font=lbl_font, variable=self.replay_var,
                                          fg_color="#ef4444", hover_color="#dc2626", command=self.trigger_update)
        self.replay_cb.pack(anchor="w", pady=(10, 2))
        
        replay_frame = ctk.CTkFrame(self, fg_color="transparent")
        replay_frame.pack(fill="x", padx=15, pady=2)
        ctk.CTkLabel(replay_frame, text="Interval (s):", font=lbl_font, width=70, anchor="w").pack(side="left")
        self.replay_start = ctk.CTkEntry(replay_frame, width=50, height=20)
        self.replay_start.pack(side="left")
        ctk.CTkLabel(replay_frame, text=" to ", font=lbl_font).pack(side="left")
        self.replay_end = ctk.CTkEntry(replay_frame, width=50, height=20)
        self.replay_end.pack(side="left")
        
        # 2. Section: Defense Modules
        ctk.CTkLabel(self, text="🛡️ Cyber Defense Shields", font=title_font, text_color="#10b981").pack(anchor="w", pady=(20, 5))
        
        # HMAC Authentication
        self.hmac_var = tk.BooleanVar(value=True)
        self.hmac_cb = ctk.CTkCheckBox(self, text="HMAC-SHA256 Signatures", font=lbl_font, variable=self.hmac_var,
                                        fg_color="#10b981", hover_color="#059669", command=self.trigger_update)
        self.hmac_cb.pack(anchor="w", pady=3)
        
        # Differential Privacy
        self.dp_var = tk.BooleanVar(value=True)
        self.dp_cb = ctk.CTkCheckBox(self, text="Differential Privacy Noise", font=lbl_font, variable=self.dp_var,
                                      fg_color="#10b981", hover_color="#059669", command=self.trigger_update)
        self.dp_cb.pack(anchor="w", pady=3)
        
        dp_frame = ctk.CTkFrame(self, fg_color="transparent")
        dp_frame.pack(fill="x", padx=15, pady=2)
        ctk.CTkLabel(dp_frame, text="Privacy Budget (ε):", font=lbl_font, width=120, anchor="w").pack(side="left")
        self.dp_epsilon = ctk.CTkEntry(dp_frame, width=65, height=20)
        self.dp_epsilon.pack(side="left")
        
        # Anomaly Detection (IDS)
        self.anomaly_var = tk.BooleanVar(value=True)
        self.anomaly_cb = ctk.CTkCheckBox(self, text="Anomaly Detection (IDS)", font=lbl_font, variable=self.anomaly_var,
                                           fg_color="#10b981", hover_color="#059669", command=self.trigger_update)
        self.anomaly_cb.pack(anchor="w", pady=3)
        
        ids_frame = ctk.CTkFrame(self, fg_color="transparent")
        ids_frame.pack(fill="x", padx=15, pady=2)
        ctk.CTkLabel(ids_frame, text="Residual Threshold:", font=lbl_font, width=120, anchor="w").pack(side="left")
        self.ids_threshold = ctk.CTkEntry(ids_frame, width=65, height=20)
        self.ids_threshold.pack(side="left")
        
        # Trust Filter
        self.trust_var = tk.BooleanVar(value=True)
        self.trust_cb = ctk.CTkCheckBox(self, text="Reputation/Trust Filter", font=lbl_font, variable=self.trust_var,
                                         fg_color="#10b981", hover_color="#059669", command=self.trigger_update)
        self.trust_cb.pack(anchor="w", pady=3)
        
        # Apply edits button
        self.apply_btn = ctk.CTkButton(self, text="Save Cybersecurity Settings", fg_color="#1e293b",
                                        hover_color="#334155", command=self.trigger_update)
        self.apply_btn.pack(fill="x", pady=15)
        
        self.active_config = None
        
    def load_configuration(self, config: dict):
        self.active_config = config
        
        # Load Attacks configuration
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
        self.delay_steps.delete(0, "end")
        self.delay_steps.insert(0, str(att.get("delay", {}).get("steps", 5)))
        
        self.replay_var.set(att.get("enable_replay", False))
        self.replay_start.delete(0, "end")
        self.replay_start.insert(0, str(att.get("replay", {}).get("start_time", 60.0)))
        self.replay_end.delete(0, "end")
        self.replay_end.insert(0, str(att.get("replay", {}).get("end_time", 70.0)))
        
        # Load Defenses configuration
        sec = config["security"]
        self.hmac_var.set(sec.get("enable_hmac", True))
        self.dp_var.set(sec.get("enable_dp", True))
        self.dp_epsilon.delete(0, "end")
        self.dp_epsilon.insert(0, str(sec.get("dp_epsilon", 1.5)))
        
        self.anomaly_var.set(sec.get("enable_anomaly", True))
        self.ids_threshold.delete(0, "end")
        self.ids_threshold.insert(0, str(sec.get("anomaly_threshold", 5.0)))
        
        self.trust_var.set(sec.get("enable_trust", True))
        
    def trigger_update(self):
        if not self.active_config:
            return
            
        try:
            # FDI offset parsing
            fdi_offset_str = self.fdi_offset.get().split(",")
            offset_arr = [float(o.strip()) for o in fdi_offset_str]
            if len(offset_arr) != 4:
                raise ValueError("FDI offset must contain exactly 4 values.")
                
            # Save inputs back to active config dict
            self.active_config["attacks"]["enable_fdi"] = self.fdi_var.get()
            self.active_config["attacks"]["fdi"]["start_time"] = float(self.fdi_start.get())
            self.active_config["attacks"]["fdi"]["end_time"] = float(self.fdi_end.get())
            self.active_config["attacks"]["fdi"]["offset"] = offset_arr
            
            self.active_config["attacks"]["enable_dos"] = self.dos_var.get()
            self.active_config["attacks"]["dos"]["start_time"] = float(self.dos_start.get())
            self.active_config["attacks"]["dos"]["end_time"] = float(self.dos_end.get())
            
            self.active_config["attacks"]["enable_delay"] = self.delay_var.get()
            self.active_config["attacks"]["delay"] = {
                "start_time": float(self.delay_start.get()),
                "end_time": float(self.delay_end.get()),
                "steps": int(self.delay_steps.get())
            }
            
            self.active_config["attacks"]["enable_replay"] = self.replay_var.get()
            self.active_config["attacks"]["replay"] = {
                "start_time": float(self.replay_start.get()),
                "end_time": float(self.replay_end.get()),
                "window_size": 40
            }
            
            self.active_config["security"]["enable_hmac"] = self.hmac_var.get()
            self.active_config["security"]["enable_dp"] = self.dp_var.get()
            self.active_config["security"]["dp_epsilon"] = float(self.dp_epsilon.get())
            self.active_config["security"]["enable_anomaly"] = self.anomaly_var.get()
            self.active_config["security"]["anomaly_threshold"] = float(self.ids_threshold.get())
            self.active_config["security"]["enable_trust"] = self.trust_var.get()
            
            # Fire configuration update callback
            self.on_update(self.active_config)
            
        except Exception as e:
            tk.messagebox.showerror("Cyber Parameter Error", f"Failed to save settings: {e}")
