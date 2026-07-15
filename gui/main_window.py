import customtkinter as ctk
from tkinter import filedialog, messagebox
import logging

from gui.sidebar import Sidebar
from gui.dashboard import Dashboard
from gui.live_plots import LivePlotsPanel
from engine.simulator import NCSSimulator
from utils.project_manager import ProjectManager
from utils.report_generator import ReportGenerator
from utils.config import normalize_simulation_duration

class MainWindow(ctk.CTk):
    """
    Main Window container (Phase 2). Arranges Sidebar and Dashboard components.
    Operates simulation timesteps and clocks.
    """
    def __init__(self, default_config: dict):
        super().__init__()
        
        self.config = default_config
        self.simulator = NCSSimulator(self.config)
        self.is_playing = False
        self.play_loop_id = None
        
        # Window attributes
        self.title("Secure Cloud Multi-Agent Control Toolbox (v10.0)")
        self.geometry("1300x850")
        self.configure(fg_color="#090d16")
        
        ctk.set_appearance_mode("dark")
        self.setup_layout()
        self.load_configuration(self.config)
        
    def setup_layout(self):
        # 1. Sidebar Container (Left Column)
        self.sidebar = Sidebar(
            self,
            on_play_callback=self.toggle_play,
            on_reset_callback=self.reset_simulation,
            on_tab_change_callback=self.on_tab_changed,
            on_load_callback=self.load_project_file,
            on_save_callback=self.save_project_file,
            on_pdf_callback=self.export_pdf_report,
            on_csv_callback=self.export_csv_data
        )
        self.sidebar.pack(side="left", fill="y", padx=5, pady=5)
        
        # Instantiate sidebar subpanels inside sidebar's content_frame
        from gui.controller_panel import ControllerPanel
        from gui.attacks_panel import AttacksPanel
        
        self.controller_panel = ControllerPanel(self.sidebar.content_frame, self.config, on_update_callback=self.on_config_changed)
        self.attacks_panel = AttacksPanel(self.sidebar.content_frame, self.config, on_update_callback=self.on_config_changed)
        
        # Pack ControllerPanel by default
        self.controller_panel.pack(fill="both", expand=True)
        
        # 2. Right Pane Frame (Dashboard on top, Plots on bottom)
        self.right_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.right_frame.pack(side="right", fill="both", expand=True, padx=5, pady=5)
        
        # Dashboard Panel (Top half)
        self.dashboard = Dashboard(self.right_frame)
        self.dashboard.pack(side="top", fill="x", pady=2)
        
        # Embed Live Matplotlib Charts Panel (Phase 3)
        self.charts_panel = LivePlotsPanel(self.right_frame, on_export_pdf_callback=self.export_pdf_report,
                                            border_width=1, border_color="#1e293b")
        self.charts_panel.pack(side="bottom", fill="both", expand=True, pady=2)
        
    def load_configuration(self, config: dict):
        # Extend t_max (if needed) so the run reaches every enabled attack's window before
        # stopping - otherwise the scrubber/step-limit below would be computed from a t_max
        # too short to ever reach a later-starting attack (e.g. Delay/Replay at 50-70s).
        normalize_simulation_duration(config)
        self.config = config
        self.simulator = NCSSimulator(self.config)

        # Reset Scrubber parameters
        steps_limit = int(self.config["system"]["t_max"] / self.config["system"]["dt"])
        self.dashboard.scrubber.configure(to=steps_limit)
        self.dashboard.scrubber.set(0)
        
        self.update_playback_labels()
        
        # Sync config to subpanels
        if hasattr(self, 'controller_panel'):
            self.controller_panel.load_configuration(config)
        if hasattr(self, 'attacks_panel'):
            self.attacks_panel.load_configuration(config)
        
        # Set followers count in animator and draw initial topology
        self.dashboard.net_animator.set_n_followers(self.config["simulation"]["n_followers"])
        self.dashboard.net_animator.draw("normal")
        
        # Draw initial plots
        is_stable, eigvals, radius = self.simulator.controller.verify_stability()
        self.charts_panel.update_active_plot(self.simulator.history, self.config, eigvals)

        # Fresh simulator has no history yet - nothing to export until a run completes or pauses
        self.set_export_enabled(False)

    def set_export_enabled(self, enabled: bool):
        """
        The PDF report reflects a specific run's data, so exporting mid-play would capture a
        moving target; the button is disabled while playing and only re-enabled once the run
        is paused, completes on its own, or is reset.
        """
        state = "normal" if enabled else "disabled"
        if hasattr(self.sidebar, 'pdf_btn'):
            self.sidebar.pdf_btn.configure(state=state)
        if hasattr(self.charts_panel, 'export_btn'):
            self.charts_panel.export_btn.configure(state=state)

    def toggle_play(self):
        if self.is_playing:
            self.is_playing = False
            self.sidebar.set_playing_state(False)
            if self.play_loop_id:
                self.after_cancel(self.play_loop_id)
                self.play_loop_id = None
            self.set_export_enabled(True)
        else:
            self.is_playing = True
            self.sidebar.set_playing_state(True)
            self.set_export_enabled(False)
            self.simulation_loop()
            
    def simulation_loop(self):
        if not self.is_playing:
            return
            
        steps_limit = int(self.config["system"]["t_max"] / self.config["system"]["dt"])
        if self.simulator.current_step_idx >= steps_limit:
            self.toggle_play()
            return
            
        # Stepping logic
        frame_data = self.simulator.step()
        
        # Update scrubber / clocks
        self.dashboard.scrubber.set(self.simulator.current_step_idx)
        self.dashboard.time_lbl.configure(text=f"{frame_data['time']:.2f}s")
        
        # Update Canvas Animator
        self.dashboard.net_animator.draw(frame_data["network_status"])
        
        # Update Cyber Dashboard Stats (Phase 7)
        self.dashboard.update_cloud_metrics(self.simulator, frame_data["network_status"])
        
        # Update live plots
        is_stable, eigvals, radius = self.simulator.controller.verify_stability()
        self.charts_panel.update_active_plot(self.simulator.history, self.config, eigvals)
        
        interval_ms = int(self.config["system"]["dt"] * 1000)
        self.play_loop_id = self.after(interval_ms, self.simulation_loop)
        
    def reset_simulation(self):
        if self.is_playing:
            self.toggle_play()
        self.simulator = NCSSimulator(self.config)
        self.dashboard.scrubber.set(0)
        self.update_playback_labels()
        
        # Reset canvas animator
        self.dashboard.net_animator.set_n_followers(self.config["simulation"]["n_followers"])
        self.dashboard.net_animator.draw("normal")
        
        # Reset Cyber Dashboard Stats (Phase 7)
        self.dashboard.update_cloud_metrics(self.simulator, "normal")
        
        # Redraw reset plots
        is_stable, eigvals, radius = self.simulator.controller.verify_stability()
        self.charts_panel.update_active_plot(self.simulator.history, self.config, eigvals)

        # The reset simulator has no history yet - nothing to export until it runs again
        self.set_export_enabled(False)

    def update_playback_labels(self):
        t_max = self.config["system"]["t_max"]
        self.dashboard.max_time_lbl.configure(text=f"{t_max:.1f}s")
        self.dashboard.time_lbl.configure(text=f"{self.simulator.t:.2f}s")
        
    def on_config_changed(self, new_config: dict):
        self.config = new_config
        self.reset_simulation()
        self.load_configuration(new_config)
        
    def on_tab_changed(self, tab_name: str):
        if tab_name == "Model":
            self.attacks_panel.pack_forget()
            self.controller_panel.pack(fill="both", expand=True)
        else:
            self.controller_panel.pack_forget()
            self.attacks_panel.pack(fill="both", expand=True)
        
    def load_project_file(self):
        path = filedialog.askopenfilename(filetypes=[("NCS Toolbox Project", "*.toolbox")])
        if not path:
            return
        config = ProjectManager.load_project(path)
        if config:
            self.load_configuration(config)
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
        ReportGenerator.generate_pdf_report(path, self.config, self.simulator.history, self.simulator.controller)
        messagebox.showinfo("Report Exported", f"Thesis PDF analysis generated successfully at:\n{path}")
        
    def export_csv_data(self):
        if not self.simulator.history["time"]:
            messagebox.showwarning("Simulation Required", "Please run the simulation before exporting data.")
            return
        path = filedialog.asksaveasfilename(filetypes=[("CSV Worksheet", "*.csv"), ("Excel Sheet", "*.xlsx")], defaultextension=".csv")
        if not path:
            return
            
        if path.endswith(".xlsx"):
            ReportGenerator.export_excel(path, self.simulator.history)
            messagebox.showinfo("Data Exported", f"Excel sheet generated successfully at:\n{path}")
        else:
            ReportGenerator.export_csv(path, self.simulator.history)
            messagebox.showinfo("Data Exported", f"CSV spreadsheet generated successfully at:\n{path}")
