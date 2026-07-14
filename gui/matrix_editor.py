import customtkinter as ctk
import numpy as np

class MatrixEditor(ctk.CTkFrame):
    """
    A reusable matrix grid editor widget.
    Dynamically renders a grid of entry inputs to edit state-space matrices of any shape.
    """
    def __init__(self, parent, label: str = "Matrix Editor", **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        
        self.label_text = label
        self.entries = []
        self.shape = (1, 1)
        
        self.setup_widgets()
        
    def setup_widgets(self):
        # Header Label
        self.header_lbl = ctk.CTkLabel(self, text=self.label_text, 
                                       font=ctk.CTkFont(family="Helvetica", size=11, weight="bold"),
                                       text_color="#94a3b8")
        self.header_lbl.pack(anchor="w", pady=(2, 4))
        
        # Grid Container
        self.grid_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.grid_frame.pack(fill="x", pady=2)
        
    def set_matrix(self, matrix: np.ndarray):
        """
        Dynamically rebuilds the entry grid to match the input matrix shape and values.
        """
        # Clear existing entries
        for row in self.entries:
            for entry in row:
                entry.destroy()
        self.entries = []
        
        self.shape = matrix.shape
        rows, cols = self.shape
        
        # Build grid
        for r in range(rows):
            row_entries = []
            for c in range(cols):
                val = matrix[r, c] if len(matrix.shape) > 1 else (matrix[r] if r == c else 0.0)
                
                entry = ctk.CTkEntry(self.grid_frame, width=50, height=22, font=("Helvetica", 9),
                                     fg_color="#1e293b", border_color="rgba(255,255,255,0.1)",
                                     text_color="#ffffff", justify="center")
                entry.grid(row=r, column=c, padx=2, pady=2)
                entry.insert(0, f"{float(val):.4f}")
                row_entries.append(entry)
            self.entries.append(row_entries)
            
    def get_matrix(self) -> np.ndarray:
        """
        Reads values from the entry grid and returns them as a numpy array.
        Raises ValueError if any cell contains an invalid float string.
        """
        rows, cols = self.shape
        arr = np.zeros((rows, cols))
        for r in range(rows):
            for c in range(cols):
                val_str = self.entries[r][c].get()
                try:
                    arr[r, c] = float(val_str)
                except ValueError:
                    raise ValueError(f"Invalid float at row {r+1}, col {c+1}: '{val_str}'")
        return arr
