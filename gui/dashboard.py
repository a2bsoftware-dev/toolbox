import customtkinter as ctk
import tkinter as tk

class Dashboard(ctk.CTkFrame):
    """
    Dashboard container housing the network topology canvas and the cloud status metrics grid.
    Provides real-time updates of packets sent/lost, latencies, and security shield states.
    """
    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.setup_layout()
        
    def setup_layout(self):
        # 1. Top Section: Topology and Cloud split
        self.top_section = ctk.CTkFrame(self, fg_color="transparent")
        self.top_section.pack(side="top", fill="x", pady=2)
        
        # Topology Frame (Phase 6)
        self.anim_container = ctk.CTkFrame(self.top_section, height=270, fg_color="#0a0e17", border_width=1, border_color="#1e293b")
        self.anim_container.pack(side="left", fill="both", expand=True, padx=2)
        
        from gui.network_animator import NetworkAnimator
        self.net_animator = NetworkAnimator(self.anim_container)
        self.net_animator.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Cloud Database Monitor Frame (Phase 7)
        self.cloud_container = ctk.CTkFrame(self.top_section, width=320, height=270, fg_color="#0f172a", border_width=1, border_color="#1e293b")
        self.cloud_container.pack(side="right", fill="both", padx=2)
        
        ctk.CTkLabel(self.cloud_container, text="☁️ Cloud Database Monitor", 
                     font=ctk.CTkFont(family="Helvetica", size=12, weight="bold"), 
                     text_color="#94a3b8").pack(anchor="w", padx=15, pady=(12, 6))
                     
        self.setup_cloud_labels()
        
        # 2. Playback Scrubber Frame
        self.playback_bar = ctk.CTkFrame(self, fg_color="#0f172a", border_width=1, border_color="#1e293b")
        self.playback_bar.pack(side="top", fill="x", pady=2)
        
        # Scrubber time indicators
        self.time_lbl = ctk.CTkLabel(self.playback_bar, text="0.00s", font=ctk.CTkFont(family="Courier", size=11))
        self.time_lbl.pack(side="left", padx=10, pady=5)
        
        self.scrubber = ctk.CTkSlider(self.playback_bar, from_=0, to=900, number_of_steps=900)
        self.scrubber.set(0)
        self.scrubber.pack(side="left", fill="x", expand=True, padx=10)
        
        self.max_time_lbl = ctk.CTkLabel(self.playback_bar, text="45.0s", font=ctk.CTkFont(family="Courier", size=11))
        self.max_time_lbl.pack(side="left", padx=10)
        
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
            row = ctk.CTkFrame(self.cloud_container, fg_color="transparent")
            row.pack(fill="x", padx=15, pady=3)
            
            ctk.CTkLabel(row, text=label, font=lbl_font, width=150, anchor="w").pack(side="left")
            widget = ctk.CTkLabel(row, text=default, font=val_font, text_color=color, width=120, anchor="e")
            widget.pack(side="right")
            self.cloud_widgets[key] = widget
            
    def update_cloud_metrics(self, simulator, status: str):
        """
        Dynamically refreshes the status labels on the metrics card layout.
        """
        sec_cfg = simulator.config["security"]
        
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
            
        # Packet counters
        self.cloud_widgets["lbl_sent"].configure(text=str(simulator.packets_sent))
        self.cloud_widgets["lbl_lost"].configure(text=str(simulator.packets_lost))
        
        # Active state & latency
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
