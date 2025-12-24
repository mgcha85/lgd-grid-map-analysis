from dataclasses import dataclass
import polars as pl
import numpy as np
from gap_analysis import remove_gaps

@dataclass(frozen=True, slots=True)
class GridCell:
    """
    Represents a grid cell.
    """
    clean_x: float # Center X in clean coordinates
    clean_y: float # Center Y in clean coordinates
    origin_center_x: float
    origin_center_y: float
    origin_min_x: float
    origin_min_y: float
    width: float
    height: float
    panel_id: str
    sub_grid_id: str
    global_row: int # Global row index in the full matrix
    global_col: int # Global col index in the full matrix

def get_panel_label(seq_no, n_cols=8):
    """
    Converts sequence number to Label (e.g., A1, B1, A2).
    Cols: A, B, C... (Left to Right)
    Rows: 1, 2, 3... (Bottom to Top)
    """
    # 0-based indices
    idx = seq_no - 1
    row_idx = idx // n_cols
    col_idx = idx % n_cols
    
    col_char = chr(ord('A') + col_idx)
    row_str = str(row_idx + 1)
    
    return f"{col_char}{row_str}"

def generate_grid_cells(
    n_split_x: int, 
    n_split_y: int,
    shift_map_x: pl.DataFrame, 
    shift_map_y: pl.DataFrame, 
    panel_df: pl.DataFrame
) -> list[GridCell]:
    """
    Generates grid cells by splitting each panel into n_split_x * n_split_y chunks.
    """
    
    # 1. Get Panel Bounds and Sequence
    # We need sequence to determine global position
    panel_bounds = panel_df.group_by("panel_id").agg([
        pl.col("x").min().alias("p_min_x"),
        pl.col("x").max().alias("p_max_x"),
        pl.col("y").min().alias("p_min_y"),
        pl.col("y").max().alias("p_max_y"),
        pl.col("sequence_no").first().alias("seq")
    ]).sort("seq")
    
    # Determine grid layout from panels
    # Assuming standard grid filling (row-major)
    # 40 panels, 8 cols.
    n_panel_cols = 8
    
    # 2. Generate Cells for each Panel
    cell_data = []
    
    rows = panel_bounds.iter_rows(named=True)
    for row in rows:
        p_id = row["panel_id"]
        try:
            seq = int(p_id[-1])
        except:
            raise ValueError(f"Invalid panel ID: {p_id}")

        min_x = row["p_min_x"]
        max_x = row["p_max_x"]
        min_y = row["p_min_y"]
        max_y = row["p_max_y"]
        
        # Panel Label
        panel_label = get_panel_label(seq, n_panel_cols)
        
        # Panel Grid Position (0-based)
        p_row = (seq - 1) // n_panel_cols
        p_col = (seq - 1) % n_panel_cols
        
        width = max_x - min_x
        height = max_y - min_y
        
        step_x = width / n_split_x
        step_y = height / n_split_y
         
        for i in range(n_split_x):
            for j in range(n_split_y):
                # i is x-index (col), j is y-index (row) within panel
                
                # Coordinates
                cell_min_x = min_x + step_x * i
                cell_min_y = min_y + step_y * j
                cx = cell_min_x + step_x * 0.5
                cy = cell_min_y + step_y * 0.5
                
                # Sub-ID Generation
                col_char = chr(ord('a') + max(0, min(25, i)))
                row_str = str(j + 1)
                # New Format: A1-a1
                sub_id = f"{panel_label}-{col_char}{row_str}"
                
                # Global Indices
                # Global Row = Panel Row * Split Y + Sub Row (j)
                # Global Col = Panel Col * Split X + Sub Col (i)
                g_row = p_row * n_split_y + j
                g_col = p_col * n_split_x + i
                
                cell_data.append({
                    "origin_center_x": cx,
                    "origin_center_y": cy,
                    "origin_min_x": cell_min_x,
                    "origin_min_y": cell_min_y,
                    "panel_id": p_id,
                    "panel_label": panel_label, # Store for ref
                    "sub_grid_id": sub_id,
                    "width": step_x,
                    "height": step_y,
                    "global_row": g_row,
                    "global_col": g_col
                })
                
    if not cell_data:
        return []

    # 3. Calculate Clean Coordinates
    df_cells_origin = pl.DataFrame(cell_data)
    
    # Use remove_gaps to translate origin_center_x/y to clean_x/y
    df_input = df_cells_origin.rename({"origin_center_x": "x", "origin_center_y": "y"})
    df_clean = remove_gaps(df_input, shift_map_x, shift_map_y)
    
    df_final = df_clean.rename({"x": "clean_x", "y": "clean_y"})
    
    # Join back
    df_combined = df_final.join(df_cells_origin, on="sub_grid_id") 
    
    result = []
    for row in df_combined.iter_rows(named=True):
        result.append(GridCell(
            clean_x=row["clean_x"],
            clean_y=row["clean_y"],
            origin_center_x=row["origin_center_x"],
            origin_center_y=row["origin_center_y"],
            origin_min_x=row["origin_min_x"],
            origin_min_y=row["origin_min_y"],
            width=row["width"],
            height=row["height"],
            panel_id=row["panel_id"],
            sub_grid_id=row["sub_grid_id"],
            global_row=row["global_row"],
            global_col=row["global_col"]
        ))
        
    return result
