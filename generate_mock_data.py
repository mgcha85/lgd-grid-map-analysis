import polars as pl
import numpy as np
import os

def generate_data(base_dir=".", n_defects=1000, n_outliers=50):
    """
    Generates mock data for panels and defects with updated requirements.
    Coordinate System: Center (0,0), Range X: -800~800, Y: -600~600.
    Panels: 40 Panels (8 cols x 5 rows).
    """
    
    # 1. Generate Panels
    # Grid: 8 cols (x), 5 rows (y)
    n_cols = 8
    n_rows = 5
    
    # Total Dimensions
    total_w = 1600
    total_h = 1200
    
    # Gaps
    gap_x = 10
    gap_y = 10
    
    # Calculate Panel Size
    # total_w = n_cols * panel_w + (n_cols - 1) * gap_x
    # panel_w = (total_w - (n_cols - 1) * gap_x) / n_cols
    panel_w = (total_w - (n_cols - 1) * gap_x) / n_cols
    panel_h = (total_h - (n_rows - 1) * gap_y) / n_rows
    
    # Start coordinates (Top-Left)
    # We want center to be (0,0).
    # Total span is -800 to 800.
    start_x = -800
    start_y = -600 # Let's say bottom is -600, top is 600.
    
    panel_rows = []
    
    for r in range(n_rows):
        for c in range(n_cols):
            # Sequence number (1-based, row-major or col-major? Let's do row-major)
            seq = r * n_cols + c + 1
            pid = f"Panel_{seq}"
            
            # Calculate bounds
            min_x = start_x + c * (panel_w + gap_x)
            max_x = min_x + panel_w
            
            min_y = start_y + r * (panel_h + gap_y)
            max_y = min_y + panel_h
            
            # 4 Corners
            corners = [
                (min_x, min_y),
                (max_x, min_y),
                (max_x, max_y),
                (min_x, max_y)
            ]
            
            for cx, cy in corners:
                panel_rows.append({
                    "panel_id": pid,
                    "sequence_no": seq,
                    "x": float(cx),
                    "y": float(cy)
                })
            
    df_panels = pl.DataFrame(panel_rows)
    df_panels.write_parquet("data/panels.parquet")
    print(f"Generated panels.parquet with {len(df_panels)} rows (40 panels).")

    # 2. Generate Defects (Clustered)
    rng = np.random.default_rng(42)
    defects = []
    
    # Generate clusters
    n_clusters = 15
    points_per_cluster = n_defects // n_clusters
    
    # Get panel bounds for valid placement
    panel_bounds = df_panels.group_by("panel_id").agg([
        pl.col("x").min().alias("min_x"),
        pl.col("x").max().alias("max_x"),
        pl.col("y").min().alias("min_y"),
        pl.col("y").max().alias("max_y"),
    ])
    
    panel_ids = panel_bounds["panel_id"].to_list()
    
    for _ in range(n_clusters):
        # Pick a random panel to put cluster in
        pid = rng.choice(panel_ids)
        bounds = panel_bounds.filter(pl.col("panel_id") == pid)
        min_x, max_x = bounds["min_x"][0], bounds["max_x"][0]
        min_y, max_y = bounds["min_y"][0], bounds["max_y"][0]
        
        # Cluster center
        cx = rng.uniform(min_x + 10, max_x - 10)
        cy = rng.uniform(min_y + 10, max_y - 10)
        
        # Spread
        sigma = rng.uniform(5, 20)
        
        # Generate points
        cluster_x = rng.normal(cx, sigma, points_per_cluster)
        cluster_y = rng.normal(cy, sigma, points_per_cluster)
        
        for x, y in zip(cluster_x, cluster_y):
            defects.append({
                "x": x,
                "y": y,
                "defect_type": "ClusterDefect"
            })
            
    # Add some random noise defects (uniform)
    n_noise = 200
    for _ in range(n_noise):
        pid = rng.choice(panel_ids)
        bounds = panel_bounds.filter(pl.col("panel_id") == pid)
        min_x, max_x = bounds["min_x"][0], bounds["max_x"][0]
        min_y, max_y = bounds["min_y"][0], bounds["max_y"][0]
        
        x = rng.uniform(min_x, max_x)
        y = rng.uniform(min_y, max_y)
        defects.append({
            "x": x,
            "y": y,
            "defect_type": "RandomNoise"
        })

    # 3. Generate Outliers (Outside panels, in gaps or outer bounds)
    for _ in range(n_outliers):
        # Randomly in the whole range, likely to hit gaps or outside
        x = rng.uniform(-900, 900)
        y = rng.uniform(-700, 700)
                
        defects.append({
            "x": x,
            "y": y,
            "defect_type": "Outlier"
        })

    df_defects = pl.DataFrame(defects)
    df_defects.write_parquet("data/defects.parquet")
    print(f"Generated defects.parquet with {len(df_defects)} rows.")

if __name__ == "__main__":
    generate_data()
