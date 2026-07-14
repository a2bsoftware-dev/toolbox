import customtkinter as ctk

class Sidebar(ctk.CTkFrame):
    """
    Sidebar widget managing the simulation lifecycle controls (Run, Pause, Reset),
    segmented tab selections, and project file managers.
    """
    def __init__(self, parent, on_play_callback, on_reset_callback, 
                 on_tab_change_callback, on_load_callback, on_save_callback,
                 on_pdf_callback, on_csv_callback, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.on_play = on_play_callback
        self.on_reset = on_reset_callback
        self.on_tab_change = on_tab_change_callback
        self.on_load = on_load_callback
        self.on_save = on_save_callback
        self.on_pdf = on_pdf_callback
        self.on_csv = on_csv_callback
        
        self.configure(fg_color="#0f172a", border_width=1, border_color="rgba(255,255,255,0.05)")
        self.setup_widgets()
        
    def setup_widgets(self):
        title_font = ctk.CTkFont(family="Helvetica", size=13, weight="bold")
        lbl_font = ctk.CTkFont(family="Helvetica", size=11)
        
        # App Title
        ctk.CTkLabel(self, text="🛡️ NCS CONTROL BOX", font=ctk.CTkFont(family="Helvetica", size=16, weight="bold"),
                     text_color="#06b6d4").pack(anchor="w", padx=15, pady=(15, 10))
        
        # Segmented Tabs to switch panels
        self.nav_tabs = ctk.CTkSegmentedButton(self, values=["Model", "Security"], 
                                               command=self.on_tab_change,
                                               selected_color="#06b6d4",
                                               selected_hover_color="#0891b2",
                                               text_color="#f3f4f6")
        self.nav_tabs.pack(fill="x", padx=10, pady=5)
        self.nav_tabs.set("Model")
        
        # Inner content frame (where config panels will be packed)
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Playback Controls Frame
        playback_frame = ctk.CTkFrame(self, fg_color="transparent")
        playback_frame.pack(fill="x", pady=10, padx=10)
        
        ctk.CTkLabel(playback_frame, text="⚡ Simulation Playback", font=title_font, text_color="#94a3b8").pack(anchor="w", pady=2)
        
        self.play_btn = ctk.CTkButton(playback_frame, text="Play", height=28, fg_color="#06b6d4", text_color="#0a0e17",
                                       hover_color="#0891b2", font=ctk.CTkFont(weight="bold"), command=self.on_play)
        self.play_btn.pack(fill="x", pady=2)
        
        self.reset_btn = ctk.CTkButton(playback_frame, text="Reset Simulation", height=28, fg_color="#1e293b",
                                        hover_color="#334155", command=self.on_reset)
        self.reset_btn.pack(fill="x", pady=2)
        
        # Project manager Frame
        proj_frame = ctk.CTkFrame(self, fg_color="transparent")
        proj_frame.pack(fill="x", pady=(5, 15), padx=10)
        
        ctk.CTkLabel(proj_frame, text="📁 Project Manager", font=title_font, text_color="#94a3b8").pack(anchor="w", pady=2)
        
        # File row 1
        row1 = ctk.CTkFrame(proj_frame, fg_color="transparent")
        row1.pack(fill="x", pady=2)
        ctk.CTkButton(row1, text="Open Project", height=24, fg_color="#1e293b", hover_color="#334155", command=self.on_load).pack(side="left", fill="x", expand=True, padx=2)
        ctk.CTkButton(row1, text="Save Project", height=24, fg_color="#1e293b", hover_color="#334155", command=self.on_save).pack(side="left", fill="x", expand=True, padx=2)
        
        # File row 2
        row2 = ctk.CTkFrame(proj_frame, fg_color="transparent")
        row2.pack(fill="x", pady=2)
        ctk.CTkButton(row2, text="Export PDF", height=24, fg_color="#059669", hover_color="#047857", text_color="#ffffff", command=self.on_pdf).pack(side="left", fill="x", expand=True, padx=2)
        ctk.CTkButton(row2, text="Export CSV", height=24, fg_color="#059669", hover_color="#047857", text_color="#ffffff", command=self.on_csv).pack(side="left", fill="x", expand=True, padx=2)
        
    def set_playing_state(self, is_playing: bool):
        if is_playing:
            self.play_btn.configure(text="Pause", fg_color="#ef4444", text_color="#ffffff", hover_color="#dc2626")
        else:
            self.play_btn.configure(text="Play", fg_color="#06b6d4", text_color="#0a0e17", hover_color="#0891b2")
