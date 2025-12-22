from dataclasses import dataclass
import polars as pl
import numpy as np
from gap_analysis import remove_gaps

@dataclass(frozen=True, slots=True)
class GridCell:
    """
    Represents a grid cell.
    """
    clean_x: float
    clean_y: float
    origin_x: float
    origin_y: float
    width: float
    height: float
    panel_id: str
    sub_grid_id: str

def generate_grid_cells(
    n_split_x: int, 
    n_split_y: int,
    shift_map_x: pl.DataFrame, 
    shift_map_y: pl.DataFrame, 
    panel_df: pl.DataFrame
) -> list[GridCell]:
    """
    Generates grid cells by splitting each panel into n_split_x * n_split_y chunks.
    
    Args:
        n_split_x: Number of splits in X direction per panel.
        n_split_y: Number of splits in Y direction per panel.
        shift_map_x: Shift map for X (to calculate clean coords).
        shift_map_y: Shift map for Y (to calculate clean coords).
        panel_df: DataFrame with [PanelID, x, y] (Original corners).
    
    Returns:
        List of GridCell objects.
    """
    
    # 1. Get Panel Bounds
    panel_bounds = panel_df.group_by("PanelID").agg([
        pl.col("x").min().alias("p_min_x"),
        pl.col("x").max().alias("p_max_x"),
        pl.col("y").min().alias("p_min_y"),
        pl.col("y").max().alias("p_max_y"),
    ])
    
    # 2. Generate Cells for each Panel
    cell_data = []
    
    rows = panel_bounds.iter_rows(named=True)
    for row in rows:
        p_id = row["PanelID"]
        min_x = row["p_min_x"]
        max_x = row["p_max_x"]
        min_y = row["p_min_y"]
        max_y = row["p_max_y"]
        
        width = max_x - min_x
        height = max_y - min_y
        
        step_x = width / n_split_x
        step_y = height / n_split_y
         
        for i in range(n_split_x):
            for j in range(n_split_y):
                # Center of the cell in Original Coordinates
                cx = min_x + step_x * (i + 0.5)
                cy = min_y + step_y * (j + 0.5)
                
                # Sub-ID Generation
                col_char = chr(ord('a') + max(0, min(25, i)))
                row_str = str(j + 1)
                sub_id = f"{p_id}{col_char}{row_str}"
                
                cell_data.append({
                    "origin_x": cx,
                    "origin_y": cy,
                    "PanelID": p_id,
                    "sub_grid_id": sub_id,
                    "width": step_x,
                    "height": step_y
                })
                
    if not cell_data:
        return []

    # 3. Calculate Clean Coordinates
    # Construct DataFrame
    df_cells_origin = pl.DataFrame(cell_data)
    
    # Use remove_gaps to translate origin_x/origin_y to clean_x/clean_y
    # Note: remove_gaps expects columns "x" and "y" by default logic or we rename.
    # The remove_gaps function in gap_analysis.py typically works on "x" and "y" cols.
    # Let's rename for the call.
    
    df_input = df_cells_origin.rename({"origin_x": "x", "origin_y": "y"})
    df_clean = remove_gaps(df_input, shift_map_x, shift_map_y)
    
    # Rename back or just use the result
    # remove_gaps returns the dataframe with modified x, y.
    
    result = []
    # Join clean x,y back with metadata if strict order is preserved (it is in Polars usually if no sort)
    # But remove_gaps uses join_asof which might require sorting? 
    # Let's look at gap_analysis.py.
    # It sorts by x to join shift_x, then sort by y to join shift_y. Order might change.
    # But we can recover by joining on IDs if unique? 
    # sub_grid_id is unique.
    
    df_final = df_clean.rename({"x": "clean_x", "y": "clean_y"})
    
    # We also need the original coords and width/height.
    # Did remove_gaps keep other columns? Yes, typical join preserves columns.
    
    for row in df_final.iter_rows(named=True):
        # We need original x/y. remove_gaps modified 'x' and 'y' in place (or returned new cols).
        # Wait, remove_gaps usually effectively *changes* the column values.
        # So we might have lost original x/y in df_clean.
        # But we have them in df_cells_origin.
        # We can join df_clean on 'sub_grid_id' with df_cells_origin.
        
        # Or better: check gap_analysis.py behavior.
        # remove_gaps usually does `df.join_asof(...)`, returns with shifted values.
        # If it replaces 'x', 'y', we lost original.
        pass

    # Safe approach: Join back with original data on sub_grid_id
    df_combined = df_final.join(df_cells_origin, on="sub_grid_id") 
    # df_final has clean_x, clean_y (renamed from x,y). df_cells_origin has origin_x, origin_y.
    
    for row in df_combined.iter_rows(named=True):
        result.append(GridCell(
            clean_x=row["clean_x"],
            clean_y=row["clean_y"],
            origin_x=row["origin_x"],
            origin_y=row["origin_y"],
            width=row["width"],
            height=row["height"],
            panel_id=row["PanelID"],
            sub_grid_id=row["sub_grid_id"]
        ))
        
    return result
