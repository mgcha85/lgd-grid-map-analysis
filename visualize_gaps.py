import polars as pl
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from generate_mock_data import generate_data
from gap_analysis import find_gaps, remove_gaps, filter_valid_points

def visualize_process():
    # 1. Generate & Load Data
    generate_data(n_outliers=10) # More outliers for visibility
    df_panels = pl.read_parquet("panels.parquet")
    df_defects_raw = pl.read_parquet("defects.parquet")
    
    # 2. Process Data
    # Identify outliers vs valid
    df_valid = filter_valid_points(df_defects_raw, df_panels)
    
    # Identify outliers for plotting (diff)
    # Anti-join to find what was removed
    df_outliers = df_defects_raw.join(df_valid, on=["x", "y"], how="anti")
    
    # Calculate Gaps
    shift_x, shift_y = find_gaps(df_panels)
    
    # Transform Panels and Valid Defects
    df_clean_panels = remove_gaps(df_panels, shift_x, shift_y)
    df_clean_defects = remove_gaps(df_valid, shift_x, shift_y)
    
    # 3. Plot
    fig, axes = plt.subplots(1, 2, figsize=(15, 6))
    
    # --- Plot 1: Original ---
    ax = axes[0]
    ax.set_title("Original Data (with Gaps & Outliers)")
    
    # Draw Panels
    # Since we have corner points, we can compute bounds per panel to draw rects
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
                                 linewidth=1, edgecolor='blue', facecolor='lightblue', alpha=0.5, label="Panel" if row["PanelID"]=="P_0_0" else "")
        ax.add_patch(rect)
        ax.text(row["min_x"]+width/2, row["min_y"]+height/2, row["PanelID"], ha='center', va='center', fontsize=8, color='blue')

    # Draw Valid Defects
    if not df_valid.is_empty():
        ax.scatter(df_valid["x"], df_valid["y"], c='green', s=10, label='Valid Defect')
        
    # Draw Outliers
    if not df_outliers.is_empty():
        ax.scatter(df_outliers["x"], df_outliers["y"], c='red', marker='x', s=30, label='Outlier')
        
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.legend()
    # Auto scale to include everything
    ax.autoscale()
    
    # --- Plot 2: Gap Removed ---
    ax = axes[1]
    ax.set_title("Processed Data (Gaps Removed)")
    
    # Draw Clean Panels
    # Need to aggregate corners again for the cleaned panels
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
                                 linewidth=1, edgecolor='blue', facecolor='lightblue', alpha=0.5)
        ax.add_patch(rect)
        ax.text(row["min_x"]+width/2, row["min_y"]+height/2, row["PanelID"], ha='center', va='center', fontsize=8, color='blue')

    # Draw Clean Defects
    if not df_clean_defects.is_empty():
        ax.scatter(df_clean_defects["x"], df_clean_defects["y"], c='green', s=10, label='Valid Defect')

    # Note: Outliers are filtered out, so not shown here (or could show where they would be if projected? No, usually discarded)
    
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_xlim(axes[0].get_xlim()) # Keep scale similar if desired, but here ranges change.
    ax.autoscale()

    plt.tight_layout()
    output_file = "gap_analysis_visualization.png"
    plt.savefig(output_file)
    print(f"Visualization saved to {output_file}")

if __name__ == "__main__":
    visualize_process()
