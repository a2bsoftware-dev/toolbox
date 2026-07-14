import customtkinter as ctk
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import numpy as np

class LivePlotsPanel(ctk.CTkFrame):
    """
    Houses multiple real-time plotting canvases inside CTkTabview tabs.
    Updates only the active tab for peak rendering performance.
    """
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        # Create Tab View
        self.tabview = ctk.CTkTabview(self, segmented_button_selected_color="#06b6d4",
                                      segmented_button_selected_hover_color="#0891b2",
                                      text_color="#f3f4f6")
        self.tabview.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.tabs = ["Trajectories", "Consensus Error", "Control Effort", "Observer Error", "Lyapunov Decays", "Pole s-Plane"]
        for tab in self.tabs:
            self.tabview.add(tab)
            
        # Matplotlib styling for Dark Theme
        plt.style.use('dark_background')
        self.plt_color_bg = "#0a0e17"
        self.plt_color_grid = (1.0, 1.0, 1.0, 0.05)
        
        # Init plots dictionary
        self.canvases = {}
        self.figures = {}
        self.axes = {}
        
        self.setup_plots()
        
    def setup_plots(self):
        # 1. Trajectories Tab
        fig, ax = plt.subplots(figsize=(5, 4), facecolor=self.plt_color_bg)
        ax.set_facecolor(self.plt_color_bg)
        ax.set_title("2D Spatial Trajectories", fontsize=10, weight="bold")
        ax.set_xlabel("X Position (m)", fontsize=8)
        ax.set_ylabel("Y Position (m)", fontsize=8)
        ax.grid(True, color="gray", alpha=0.2)
        fig.tight_layout()
        self.store_plot("Trajectories", fig, ax)
        
        # 2. Consensus Error Tab
        fig, ax = plt.subplots(figsize=(5, 4), facecolor=self.plt_color_bg)
        ax.set_facecolor(self.plt_color_bg)
        ax.set_title("Consensus Tracking Error", fontsize=10, weight="bold")
        ax.set_xlabel("Time (s)", fontsize=8)
        ax.set_ylabel("Error (m)", fontsize=8)
        ax.grid(True, color="gray", alpha=0.2)
        fig.tight_layout()
        self.store_plot("Consensus Error", fig, ax)
        
        # 3. Control Effort Tab
        fig, ax = plt.subplots(figsize=(5, 4), facecolor=self.plt_color_bg)
        ax.set_facecolor(self.plt_color_bg)
        ax.set_title("Control Input Command Magnitude ||u(t)||", fontsize=10, weight="bold")
        ax.set_xlabel("Time (s)", fontsize=8)
        ax.set_ylabel("Acceleration (m/s^2)", fontsize=8)
        ax.grid(True, color="gray", alpha=0.2)
        fig.tight_layout()
        self.store_plot("Control Effort", fig, ax)
        
        # 4. Observer Error Tab
        fig, ax = plt.subplots(figsize=(5, 4), facecolor=self.plt_color_bg)
        ax.set_facecolor(self.plt_color_bg)
        ax.set_title("Kalman Filter Estimation Error", fontsize=10, weight="bold")
        ax.set_xlabel("Time (s)", fontsize=8)
        ax.set_ylabel("Error Norm", fontsize=8)
        ax.grid(True, color="gray", alpha=0.2)
        fig.tight_layout()
        self.store_plot("Observer Error", fig, ax)
        
        # 5. Lyapunov Decays Tab
        fig, ax = plt.subplots(figsize=(5, 4), facecolor=self.plt_color_bg)
        ax.set_facecolor(self.plt_color_bg)
        ax.set_title("System Lyapunov Stability Decay V(t)", fontsize=10, weight="bold")
        ax.set_xlabel("Time (s)", fontsize=8)
        ax.set_ylabel("Energy Value", fontsize=8)
        ax.grid(True, color="gray", alpha=0.2)
        fig.tight_layout()
        self.store_plot("Lyapunov Decays", fig, ax)
        
        # 6. Pole s-Plane Tab
        fig, ax = plt.subplots(figsize=(5, 4), facecolor=self.plt_color_bg)
        ax.set_facecolor(self.plt_color_bg)
        ax.set_title("Continuous Closed-Loop Poles (s-plane)", fontsize=10, weight="bold")
        ax.set_xlabel("Real Part (σ)", fontsize=8)
        ax.set_ylabel("Imaginary Part (jω)", fontsize=8)
        fig.tight_layout()
        self.store_plot("Pole s-Plane", fig, ax)
        
    def store_plot(self, tab_name: str, fig, ax):
        tab_frame = self.tabview.tab(tab_name)
        canvas = FigureCanvasTkAgg(fig, master=tab_frame)
        canvas.get_tk_widget().pack(fill="both", expand=True)
        
        self.figures[tab_name] = fig
        self.axes[tab_name] = ax
        self.canvases[tab_name] = canvas
        
    def update_active_plot(self, history: dict, config: dict, eigenvalues=None):
        """
        Redraws ONLY the currently selected tab's canvas to conserve CPU cycles.
        """
        active_tab = self.tabview.get()
        if not history["time"] and active_tab != "Pole s-Plane":
            return
            
        ax = self.axes[active_tab]
        fig = self.figures[active_tab]
        canvas = self.canvases[active_tab]
        
        ax.clear()
        
        # Sub-colors
        colors = ["#10b981", "#06b6d4", "#8b5cf6", "#f59e0b", "#ec4899"]
        n_followers = len(history["followers"])
        time = history["time"]
        
        attack_cfg = config.get("attacks", {})
        fdi_start = attack_cfg.get("fdi", {}).get("start_time", 12.0)
        fdi_end = attack_cfg.get("fdi", {}).get("end_time", 22.0)
        dos_start = attack_cfg.get("dos", {}).get("start_time", 28.0)
        dos_end = attack_cfg.get("dos", {}).get("end_time", 38.0)
        
        if active_tab == "Trajectories":
            # Plot leader reference orbit
            ld = np.array(history["leader"])
            if len(ld) > 0:
                ax.plot(ld[:, 0], ld[:, 2], 'w--', label="Leader Target", linewidth=1.5)
                # Plot live node marker
                ax.scatter(ld[-1, 0], ld[-1, 2], color="#ffffff", s=50, zorder=5)
                
            # Plot followers positions
            for i in range(n_followers):
                fol = np.array(history["followers"][i])
                if len(fol) > 0:
                    ax.plot(fol[:, 0], fol[:, 2], color=colors[i % len(colors)], label=f"F{i+1}")
                    ax.scatter(fol[-1, 0], fol[-1, 2], color=colors[i % len(colors)], s=40, zorder=4)
            ax.set_title("2D Spatial Trajectories", fontsize=10, weight="bold")
            ax.set_xlabel("X Position (m)", fontsize=8)
            ax.set_ylabel("Y Position (m)", fontsize=8)
            ax.set_xlim([-18, 18])
            ax.set_ylim([-18, 18])
            ax.grid(True, color="gray", alpha=0.1)
            
        elif active_tab == "Consensus Error":
            # Plot consensus error for each agent
            for i in range(n_followers):
                ax.plot(time, history["tracking_errors"][i], color=colors[i % len(colors)], label=f"F{i+1}")
            self.shade_attack_windows(ax, fdi_start, fdi_end, dos_start, dos_end)
            ax.set_title("Consensus Tracking Error", fontsize=10, weight="bold")
            ax.set_xlabel("Time (s)", fontsize=8)
            ax.set_ylabel("Error (m)", fontsize=8)
            ax.grid(True, color="gray", alpha=0.1)
            
        elif active_tab == "Control Effort":
            # Plot control commands
            for i in range(n_followers):
                ax.plot(time, history["control_inputs"][i], color=colors[i % len(colors)], label=f"F{i+1}")
            self.shade_attack_windows(ax, fdi_start, fdi_end, dos_start, dos_end)
            ax.set_title("Control Input Command Magnitude ||u(t)||", fontsize=10, weight="bold")
            ax.set_xlabel("Time (s)", fontsize=8)
            ax.set_ylabel("Acceleration (m/s^2)", fontsize=8)
            ax.grid(True, color="gray", alpha=0.1)
            
        elif active_tab == "Observer Error":
            # Plot KF estimation errors
            for i in range(n_followers):
                ax.plot(time, history["estimation_errors"][i], color=colors[i % len(colors)], label=f"F{i+1}")
            self.shade_attack_windows(ax, fdi_start, fdi_end, dos_start, dos_end)
            ax.set_title("Kalman Filter Estimation Error", fontsize=10, weight="bold")
            ax.set_xlabel("Time (s)", fontsize=8)
            ax.set_ylabel("Error Norm", fontsize=8)
            ax.grid(True, color="gray", alpha=0.1)
            
        elif active_tab == "Lyapunov Decays":
            # Plot Lyapunov energy decay
            for i in range(n_followers):
                ax.plot(time, history["lyapunov_values"][i], color=colors[i % len(colors)], label=f"F{i+1}")
            self.shade_attack_windows(ax, fdi_start, fdi_end, dos_start, dos_end)
            ax.set_title("System Lyapunov Stability Decay V(t)", fontsize=10, weight="bold")
            ax.set_xlabel("Time (s)", fontsize=8)
            ax.set_ylabel("Energy Value", fontsize=8)
            ax.grid(True, color="gray", alpha=0.1)
            
        elif active_tab == "Pole s-Plane" and eigenvalues is not None:
            # Map discrete poles to continuous complex s-plane
            dt = config["system"]["dt"]
            s_poles = np.log(eigenvalues) / dt
            
            # Draw axes
            ax.axvline(0, color='white', linewidth=1.5, label='Stability Boundary')
            ax.axhline(0, color='gray', linewidth=0.5)
            # Shade regions
            ax.axvspan(-6.0, 0, color='green', alpha=0.1, label='Stable (LHP)')
            ax.axvspan(0, 3.0, color='red', alpha=0.1, label='Unstable (RHP)')
            # Plot poles
            ax.scatter(s_poles.real, s_poles.imag, marker='x', color='#06b6d4', s=100, label='CL Poles', zorder=5)
            
            for p in s_poles:
                ax.annotate(f"{p.real:.2f} + {p.imag:.2f}i", (p.real + 0.1, p.imag + 0.05), fontsize=8, color='#f3f4f6', weight='bold')
                
            ax.set_title("Continuous Closed-Loop Poles (s-plane)", fontsize=10, weight="bold")
            ax.set_xlabel("Real Part (σ)", fontsize=8)
            ax.set_ylabel("Imaginary Part (jω)", fontsize=8)
            ax.set_xlim([-5.0, 2.0])
            ax.set_ylim([-3.0, 3.0])
            ax.grid(True, color="gray", alpha=0.1)
            
        fig.tight_layout()
        canvas.draw()
        
    def shade_attack_windows(self, ax, fdi_start, fdi_end, dos_start, dos_end):
        """
        Shades active FDI and DoS intervals on the time axes.
        """
        ax.axvspan(fdi_start, fdi_end, color='yellow', alpha=0.1)
        ax.axvspan(dos_start, dos_end, color='gray', alpha=0.1)
        # Text label indicators using axis transforms
        ax.text((fdi_start + fdi_end)/2.0, 0.85, "FDI Active", color='darkgoldenrod',
                alpha=0.85, ha='center', weight='bold', fontsize=8, transform=ax.get_xaxis_transform())
        ax.text((dos_start + dos_end)/2.0, 0.85, "DoS Active", color='dimgray',
                alpha=0.85, ha='center', weight='bold', fontsize=8, transform=ax.get_xaxis_transform())
