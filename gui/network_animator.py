import tkinter as tk
import customtkinter as ctk
import math
import time

class NetworkAnimator(ctk.CTkFrame):
    """
    Tkinter Canvas widget that renders real-time multi-agent network topologies
    with moving packet flow particles and color-shifting telemetry links.
    """
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.canvas = tk.Canvas(self, bg="#0a0e17", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        
        self.particle_progress = 0.0
        self.n_followers = 3
        
        # Start redraw loop
        self.canvas.bind("<Configure>", lambda e: self.redraw())
        
    def set_n_followers(self, count: int):
        self.n_followers = count
        self.redraw()
        
    def draw(self, status: str):
        """
        Public update method called at each simulation timestep.
        """
        # Update particle flow index
        if status != "dos":
            self.particle_progress = (self.particle_progress + 0.08) % 1.0
        else:
            self.particle_progress = 0.0
            
        self.redraw(status)
        
    def redraw(self, status: str = "normal"):
        self.canvas.delete("all")
        
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w < 50 or h < 50:
            return
            
        # Coordinates
        cloud_node = {"x": w / 2, "y": h / 2 - 10, "label": "Cloud"}
        leader_node = {"x": w / 2, "y": 40, "label": "Leader"}
        
        followers = []
        for i in range(self.n_followers):
            x_pos = w / 2
            if self.n_followers > 1:
                # Distribute followers horizontally
                span = w * 0.7
                start_x = w / 2 - span / 2
                x_pos = start_x + (i / (self.n_followers - 1)) * span
            followers.append({"x": x_pos, "y": h - 45, "label": f"F{i+1}"})
            
        # Determine link parameters based on security status
        link_color = "#10b981" # Green
        particle_color = "#10b981"
        is_dashed = False
        
        if status == "dos":
            link_color = "#ef4444" # Red
            is_dashed = True
            particle_color = None
        elif status == "attacked":
            link_color = "#f59e0b" # Orange
            particle_color = "#f59e0b"
        elif status == "secured":
            link_color = "#06b6d4" # Cyan
            particle_color = "#06b6d4"
        elif status in ["delayed", "replayed"]:
            link_color = "#8b5cf6" # Purple
            particle_color = "#8b5cf6"
            
        # 1. Draw Links
        # Leader to Cloud
        self.draw_link(leader_node, cloud_node, link_color, is_dashed)
        # Cloud to Followers
        for f in followers:
            self.draw_link(cloud_node, f, link_color, is_dashed)
            
        # 2. Draw Packet Particles
        if particle_color:
            # Leader to Cloud
            self.draw_particle(leader_node, cloud_node, self.particle_progress, particle_color)
            # Cloud to Followers
            for idx, f in enumerate(followers):
                # Stagger progress slightly
                progress = (self.particle_progress + idx * 0.3) % 1.0
                self.draw_particle(cloud_node, f, progress, particle_color)
                
        # 3. Draw Nodes
        # Leader (White)
        self.draw_node(leader_node, "#ffffff", 14)
        # Cloud (Cyan/Orange)
        cloud_color = "#06b6d4" if status == "secured" else "#f59e0b"
        self.draw_node(cloud_node, cloud_color, 18, is_cloud=True)
        # Followers (Alternating Theme Colors)
        colors = ["#10b981", "#06b6d4", "#8b5cf6", "#f59e0b", "#ec4899"]
        for i, f in enumerate(followers):
            color = colors[i % len(colors)]
            self.draw_node(f, color, 12)
            
    def draw_link(self, p1, p2, color: str, is_dashed: bool):
        dash_tuple = (6, 6) if is_dashed else None
        self.canvas.create_line(p1["x"], p1["y"], p2["x"], p2["y"],
                                fill=color, width=2.5, dash=dash_tuple)
                                
    def draw_particle(self, p1, p2, progress: float, color: str):
        px = p1["x"] + (p2["x"] - p1["x"]) * progress
        py = p1["y"] + (p2["y"] - p1["y"]) * progress
        r = 4.5
        self.canvas.create_oval(px - r, py - r, px + r, py + r,
                                fill=color, outline="#ffffff", width=0.8)
                                
    def draw_node(self, node, color: str, size: float, is_cloud: bool = False):
        x, y = node["x"], node["y"]
        
        # Outer ring
        self.canvas.create_oval(x - size, y - size, x + size, y + size,
                                fill="#111827", outline=color, width=3)
                                
        # Node text label
        self.canvas.create_text(x, y + size + 10, text=node["label"],
                                fill="#f3f4f6", font=("Helvetica", 9, "bold"))
                                
        if is_cloud:
            self.canvas.create_text(x, y, text="CLOUD",
                                    fill="#ffffff", font=("Helvetica", 8, "bold"))
