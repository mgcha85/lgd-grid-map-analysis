import polars as pl
import numpy as np
import os

def generate_data(base_dir=".", n_outliers=0):
    """
    Generates mock data for panels and defects.
    Layout: 2 rows x 3 columns.
    Panel Size: width=100, height=50.
    Gaps: x_gap=10, y_gap=20.
    """
    
    # 1. Generate Panels
    # Grid: 2 rows (y), 3 cols (x)
    n_rows = 2
    n_cols = 3
    panel_w = 100.0
    panel_h = 50.0
    gap_x = 10.0
    gap_y = 20.0
    
    panels = []
    
    for r in range(n_rows):
        for c in range(n_cols):
            panel_id = f"P_{r}_{c}"
            
            # Origin of this panel
            x_start = c * (panel_w + gap_x)
            y_start = r * (panel_h + gap_y)
            
            x_end = x_start + panel_w
            y_end = y_start + panel_h
            
            # 4 Corners: (x_start, y_start), (x_end, y_start), (x_end, y_end), (x_start, y_end)
            # Order doesn't strictly matter for the logic as long as min/max captures bounds
            corners = [
                (x_start, y_start),
                (x_end, y_start),
                (x_end, y_end),
                (x_start, y_end)
            ]
            
            for cx, cy in corners:
                panels.append({"PanelID": panel_id, "x": cx, "y": cy})
                
    df_panels = pl.DataFrame(panels)
    df_panels.write_parquet(os.path.join(base_dir, "panels.parquet"))
    print(f"Generated panels.parquet with {len(df_panels)} rows.")

    # 2. Generate Defects
    # Randomly place defects inside valid panel areas
    n_defects = 20
    defects = []
    
    # Get bounds for each panel to place points effectively
    # Group by PanelID to find bounds
    panel_bounds = (
        df_panels
        .group_by("PanelID")
        .agg([
            pl.col("x").min().alias("min_x"),
            pl.col("x").max().alias("max_x"),
            pl.col("y").min().alias("min_y"),
            pl.col("y").max().alias("max_y"),
        ])
    )
    
    # Randomly pick a panel and generate point inside
    # We will just generate points and check if they are inside, or easier: 
    # Just iterate and generate a few points per panel.
    
    rng = np.random.default_rng(42)
    
    panel_ids = panel_bounds["PanelID"].to_list()
    
    for _ in range(n_defects):
        pid = rng.choice(panel_ids)
        min_x = panel_bounds.filter(pl.col("PanelID") == pid)["min_x"][0]
        max_x = panel_bounds.filter(pl.col("PanelID") == pid)["max_x"][0]
        min_y = panel_bounds.filter(pl.col("PanelID") == pid)["min_y"][0]
        max_y = panel_bounds.filter(pl.col("PanelID") == pid)["max_y"][0]

        dx = rng.uniform(min_x, max_x)
        dy = rng.uniform(min_y, max_y)
        dtype = rng.choice(["Scratch", "Dent", "Stain"])
        
        defects.append({"x": dx, "y": dy, "defect_type": dtype})
    
    # Generate Outliers (Machine Malfunction Data)
    for _ in range(n_outliers):
        # Pick a spot clearly outside. 
        # For example, in the negative area or way beyond data bounds.
        # Or specifically in the gap (which should be theoretically invalid for 'on-panel' data, 
        # though strictly speaking a gap is space between panels. 
        # The user said "outside the four corners", meaning outside any valid panel rectangle.
        
        # Method: Generate a completely random point in the bounding box of the whole system,
        # but ensure it's not inside any panel. 
        # Simpler: Generate points in gaps or clearly outside.
        
        # Let's generate some in the gaps
        is_x_gap = rng.choice([True, False])
        if is_x_gap:
            # First vertical gap is approx at x=100..110
            dx = rng.uniform(102, 108) 
            dy = rng.uniform(0, 100)
        else:
            # Negative coords (clearly wrong)
            dx = rng.uniform(-50, -10)
            dy = rng.uniform(-50, -10)
            
        defects.append({"x": dx, "y": dy, "defect_type": "DataError"})

    df_defects = pl.DataFrame(defects)
    df_defects.write_parquet(os.path.join(base_dir, "defects.parquet"))
    print(f"Generated defects.parquet with {len(df_defects)} rows (incl. {n_outliers} outliers).")

if __name__ == "__main__":
    generate_data()
