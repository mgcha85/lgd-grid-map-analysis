import polars as pl
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from generate_mock_data import generate_data
from gap_analysis import find_gaps, remove_gaps, filter_valid_points
from grid_mapping import generate_grid_cells, GridCell

def visualize_process():
    # 1. Generate & Load Data
    generate_data(n_outliers=10)
    df_panels = pl.read_parquet("panels.parquet")
    df_defects_raw = pl.read_parquet("defects.parquet")
    
    # 2. Process Data
    # Filter
    df_valid = filter_valid_points(df_defects_raw, df_panels)
    df_outliers = df_defects_raw.join(df_valid, on=["x", "y"], how="anti")
    
    # Gaps
    shift_x, shift_y = find_gaps(df_panels)
    
    # Transform
    df_clean_panels = remove_gaps(df_panels, shift_x, shift_y)
    df_clean_defects = remove_gaps(df_valid, shift_x, shift_y)
    
    # Grid Generation
    max_x_clean = df_clean_panels["x"].max() # Approximate max
    max_y_clean = df_clean_panels["y"].max()
    # Let's use hardcoded clean dimensions if we know them, or dynamic
    # From verification we know ~300x100.
    
    n_split_x = 3
    n_split_y = 3
    
    grid_cells = generate_grid_cells(
        n_split_x, n_split_y, 
        shift_x, shift_y, df_panels
    )
    
    # 3. Plot
    fig, axes = plt.subplots(1, 2, figsize=(20, 8))
    
    # --- Plot 1: Original Data ---
    ax = axes[0]
    ax.set_title("Original Data (with Sub-grid Overlay)")
    
    # Draw Original Panels
    panel_groups = df_panels.group_by("PanelID").agg([
        pl.col("x").min().alias("min_x"),
        pl.col("x").max().alias("max_x"),
        pl.col("y").min().alias("min_y"),
        pl.col("y").max().alias("max_y"),
    ])
    
    for row in panel_groups.iter_rows(named=True):
        width = row["max_x"] - row["min_x"]
        height = row["max_y"] - row["min_y"]
        rect = patches.Rectangle((row["min_x"], row["min_y"]), width, height, 
                                 linewidth=2, edgecolor='blue', facecolor='none', alpha=0.3)
        ax.add_patch(rect)
        # Panel Label
        # ax.text(row["min_x"], row["min_y"], row["PanelID"], fontsize=12, color='blue', va='top')

    # Draw Grid Cells (Projected to Original)
    # GridCell has origin_x/origin_y which is the CENTER.
    # We need to draw the rectangle. 
    # Original rectangle logic: 
    # Clean: [clean_x - w/2, clean_x + w/2].
    # Original: Map clean bounds to original.
    # Simple way: Map (clean_x - w/2, clean_y - h/2) -> BottomLeft.
    # Since shift is constant per interval, mapping corners is safe unless splitting a gap (which grid gen avoids/handles).
    
    # Let's map corners for drawing
    corners_data = []
    
    # To map arbitrary points, we need a helper or just reuse remove_gaps reversed? 
    # Actually grid_mapping does the reverse mapping logic.
    # But `generate_grid_cells` only returns the center.
    # We can approximate for visualization: center +/- size/2. 
    # But wait, 'origin_x' is the center in original space.
    # Original interval is contiguous for the cell? Yes, unless it spans a gap.
    # But we filter cells by 'contained in panel'. So they don't span gaps.
    # So we can just use size.
    
    for cell in grid_cells:
        # Original Plot
        # Center: cell.origin_x, cell.origin_y
        # Size: cell.width, cell.height
        
        ox = cell.origin_x - cell.width/2
        oy = cell.origin_y - cell.height/2
        
        rect = patches.Rectangle((ox, oy), cell.width, cell.height, 
                                 linewidth=1, edgecolor='grey', facecolor='none', linestyle=':')
        ax.add_patch(rect)
        
        # Label Sub-ID
        short_id = cell.sub_grid_id.replace(cell.panel_id, "")
        ax.text(cell.origin_x, cell.origin_y, short_id, 
                ha='center', va='center', fontsize=6, color='grey')
                
    # Defects
    if not df_outliers.is_empty():
        ax.scatter(df_outliers["x"], df_outliers["y"], c='red', marker='x', s=20, label='Outlier')
    if not df_valid.is_empty():
        ax.scatter(df_valid["x"], df_valid["y"], c='green', s=10, label='Valid')

    ax.autoscale()
    ax.legend()
    
    # --- Plot 2: Processed Data ---
    ax = axes[1]
    ax.set_title("Processed Data (Gap Removed + Grid)")

    # Draw Clean Panels
    panel_groups_clean = df_clean_panels.group_by("PanelID").agg([
        pl.col("x").min().alias("min_x"),
        pl.col("x").max().alias("max_x"),
        pl.col("y").min().alias("min_y"),
        pl.col("y").max().alias("max_y"),
    ])
    
    for row in panel_groups_clean.iter_rows(named=True):
        width = row["max_x"] - row["min_x"]
        height = row["max_y"] - row["min_y"]
        rect = patches.Rectangle((row["min_x"], row["min_y"]), width, height, 
                                 linewidth=2, edgecolor='blue', facecolor='none', alpha=0.3)
        ax.add_patch(rect)

    # Draw Grid Cells (Clean Space)
    for cell in grid_cells:
        cx = cell.clean_x - cell.width/2
        cy = cell.clean_y - cell.height/2
        
        rect = patches.Rectangle((cx, cy), cell.width, cell.height, 
                                 linewidth=1, edgecolor='grey', facecolor='none', linestyle=':')
        ax.add_patch(rect)
        
        short_id = cell.sub_grid_id.replace(cell.panel_id, "")
        ax.text(cell.clean_x, cell.clean_y, short_id, 
                ha='center', va='center', fontsize=6, color='grey')

    # Clean Defects
    if not df_clean_defects.is_empty():
        ax.scatter(df_clean_defects["x"], df_clean_defects["y"], c='green', s=10, label='Valid')
        
    ax.autoscale()
    ax.legend()

    plt.tight_layout()
    output_file = "gap_analysis_visualization.png"
    plt.savefig(output_file, dpi=150)
    print(f"Visualization saved to {output_file}")

if __name__ == "__main__":
    visualize_process()
