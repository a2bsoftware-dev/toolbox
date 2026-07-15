import customtkinter as ctk
import numpy as np
from tkinter import messagebox
from gui.matrix_editor import MatrixEditor
from engine.controllers import LQRController, PolePlacementController
from engine.model import continuous_matrices, euler_discrete_matrices

class ControllerPanel(ctk.CTkFrame):
    """
    Controller design panel (Phase 5) allowing matrix edits,
    LQR/PID/PP gains solving, and closed-loop stability verification.
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
        
        # 1. Domain & Type Selection
        ctk.CTkLabel(self, text="⚡ System Modeling Domain", font=title_font, text_color="#06b6d4").pack(anchor="w", pady=(5, 2))
        
        dom_frame = ctk.CTkFrame(self, fg_color="transparent")
        dom_frame.pack(fill="x", pady=2)
        ctk.CTkLabel(dom_frame, text="Domain Select:", font=lbl_font, width=110, anchor="w").pack(side="left")
        self.domain_select = ctk.CTkOptionMenu(dom_frame, values=["Continuous", "Discrete"], 
                                               fg_color="#1e293b", button_color="#0f172a",
                                               button_hover_color="#1e293b", dropdown_fg_color="#1e293b",
                                               height=22, command=self.on_domain_changed)
        self.domain_select.pack(side="left", fill="x", expand=True)
        
        ctk.CTkLabel(self, text="🔌 Controller Design Type", font=title_font, text_color="#06b6d4").pack(anchor="w", pady=(10, 2))
        
        type_frame = ctk.CTkFrame(self, fg_color="transparent")
        type_frame.pack(fill="x", pady=2)
        ctk.CTkLabel(type_frame, text="Design Scheme:", font=lbl_font, width=110, anchor="w").pack(side="left")
        self.ctrl_type_select = ctk.CTkOptionMenu(type_frame, values=["LQR", "PID", "Pole Placement"], 
                                                   fg_color="#1e293b", button_color="#0f172a",
                                                   button_hover_color="#1e293b", dropdown_fg_color="#1e293b",
                                                   height=22, command=self.on_scheme_changed)
        self.ctrl_type_select.pack(side="left", fill="x", expand=True)
        
        # 2. Reusable Matrix Editor Widget
        self.matrix_sel_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.matrix_sel_frame.pack(fill="x", pady=(10, 2))
        
        ctk.CTkLabel(self.matrix_sel_frame, text="Matrix to Edit:", font=lbl_font, width=110, anchor="w").pack(side="left")
        self.matrix_selector = ctk.CTkOptionMenu(self.matrix_sel_frame, values=["A", "B", "Q_lqr", "R_lqr"],
                                                  fg_color="#1e293b", button_color="#0f172a",
                                                  button_hover_color="#1e293b", dropdown_fg_color="#1e293b",
                                                  height=22, command=self.on_matrix_type_changed)
        self.matrix_selector.pack(side="left", fill="x", expand=True)
        
        # Instantiate Matrix Editor
        self.matrix_editor = MatrixEditor(self, label="Matrix Coefficients Editor")
        self.matrix_editor.pack(fill="x", pady=5)
        
        # 3. PID and Pole parameters frames
        self.pid_params_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.pid_entries = {}
        for kp_ki_kd in ["Kp", "Ki", "Kd"]:
            row = ctk.CTkFrame(self.pid_params_frame, fg_color="transparent")
            row.pack(fill="x", pady=1)
            ctk.CTkLabel(row, text=f"Gain {kp_ki_kd}:", font=lbl_font, width=110, anchor="w").pack(side="left")
            entry = ctk.CTkEntry(row, width=80, height=20, fg_color="#1e293b", text_color="#ffffff")
            entry.pack(side="left")
            self.pid_entries[kp_ki_kd] = entry
            
        self.pp_params_frame = ctk.CTkFrame(self, fg_color="transparent")
        row = ctk.CTkFrame(self.pp_params_frame, fg_color="transparent")
        row.pack(fill="x", pady=1)
        ctk.CTkLabel(row, text="Desired Poles:", font=lbl_font, width=110, anchor="w").pack(side="left")
        self.poles_entry = ctk.CTkEntry(row, width=130, height=20, fg_color="#1e293b", text_color="#ffffff")
        self.poles_entry.pack(side="left")
        
        # 4. Solvers trigger button
        self.solve_btn = ctk.CTkButton(self, text="Compute Feedback Gain K", fg_color="#06b6d4",
                                        hover_color="#0891b2", text_color="#0a0e17", font=ctk.CTkFont(weight="bold"),
                                        command=self.on_compute_clicked)
        self.solve_btn.pack(fill="x", pady=10)
        
        # 5. Designer Output Box
        ctk.CTkLabel(self, text="📊 Stability Verification", font=title_font, text_color="#06b6d4").pack(anchor="w", pady=(10, 2))
        
        self.out_box = ctk.CTkFrame(self, fg_color="#0f172a", border_width=1, border_color="#1e293b")
        self.out_box.pack(fill="both", expand=True, pady=2, padx=2)
        
        self.lbl_stable = ctk.CTkLabel(self.out_box, text="Stable: -", font=lbl_font, text_color="#94a3b8")
        self.lbl_stable.pack(anchor="w", padx=10, pady=2)
        
        self.lbl_poles = ctk.CTkLabel(self.out_box, text="Eigenvalues (poles):\n-", font=lbl_font, text_color="#94a3b8", justify="left")
        self.lbl_poles.pack(anchor="w", padx=10, pady=2)
        
        self.lbl_gain = ctk.CTkLabel(self.out_box, text="Gain Matrix K:\n-", font=lbl_font, text_color="#94a3b8", justify="left")
        self.lbl_gain.pack(anchor="w", padx=10, pady=(2, 10))
        
    def load_configuration(self, config: dict):
        self.config = config
        
        # Load modeling domain
        dom = config["system"].get("model_domain", "continuous").capitalize()
        self.domain_select.set(dom)
        
        # Load controller scheme
        scheme = config["controller"].get("type", "LQR")
        if scheme == "POLE_PLACEMENT":
            scheme = "Pole Placement"
        self.ctrl_type_select.set(scheme)
        
        # Set visibility
        self.on_scheme_changed(scheme)
        
        # Load matrix editor with A by default
        self.on_matrix_type_changed("A")
        
        # Load PID inputs
        pid_cfg = config["controller"].get("pid", {"kp": 2.0, "ki": 0.05, "kd": 0.5})
        self.pid_entries["Kp"].delete(0, "end")
        self.pid_entries["Kp"].insert(0, str(pid_cfg.get("kp", 2.0)))
        self.pid_entries["Ki"].delete(0, "end")
        self.pid_entries["Ki"].insert(0, str(pid_cfg.get("ki", 0.05)))
        self.pid_entries["Kd"].delete(0, "end")
        self.pid_entries["Kd"].insert(0, str(pid_cfg.get("kd", 0.5)))
        
        # Load PP poles
        poles = config["controller"].get("desired_poles", [0.91, 0.91, 0.85, 0.85])
        self.poles_entry.delete(0, "end")
        self.poles_entry.insert(0, ", ".join(map(str, poles)))
        
        # Update output logs
        self.update_stability_logs()
        
    def on_domain_changed(self, val: str):
        self.config["system"]["model_domain"] = val.lower()
        self.on_matrix_type_changed(self.matrix_selector.get())
        
    def on_scheme_changed(self, val: str):
        self.pid_params_frame.pack_forget()
        self.pp_params_frame.pack_forget()
        
        if val == "PID":
            self.pid_params_frame.pack(fill="x", pady=5)
            self.matrix_sel_frame.pack_forget()
            self.matrix_editor.pack_forget()
        elif val == "Pole Placement":
            self.pp_params_frame.pack(fill="x", pady=5)
            self.matrix_sel_frame.pack(fill="x", pady=(10, 2))
            self.matrix_editor.pack(fill="x", pady=5)
        else:
            self.matrix_sel_frame.pack(fill="x", pady=(10, 2))
            self.matrix_editor.pack(fill="x", pady=5)
            
    def on_matrix_type_changed(self, val: str):
        dom = self.domain_select.get().lower()
        
        # Form basic continuous matrices
        damping = self.config["system"]["damping"]
        
        # We fetch continuous or discrete matrix configurations based on domain selection
        if val in ("A", "B"):
            if dom == "continuous":
                A, B, _ = continuous_matrices(damping)
            else:
                dt = self.config["system"]["dt"]
                A, B = euler_discrete_matrices(damping, dt)
            arr = A if val == "A" else B
        elif val == "Q_lqr":
            arr = np.diag(self.config["lqr"]["Q_lqr_diag"])
        else:
            arr = np.diag(self.config["lqr"]["R_lqr_diag"])
            
        self.matrix_editor.set_matrix(arr)
        
    def on_compute_clicked(self):
        try:
            # 1. Read matrix edits
            val = self.matrix_selector.get()
            arr = self.matrix_editor.get_matrix()
            
            # Save matrix diagonal parameters back to config
            if val == "Q_lqr":
                self.config["lqr"]["Q_lqr_diag"] = np.diag(arr).tolist()
            elif val == "R_lqr":
                self.config["lqr"]["R_lqr_diag"] = np.diag(arr).tolist()
            
            # 2. Read designer parameters
            scheme = self.ctrl_type_select.get()
            if scheme == "PID":
                self.config["controller"]["type"] = "PID"
                self.config["controller"]["pid"] = {
                    "kp": float(self.pid_entries["Kp"].get()),
                    "ki": float(self.pid_entries["Ki"].get()),
                    "kd": float(self.pid_entries["Kd"].get())
                }
            elif scheme == "Pole Placement":
                self.config["controller"]["type"] = "POLE_PLACEMENT"
                poles_str = self.poles_entry.get().split(",")
                poles = [float(p.strip()) for p in poles_str]
                if len(poles) != 4:
                    raise ValueError("Exactly 4 poles must be specified.")
                self.config["controller"]["desired_poles"] = poles
            else:
                self.config["controller"]["type"] = "LQR"
                
            # Fire update notification callback
            self.on_update(self.config)
            
            # Refresh Output Logs
            self.update_stability_logs()
            
        except Exception as e:
            messagebox.showerror("Solver Error", f"Failed to compute controller feedback gains: {e}")
            
    def update_stability_logs(self):
        # Dynamically instantiate a temporary LQRController to compute gain and verify stability
        try:
            dom = self.config["system"].get("model_domain", "continuous").lower()
            damping = self.config["system"]["damping"]
            
            if dom == "continuous":
                A, B, _ = continuous_matrices(damping)
            else:
                dt = self.config["system"]["dt"]
                A, B = euler_discrete_matrices(damping, dt)

            Q = np.diag(self.config["lqr"]["Q_lqr_diag"])
            R = np.diag(self.config["lqr"]["R_lqr_diag"])
            
            # Solve
            temp_ctrl = LQRController(A, B, Q, R, domain=dom)
            is_stable, eigvals, idx = temp_ctrl.verify_stability()
            
            # Display Stability status
            if is_stable:
                self.lbl_stable.configure(text="Stable: Stable ✔", text_color="#10b981")
            else:
                self.lbl_stable.configure(text="Stable: UNSTABLE ❌", text_color="#ef4444")
                
            # Display Poles
            poles_text = "Eigenvalues (poles):\n" + "\n".join([f"  {p.real:.4f} + {p.imag:.4f}j" for p in eigvals])
            self.lbl_poles.configure(text=poles_text)
            
            # Display Feedback Gain
            gain_text = "Gain Matrix K:\n"
            for row in temp_ctrl.K_fb:
                gain_text += "  [ " + " ".join([f"{cell:.3f}" for cell in row]) + " ]\n"
            self.lbl_gain.configure(text=gain_text)
            
        except Exception as e:
            self.lbl_stable.configure(text="Stable: Design Failed", text_color="#ef4444")
            self.lbl_poles.configure(text="Eigenvalues (poles):\nFailed")
            self.lbl_gain.configure(text="Gain Matrix K:\nFailed")
