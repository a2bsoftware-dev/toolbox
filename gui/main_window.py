import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
from gui.config_panel import ConfigPanel
from gui.attacks_defenses_panel import AttacksDefensesPanel
from gui.network_animator import NetworkAnimator
from gui.live_plots import LivePlotsPanel
from engine.simulator import NCSSimulator
from utils.project_manager import ProjectManager
from utils.report_generator import ReportGenerator

class MainWindow(ctk.CTk):
    """
    Main CustomTkinter window organizing layout, simulation loop, and file outputs.
    """
    def __init__(self, default_config: dict):
        super().__init__()
        
        self.config = default_config
        self.simulator = NCSSimulator(self.config)
        self.is_playing = False
        self.play_loop_id = None
        self.speed_multiplier = 1.0
        
        # Configure Window
        self.title("Secure Cloud Multi-Agent Control Toolbox (v10.0)")
        self.geometry("1400x900")
        self.configure(fg_color="#090d16") # Deep slate bg
        
        ctk.set_appearance_mode("dark")
        
        self.setup_layout()
        
        # Load simulator config into panels
        self.load_configuration_data(self.config)
        
    def setup_layout(self):
        # 1. Left Sidebar Frame (Configuration & File Controls)
        self.sidebar = ctk.CTkFrame(self, width=330, fg_color="#0f172a", border_width=1, border_color="rgba(255,255,255,0.05)")
        self.sidebar.pack(side="left", fill="y", padx=5, pady=5)
        
        # Sidebar Segmented Tabs selector
        self.sidebar_tabs = ctk.CTkTabview(self.sidebar, segmented_button_selected_color="#06b6d4",
                                            segmented_button_selected_hover_color="#0891b2")
        self.sidebar_tabs.pack(fill="both", expand=True, padx=5, pady=5)
        self.sidebar_tabs.add("Parameters")
        self.sidebar_tabs.add("Threat & Shield")
        
        # Instantiate Sidebar panels
        self.config_panel = ConfigPanel(self.sidebar_tabs.tab("Parameters"), on_update_callback=self.on_config_changed)
        self.config_panel.pack(fill="both", expand=True)
        
        self.cyber_panel = AttacksDefensesPanel(self.sidebar_tabs.tab("Threat & Shield"), on_update_callback=self.on_config_changed)
        self.cyber_panel.pack(fill="both", expand=True)
        
        # Bottom of Sidebar: Project File Buttons
        proj_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        proj_frame.pack(fill="x", pady=10, padx=10)
        
        title_font = ctk.CTkFont(family="Helvetica", size=10, weight="bold")
        ctk.CTkLabel(proj_frame, text="📁 Project Manager", font=title_font, text_color="#94a3b8").pack(anchor="w", pady=2)
        
        row1 = ctk.CTkFrame(proj_frame, fg_color="transparent")
        row1.pack(fill="x", pady=2)
        ctk.CTkButton(row1, text="Open Project", height=24, fg_color="#1e293b", hover_color="#334155", command=self.load_project_file).pack(side="left", fill="x", expand=True, padx=2)
        ctk.CTkButton(row1, text="Save Project", height=24, fg_color="#1e293b", hover_color="#334155", command=self.save_project_file).pack(side="left", fill="x", expand=True, padx=2)
        
        row2 = ctk.CTkFrame(proj_frame, fg_color="transparent")
        row2.pack(fill="x", pady=2)
        ctk.CTkButton(row2, text="Export PDF Report", height=24, fg_color="#059669", hover_color="#047857", text_color="#ffffff", command=self.export_pdf_report).pack(side="left", fill="x", expand=True, padx=2)
        ctk.CTkButton(row2, text="Export CSV Log", height=24, fg_color="#059669", hover_color="#047857", text_color="#ffffff", command=self.export_csv_data).pack(side="left", fill="x", expand=True, padx=2)
        
        # 2. Right Container Frame (Split into Top: Animation + Cloud Console, Bottom: Live Charts)
        self.right_container = ctk.CTkFrame(self, fg_color="transparent")
        self.right_container.pack(side="right", fill="both", expand=True, padx=5, pady=5)
        
        # Splitter Frame (Top Half: Animation, Playback, and Console)
        self.top_section = ctk.CTkFrame(self.right_container, fg_color="transparent")
        self.top_section.pack(side="top", fill="x", pady=(0, 5))
        
        # Topology Animation Box
        self.anim_panel = ctk.CTkFrame(self.top_section, height=270, fg_color="#0a0e17", border_width=1, border_color="rgba(255,255,255,0.05)")
        self.anim_panel.pack(side="left", fill="both", expand=True, padx=2)
        
        ctk.CTkLabel(self.anim_panel, text="🌐 Network Topology View", font=ctk.CTkFont(family="Helvetica", size=11, weight="bold"), text_color="#94a3b8").pack(anchor="w", padx=10, pady=5)
        self.net_animator = NetworkAnimator(self.anim_panel)
        self.net_animator.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Cloud Monitor Box
        self.cloud_panel = ctk.CTkFrame(self.top_section, width=320, height=270, fg_color="#0f172a", border_width=1, border_color="rgba(255,255,255,0.05)")
        self.cloud_panel.pack(side="right", fill="both", padx=2)
        
        ctk.CTkLabel(self.cloud_panel, text="☁️ Cloud Database Monitor", font=ctk.CTkFont(family="Helvetica", size=11, weight="bold"), text_color="#94a3b8").pack(anchor="w", padx=10, pady=5)
        self.setup_cloud_labels()
        
        # Playback Control Bar
        self.playback_panel = ctk.CTkFrame(self.right_container, fg_color="#0f172a", border_width=1, border_color="rgba(255,255,255,0.05)")
        self.playback_panel.pack(side="top", fill="x", pady=2)
        
        self.setup_playback_controls()
        
        # Charts view (Bottom Half)
        self.charts_panel = LivePlotsPanel(self.right_container, border_width=1, border_color="rgba(255,255,255,0.05)")
        self.charts_panel.pack(side="bottom", fill="both", expand=True, pady=(5, 0))
        
    def setup_cloud_labels(self):
        lbl_font = ctk.CTkFont(family="Helvetica", size=11)
        val_font = ctk.CTkFont(family="Courier", size=11, weight="bold")
        
        fields = [
            ("Encryption Shield", "lbl_enc", "None", "#f59e0b"),
            ("HMAC Signature check", "lbl_auth", "Disabled", "#ef4444"),
            ("Differential Privacy", "lbl_dp", "OFF", "#ef4444"),
            ("Packets Sent", "lbl_sent", "0", "#ffffff"),
            ("Packets Lost (DoS)", "lbl_lost", "0", "#ffffff"),
            ("Avg Telemetry Latency", "lbl_latency", "50 ms", "#ffffff"),
            ("Active Network State", "lbl_state", "Normal", "#10b981")
        ]
        
        self.cloud_widgets = {}
        for label, key, default, color in fields:
            row = ctk.CTkFrame(self.cloud_panel, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=2)
            
            ctk.CTkLabel(row, text=label, font=lbl_font, width=150, anchor="w").pack(side="left")
            widget = ctk.CTkLabel(row, text=default, font=val_font, text_color=color, width=120, anchor="e")
            widget.pack(side="right")
            self.cloud_widgets[key] = widget
            
    def setup_playback_controls(self):
        # Buttons
        self.play_btn = ctk.CTkButton(self.playback_panel, text="Play", width=80, fg_color="#06b6d4", text_color="#0a0e17", hover_color="#0891b2", font=ctk.CTkFont(weight="bold"), command=self.toggle_play)
        self.play_btn.pack(side="left", padx=5, pady=5)
        
        self.reset_btn = ctk.CTkButton(self.playback_panel, text="Reset", width=80, fg_color="#1e293b", hover_color="#334155", command=self.reset_simulation)
        self.reset_btn.pack(side="left", padx=5, pady=5)
        
        # Scrubber Time Label
        self.time_lbl = ctk.CTkLabel(self.playback_panel, text="0.00s", font=ctk.CTkFont(family="Courier", size=11))
        self.time_lbl.pack(side="left", padx=5)
        
        # Scrubber slider
        self.scrubber = ctk.CTkSlider(self.playback_panel, from_=0, to=900, number_of_steps=900, command=self.on_scrub)
        self.scrubber.set(0)
        self.scrubber.pack(side="left", fill="x", expand=True, padx=5)
        
        self.max_time_lbl = ctk.CTkLabel(self.playback_panel, text="45.0s", font=ctk.CTkFont(family="Courier", size=11))
        self.max_time_lbl.pack(side="left", padx=5)
        
        # Speed selector
        ctk.CTkLabel(self.playback_panel, text="Speed:").pack(side="left", padx=2)
        self.speed_select = ctk.CTkOptionMenu(self.playback_panel, values=["0.5x", "1.0x", "2.0x", "5.0x"], 
                                               width=80, command=self.on_speed_change,
                                               fg_color="#1e293b", button_color="#0f172a",
                                               button_hover_color="#1e293b", dropdown_fg_color="#1e293b")
        self.speed_select.set("1.0x")
        self.speed_select.pack(side="left", padx=5)
        
    def load_configuration_data(self, config: dict):
        self.config = config
        self.simulator = NCSSimulator(self.config)
        self.net_animator.set_n_followers(self.config["simulation"]["n_followers"])
        
        self.config_panel.load_configuration(self.config)
        self.cyber_panel.load_configuration(self.config)
        
        self.scrubber.configure(to=int(self.config["system"]["t_max"] / self.config["system"]["dt"]))
        self.scrubber.set(0)
        
        # Update Stability parameters
        is_stable, eigvals, radius = self.simulator.controller.verify_stability()
        self.config_panel.update_stability_labels(is_stable, radius)
        
        # Redraw plots
        self.charts_panel.update_active_plot(self.simulator.history, self.config, eigvals)
        self.update_playback_labels()
        
    def on_config_changed(self, new_config: dict):
        """
        Callback fired when user clicks 'Save edits' in Config or Cyber panels.
        """
        self.reset_simulation()
        self.load_configuration_data(new_config)
        
    def toggle_play(self):
        if self.is_playing:
            self.is_playing = False
            self.play_btn.configure(text="Play")
            if self.play_loop_id:
                self.after_cancel(self.play_loop_id)
                self.play_loop_id = None
        else:
            self.is_playing = True
            self.play_btn.configure(text="Pause")
            self.simulation_loop()
            
    def simulation_loop(self):
        if not self.is_playing:
            return
            
        steps_limit = int(self.config["system"]["t_max"] / self.config["system"]["dt"])
        if self.simulator.current_step_idx >= steps_limit:
            self.toggle_play() # Pause on reaching limit
            return
            
        # Execute simulator step
        frame_data = self.simulator.step()
        
        # Update UI components
        self.scrubber.set(self.simulator.current_step_idx)
        self.time_lbl.configure(text=f"{frame_data['time']:.2f}s")
        
        # Update live charts
        is_stable, eigvals, radius = self.simulator.controller.verify_stability()
        self.charts_panel.update_active_plot(self.simulator.history, self.config, eigvals)
        
        # Update Canvas Animator
        self.net_animator.draw(frame_data["network_status"])
        
        # Update Cloud Database Console
        self.update_cloud_monitor_labels(frame_data["network_status"])
        
        # Periodic looping based on speed selection
        interval_ms = int((self.config["system"]["dt"] * 1000) / self.speed_multiplier)
        self.play_loop_id = self.after(interval_ms, self.simulation_loop)
        
    def update_cloud_monitor_labels(self, status: str):
        sec_cfg = self.config["security"]
        
        # HMAC
        if sec_cfg.get("enable_hmac", True):
            self.cloud_widgets["lbl_enc"].configure(text="HMAC-SHA256", text_color="#06b6d4")
            self.cloud_widgets["lbl_auth"].configure(text="VERIFIED", text_color="#10b981")
        else:
            self.cloud_widgets["lbl_enc"].configure(text="None", text_color="#f59e0b")
            self.cloud_widgets["lbl_auth"].configure(text="INACTIVE", text_color="#ef4444")
            
        # DP
        if sec_cfg.get("enable_dp", True):
            self.cloud_widgets["lbl_dp"].configure(text=f"ON (e={sec_cfg.get('dp_epsilon', 1.5)})", text_color="#10b981")
        else:
            self.cloud_widgets["lbl_dp"].configure(text="OFF", text_color="#ef4444")
            
        # Packet stats
        self.cloud_widgets["lbl_sent"].configure(text=str(self.simulator.packets_sent))
        self.cloud_widgets["lbl_lost"].configure(text=str(self.simulator.packets_lost))
        
        # Latency / Status
        if status == "dos":
            self.cloud_widgets["lbl_latency"].configure(text="inf (Severed)", text_color="#ef4444")
            self.cloud_widgets["lbl_state"].configure(text="DoS ACTIVE", text_color="#ef4444")
        elif status == "attacked":
            self.cloud_widgets["lbl_latency"].configure(text="50 ms", text_color="#ffffff")
            self.cloud_widgets["lbl_state"].configure(text="FDI ACTIVE", text_color="#f59e0b")
        elif status == "secured":
            self.cloud_widgets["lbl_latency"].configure(text="50 ms", text_color="#ffffff")
            self.cloud_widgets["lbl_state"].configure(text="SHIELDED [OK]", text_color="#06b6d4")
        elif status in ["delayed", "replayed"]:
            self.cloud_widgets["lbl_latency"].configure(text="Delayed", text_color="#8b5cf6")
            self.cloud_widgets["lbl_state"].configure(text=status.upper(), text_color="#8b5cf6")
        else:
            self.cloud_widgets["lbl_latency"].configure(text="50 ms", text_color="#ffffff")
            self.cloud_widgets["lbl_state"].configure(text="NORMAL", text_color="#10b981")
            
    def update_playback_labels(self):
        t_max = self.config["system"]["t_max"]
        self.max_time_lbl.configure(text=f"{t_max:.1f}s")
        self.time_lbl.configure(text=f"{self.simulator.t:.2f}s")
        
    def reset_simulation(self):
        if self.is_playing:
            self.toggle_play()
        self.simulator = NCSSimulator(self.config)
        self.scrubber.set(0)
        self.update_playback_labels()
        
        # Reset canvas
        self.net_animator.set_n_followers(self.config["simulation"]["n_followers"])
        self.net_animator.draw("normal")
        
        # Reset labels
        self.cloud_widgets["lbl_sent"].configure(text="0")
        self.cloud_widgets["lbl_lost"].configure(text="0")
        self.cloud_widgets["lbl_latency"].configure(text="50 ms", text_color="#ffffff")
        self.cloud_widgets["lbl_state"].configure(text="NORMAL", text_color="#10b981")
        
        # Redraw charts
        is_stable, eigvals, radius = self.simulator.controller.verify_stability()
        self.charts_panel.update_active_plot(self.simulator.history, self.config, eigvals)
        
    def on_scrub(self, val):
        # Frame scrubbing allows the user to see charts at any historical timestamp
        idx = int(val)
        if idx < len(self.simulator.history["time"]):
            t_curr = self.simulator.history["time"][idx]
            self.time_lbl.configure(text=f"{t_curr:.2f}s")
            
            # Repopulate canvas & charts cursors at scrubbed time index
            # (In a real-time playback system, scrubbing moves the pointer index)
            pass
            
    def on_speed_change(self, val):
        multiplier_str = val.replace("x", "")
        self.speed_multiplier = float(multiplier_str)
        if self.is_playing:
            # Refresh looping frequency
            self.toggle_play()
            self.toggle_play()
            
    # --- Project file manager controls ---
    def load_project_file(self):
        path = filedialog.askopenfilename(filetypes=[("NCS Toolbox Project", "*.toolbox")])
        if not path:
            return
        config = ProjectManager.load_project(path)
        if config:
            self.load_configuration_data(config)
            messagebox.showinfo("Project Loaded", "Simulation parameters loaded successfully.")
        else:
            messagebox.showerror("Format Error", "Selected file is not a valid .toolbox configuration database.")
            
    def save_project_file(self):
        path = filedialog.asksaveasfilename(filetypes=[("NCS Toolbox Project", "*.toolbox")], defaultextension=".toolbox")
        if not path:
            return
        success = ProjectManager.save_project(path, self.config)
        if success:
            messagebox.showinfo("Project Saved", "Configuration saved successfully.")
        else:
            messagebox.showerror("Write Error", "Failed to save configuration profile.")
            
    def export_pdf_report(self):
        if not self.simulator.history["time"]:
            messagebox.showwarning("Simulation Required", "Please run the simulation before compiling reports.")
            return
        path = filedialog.asksaveasfilename(filetypes=[("PDF Document", "*.pdf")], defaultextension=".pdf")
        if not path:
            return
        ReportGenerator.generate_pdf_report(path, self.config, self.simulator.history)
        messagebox.showinfo("Report Exported", f"Thesis PDF analysis generated successfully at: {path}")
        
    def export_csv_data(self):
        if not self.simulator.history["time"]:
            messagebox.showwarning("Simulation Required", "Please run the simulation before exporting data.")
            return
        path = filedialog.asksaveasfilename(filetypes=[("CSV Worksheet", "*.csv"), ("Excel Sheet", "*.xlsx")], defaultextension=".csv")
        if not path:
            return
            
        if path.endswith(".xlsx"):
            ReportGenerator.export_excel(path, self.simulator.history)
            messagebox.showinfo("Data Exported", f"Excel sheet generated successfully at: {path}")
        else:
            ReportGenerator.export_csv(path, self.simulator.history)
            messagebox.showinfo("Data Exported", f"CSV spreadsheet generated successfully at: {path}")
