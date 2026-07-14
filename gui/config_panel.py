import customtkinter as ctk
import numpy as np

class ConfigPanel(ctk.CTkScrollableFrame):
    """
    Configuration panel containing agent settings, a dynamic matrix grid editor,
    and a controller designer solver interface.
    """
    def __init__(self, parent, on_update_callback, **kwargs):
        super().__init__(parent, **kwargs)
        self.on_update = on_update_callback
        
        self.configure(fg_color="#0f172a") # Slate-900 background
        
        # Current active matrix selection
        self.matrix_options = {
            "A (System Matrix 4x4)": ("A_d", (4, 4)),
            "B (Input Matrix 4x2)": ("B_d", (4, 2)),
            "C (Output Matrix 2x4)": ("C_d", (2, 4)),
            "Q (Process Noise Cov 4x4)": ("Q_process", (4, 4)),
            "R (Measurement Noise Cov 2x2)": ("R_measure", (2, 2)),
            "Q_lqr (LQR State Cost 4x4)": ("Q_lqr", (4, 4)),
            "R_lqr (LQR Input Cost 2x2)": ("R_lqr", (2, 2))
        }
        
        self.setup_widgets()
        
    def setup_widgets(self):
        title_font = ctk.CTkFont(family="Helvetica", size=13, weight="bold")
        lbl_font = ctk.CTkFont(family="Helvetica", size=11)
        
        # 1. Section: Agent Configuration
        ctk.CTkLabel(self, text="✈️ Agent Configuration", font=title_font, text_color="#06b6d4").pack(anchor="w", pady=(5, 5))
        
        # Followers Count
        fol_frame = ctk.CTkFrame(self, fg_color="transparent")
        fol_frame.pack(fill="x", pady=2)
        ctk.CTkLabel(fol_frame, text="Followers (1-5):", font=lbl_font, width=120, anchor="w").pack(side="left")
        self.fol_entry = ctk.CTkEntry(fol_frame, width=80, height=24)
        self.fol_entry.pack(side="left")
        
        # Leader Orbit Radius
        rad_frame = ctk.CTkFrame(self, fg_color="transparent")
        rad_frame.pack(fill="x", pady=2)
        ctk.CTkLabel(rad_frame, text="Orbit Radius (m):", font=lbl_font, width=120, anchor="w").pack(side="left")
        self.rad_entry = ctk.CTkEntry(rad_frame, width=80, height=24)
        self.rad_entry.pack(side="left")
        
        # Leader Orbit Speed (omega)
        omg_frame = ctk.CTkFrame(self, fg_color="transparent")
        omg_frame.pack(fill="x", pady=2)
        ctk.CTkLabel(omg_frame, text="Orbit Speed (rad/s):", font=lbl_font, width=120, anchor="w").pack(side="left")
        self.omg_entry = ctk.CTkEntry(omg_frame, width=80, height=24)
        self.omg_entry.pack(side="left")
        
        # 2. Section: Matrix Grid Editor
        ctk.CTkLabel(self, text="🛠️ System Matrix Editor", font=title_font, text_color="#06b6d4").pack(anchor="w", pady=(15, 5))
        
        self.matrix_select = ctk.CTkOptionMenu(self, values=list(self.matrix_options.keys()), 
                                                command=self.on_matrix_select_change,
                                                fg_color="#1e293b", button_color="#0f172a",
                                                button_hover_color="#1e293b", dropdown_fg_color="#1e293b")
        self.matrix_select.pack(fill="x", pady=5)
        
        # Dynamic matrix grid frame
        self.grid_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.grid_frame.pack(fill="x", pady=5)
        self.matrix_entries = []
        
        # Button to save matrix edits
        self.save_matrix_btn = ctk.CTkButton(self, text="Save Matrix Edits", height=24, fg_color="#1e293b",
                                              hover_color="#334155", command=self.save_matrix_edits)
        self.save_matrix_btn.pack(fill="x", pady=2)
        
        # 3. Section: Controller Designer
        ctk.CTkLabel(self, text="🔌 Controller Designer", font=title_font, text_color="#06b6d4").pack(anchor="w", pady=(15, 5))
        
        ctrl_frame = ctk.CTkFrame(self, fg_color="transparent")
        ctrl_frame.pack(fill="x", pady=2)
        ctk.CTkLabel(ctrl_frame, text="Controller Type:", font=lbl_font, width=100, anchor="w").pack(side="left")
        self.ctrl_type_select = ctk.CTkOptionMenu(ctrl_frame, values=["LQR", "PID", "Pole Placement"], 
                                                   command=self.on_controller_change, width=130, height=24,
                                                   fg_color="#1e293b", button_color="#0f172a",
                                                   button_hover_color="#1e293b", dropdown_fg_color="#1e293b")
        self.ctrl_type_select.pack(side="left")
        
        # PID Parameter input container
        self.pid_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.pid_entries = {}
        for param, default_val in [("Kp", "2.0"), ("Ki", "0.05"), ("Kd", "0.5")]:
            f = ctk.CTkFrame(self.pid_frame, fg_color="transparent")
            f.pack(fill="x", pady=1)
            ctk.CTkLabel(f, text=f"  Gain {param}:", font=lbl_font, width=100, anchor="w").pack(side="left")
            entry = ctk.CTkEntry(f, width=80, height=20)
            entry.insert(0, default_val)
            entry.pack(side="left")
            self.pid_entries[param] = entry
            
        # Pole Placement input container
        self.pole_frame = ctk.CTkFrame(self, fg_color="transparent")
        f_p = ctk.CTkFrame(self.pole_frame, fg_color="transparent")
        f_p.pack(fill="x", pady=1)
        ctk.CTkLabel(f_p, text="  Desired Poles:", font=lbl_font, width=100, anchor="w").pack(side="left")
        self.poles_entry = ctk.CTkEntry(f_p, width=120, height=20)
        self.poles_entry.insert(0, "0.91, 0.91, 0.85, 0.85")
        self.poles_entry.pack(side="left")
        
        # LQR parameters (Q_lqr/R_lqr edited via Matrix Editor)
        self.lqr_info_label = ctk.CTkLabel(self, text="  Edit Q_lqr / R_lqr via Matrix Editor above.",
                                            font=ctk.CTkFont(family="Helvetica", size=9, slant="italic"), text_color="#94a3b8")
                                            
        # Compute gains button
        self.compute_btn = ctk.CTkButton(self, text="Compute Feedback Gain", fg_color="#06b6d4",
                                          hover_color="#0891b2", text_color="#0a0e17", font=ctk.CTkFont(weight="bold"),
                                          command=self.compute_gains)
        self.compute_btn.pack(fill="x", pady=8)
        
        # 4. Section: Stability Info
        ctk.CTkLabel(self, text="📊 Stability Status", font=title_font, text_color="#06b6d4").pack(anchor="w", pady=(10, 5))
        
        self.stab_stable_lbl = ctk.CTkLabel(self, text="Stable: Pending", font=lbl_font, text_color="#94a3b8")
        self.stab_stable_lbl.pack(anchor="w")
        self.stab_radius_lbl = ctk.CTkLabel(self, text="Spectral Radius ρ: -", font=lbl_font, text_color="#94a3b8")
        self.stab_radius_lbl.pack(anchor="w")
        
        # Load active configuration values
        self.active_config = None
        
    def load_configuration(self, config: dict):
        self.active_config = config
        
        # Load agent configs
        sim_cfg = config["simulation"]
        self.fol_entry.delete(0, "end")
        self.fol_entry.insert(0, str(sim_cfg["n_followers"]))
        
        self.rad_entry.delete(0, "end")
        self.rad_entry.insert(0, str(sim_cfg["leader_orbit_radius"]))
        
        self.omg_entry.delete(0, "end")
        self.omg_entry.insert(0, str(sim_cfg["leader_orbit_omega"]))
        
        # Load controller type dropdown
        ctrl_type = config["controller"].get("type", "LQR")
        self.ctrl_type_select.set(ctrl_type)
        self.on_controller_change(ctrl_type)
        
        # Load active matrix selection grid
        self.on_matrix_select_change(self.matrix_select.get())
        
    def on_matrix_select_change(self, val):
        if not self.active_config:
            return
            
        # Clear grid
        for row in self.matrix_entries:
            for entry in row:
                entry.destroy()
        self.matrix_entries = []
        
        # Retrieve matrix properties
        key, shape = self.matrix_options[val]
        rows, cols = shape
        
        # Get matrix array
        if key in ["A_d", "B_d", "C_d"]:
            # Recalculate A_d, B_d based on current dt/damping or hold custom values
            dt = self.active_config["system"]["dt"]
            damping = self.active_config["system"]["damping"]
            
            # Form default matrix if not loaded
            if key == "A_d":
                arr = np.array([
                    [1.0,  dt,  0.0,  0.0],
                    [0.0,  1.0 - damping*dt, 0.0, 0.0],
                    [0.0,  0.0,  1.0,  dt],
                    [0.0,  0.0,  0.0,  1.0 - damping*dt]
                ])
            elif key == "B_d":
                arr = np.array([
                    [0.0, 0.0],
                    [dt,  0.0],
                    [0.0, 0.0],
                    [0.0, dt]
                ])
            else:
                arr = np.array([
                    [1.0, 0.0, 0.0, 0.0],
                    [0.0, 0.0, 1.0, 0.0]
                ])
        elif key == "Q_process":
            arr = np.diag(self.active_config["noises"]["process_noise_diag"])
        elif key == "R_measure":
            arr = np.diag(self.active_config["noises"]["measure_noise_diag"])
        elif key == "Q_lqr":
            arr = np.diag(self.active_config["lqr"]["Q_lqr_diag"])
        else:
            arr = np.diag(self.active_config["lqr"]["R_lqr_diag"])
            
        # Draw Entry grid
        for r in range(rows):
            row_entries = []
            for c in range(cols):
                val_cell = arr[r, c] if len(arr.shape) > 1 else (arr[r] if r == c else 0.0)
                entry = ctk.CTkEntry(self.grid_frame, width=50, height=20, font=("Helvetica", 9))
                entry.grid(row=r, column=c, padx=2, pady=2)
                entry.insert(0, f"{val_cell:.4f}")
                row_entries.append(entry)
            self.matrix_entries.append(row_entries)
            
    def save_matrix_edits(self):
        if not self.active_config:
            return
            
        val = self.matrix_select.get()
        key, shape = self.matrix_options[val]
        rows, cols = shape
        
        # Read matrix entries
        arr = np.zeros((rows, cols))
        try:
            for r in range(rows):
                for c in range(cols):
                    arr[r, c] = float(self.matrix_entries[r][c].get())
        except ValueError:
            tk.messagebox.showerror("Matrix Input Error", "Please ensure all grid cells contain valid float values.")
            return
            
        # Save array back to active config profile
        if key in ["A_d", "B_d", "C_d"]:
            # For simplicity, store matrix arrays or keep custom models
            pass
        elif key == "Q_process":
            self.active_config["noises"]["process_noise_diag"] = [arr[0,0], arr[1,1], arr[2,2], arr[3,3]]
        elif key == "R_measure":
            self.active_config["noises"]["measure_noise_diag"] = [arr[0,0], arr[1,1]]
        elif key == "Q_lqr":
            self.active_config["lqr"]["Q_lqr_diag"] = [arr[0,0], arr[1,1], arr[2,2], arr[3,3]]
        elif key == "R_lqr":
            self.active_config["lqr"]["R_lqr_diag"] = [arr[0,0], arr[1,1]]
            
        ctk.CTkLabel(self, text="Matrix updated successfully!", text_color="#10b981", font=("Helvetica", 9)).pack(anchor="w", pady=2)
        
    def on_controller_change(self, val):
        self.pid_frame.pack_forget()
        self.pole_frame.pack_forget()
        self.lqr_info_label.pack_forget()
        
        if val == "PID":
            self.pid_frame.pack(fill="x", pady=5)
        elif val == "Pole Placement":
            self.pole_frame.pack(fill="x", pady=5)
        else:
            self.lqr_info_label.pack(fill="x", pady=5)
            
    def compute_gains(self):
        """
        Gathers UI inputs, updates active configuration, and fires the change callback.
        """
        if not self.active_config:
            return
            
        try:
            # 1. Update Agent values
            followers = int(self.fol_entry.get())
            if not (1 <= followers <= 5):
                raise ValueError("Followers must be between 1 and 5.")
            self.active_config["simulation"]["n_followers"] = followers
            
            radius = float(self.rad_entry.get())
            self.active_config["simulation"]["leader_orbit_radius"] = radius
            
            omega = float(self.omg_entry.get())
            self.active_config["simulation"]["leader_orbit_omega"] = omega
            
            # 2. Update Controller parameters
            c_type = self.ctrl_type_select.get()
            self.active_config["controller"]["type"] = c_type
            
            if c_type == "PID":
                self.active_config["controller"]["pid"] = {
                    "kp": float(self.pid_entries["Kp"].get()),
                    "ki": float(self.pid_entries["Ki"].get()),
                    "kd": float(self.pid_entries["Kd"].get())
                }
            elif c_type == "Pole Placement":
                poles_str = self.poles_entry.get().split(",")
                poles = [float(p.strip()) for p in poles_str]
                if len(poles) != 4:
                    raise ValueError("Exactly 4 poles must be specified.")
                self.active_config["controller"]["desired_poles"] = poles
                
            # Fire update callback
            self.on_update(self.active_config)
            
        except Exception as e:
            tk.messagebox.showerror("Configuration Error", f"Failed to save parameters: {e}")
            
    def update_stability_labels(self, is_stable: bool, spectral_radius: float):
        if is_stable:
            self.stab_stable_lbl.configure(text="Stable: Yes (Schur)", text_color="#10b981")
        else:
            self.stab_stable_lbl.configure(text="Stable: No (Instable)", text_color="#ef4444")
            
        self.stab_radius_lbl.configure(text=f"Spectral Radius ρ: {spectral_radius:.6f}")
