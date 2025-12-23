import polars as pl
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import numpy as np
import os
from gap_analysis import find_gaps, remove_gaps, filter_valid_points
from grid_mapping import generate_grid_cells, get_panel_label
from analysis_utils import (
    generate_heatmap, 
    generate_background_noise, 
    remove_noise, 
    find_connected_components, 
    map_points_to_components,
    calculate_original_bounds,
    count_defects_per_subgrid,
    create_subgrid_matrix,
    analyze_regions
)

def main():
    print("1. Loading Data...")
    df_panels = pl.read_parquet("panels.parquet")
    df_defects = pl.read_parquet("defects.parquet")
    
    print(f"   Panels: {len(df_panels)}")
    print(f"   Defects: {len(df_defects)}")
    
    # 2. Filter Outliers
    print("2. Filtering Outliers...")
    df_valid_defects = filter_valid_points(df_defects, df_panels)
    print(f"   Valid Defects: {len(df_valid_defects)} (Removed {len(df_defects) - len(df_valid_defects)})")
    
    # Preserve original coordinates
    df_valid_defects = df_valid_defects.with_columns([
        pl.col("x").alias("orig_x"),
        pl.col("y").alias("orig_y")
    ])
    
    # 3. Gap Analysis & Removal
    print("3. Removing Gaps...")
    shift_x, shift_y = find_gaps(df_panels)
    
    df_clean_defects = remove_gaps(df_valid_defects, shift_x, shift_y)
    
    # 4. Generate Grid Cells (3x3 Split)
    print("4. Generating Grid Cells...")
    grid_cells = generate_grid_cells(3, 3, shift_x, shift_y, df_panels)
    print(f"   Generated {len(grid_cells)} grid cells.")
    
    # 5. Sub-grid Analysis (Cleaned Data)
    print("5. Analyzing Sub-grids (Cleaned Data)...")
    
    # Count defects per sub-grid (Raw)
    df_subgrid_counts_raw = count_defects_per_subgrid(df_valid_defects, grid_cells)
    
    # Calculate Cleaned Counts (Remove Noise)
    # Noise params: mean=0.5 per 10x10 bin (area 100).
    # Sub-grid area: width * height.
    # We need to estimate noise per sub-grid.
    # Assuming uniform noise density from `generate_background_noise` logic (mean=0.5 per 100 units area)
    noise_density = 0.5 / 100.0
    
    cleaned_data = []
    for row in df_subgrid_counts_raw.iter_rows(named=True):
        # Find cell dimensions
        # We can look up in grid_cells list or just use area if uniform.
        # But cells might vary slightly? No, they are uniform splits.
        # Let's find the cell object for width/height.
        # Optimization: Create a map.
        pass
        
    # Better: Add width/height to df_subgrid_counts_raw?
    # Or just iterate grid_cells again since they align with df rows if sorted?
    # `count_defects_per_subgrid` returns rows in order of grid_cells iteration.
    
    # Let's rebuild the DF with cleaned counts.
    cleaned_rows = []
    
    # Create map for cell dimensions
    cell_dim_map = {c.sub_grid_id: (c.width, c.height) for c in grid_cells}
    
    for row in df_subgrid_counts_raw.iter_rows(named=True):
        sid = row["sub_grid_id"]
        raw_count = row["count"]
        w, h = cell_dim_map[sid]
        area = w * h
        expected_noise = area * noise_density
        clean_count = max(0, raw_count - expected_noise)
        
        # We use 'clean_count' as the 'count' for analysis
        cleaned_rows.append({
            "sub_grid_id": sid,
            "count": int(round(clean_count)), # Round to nearest int for matrix
            "raw_count": raw_count,
            "global_row": row["global_row"],
            "global_col": row["global_col"]
        })
        
    df_subgrid_counts_clean = pl.DataFrame(cleaned_rows)
    
    # Create Matrix from Cleaned Counts
    matrix = create_subgrid_matrix(df_subgrid_counts_clean)
    
    # Analyze Regions (CV) on Cleaned Data
    # Threshold: e.g., > 0 defects after cleaning (or higher)
    df_regions, stats_df, labeled_matrix = analyze_regions(matrix, df_subgrid_counts_clean, threshold=0)
    print(f"   Found {len(stats_df)} high-defect regions (on cleaned data).")
    print(stats_df)
    
    # 6. Visualization
    print("6. Visualizing Results...")
    fig, axes = plt.subplots(1, 2, figsize=(24, 10))
    
    # --- Plot 1: Original Map with Sub-grid Heatmap (Raw) & Regions (Cleaned) ---
    ax1 = axes[0]
    ax1.set_title(f"Original Map: Sub-grid Heatmap (Raw) & Regions (Detected on Cleaned)")
    
    # Draw Defects (faint)
    ax1.scatter(df_defects["x"], df_defects["y"], s=1, c='gray', alpha=0.2, label="Defects")
    
    # Draw Sub-grids colored by RAW count
    max_count_raw = df_subgrid_counts_clean["raw_count"].max()
    norm_raw = mcolors.Normalize(vmin=0, vmax=max_count_raw)
    cmap = cm.Reds
    
    # Maps
    raw_count_map = {row["sub_grid_id"]: row["raw_count"] for row in df_subgrid_counts_clean.iter_rows(named=True)}
    clean_count_map = {row["sub_grid_id"]: row["count"] for row in df_subgrid_counts_clean.iter_rows(named=True)}
    region_map = {row["sub_grid_id"]: row["region_id"] for row in df_regions.iter_rows(named=True)}
    
    for cell in grid_cells:
        cnt = raw_count_map.get(cell.sub_grid_id, 0)
        color = cmap(norm_raw(cnt))
        
        # Draw filled rect for heatmap
        rect = plt.Rectangle((cell.origin_min_x, cell.origin_min_y), cell.width, cell.height,
                             linewidth=0, facecolor=color, alpha=0.7)
        ax1.add_patch(rect)
        
        # Draw border (dashed)
        rect_border = plt.Rectangle((cell.origin_min_x, cell.origin_min_y), cell.width, cell.height,
                             linewidth=0.5, edgecolor='black', linestyle=':', facecolor='none', alpha=0.3)
        ax1.add_patch(rect_border)
        
        # Label sub-grid
        short_sub_id = cell.sub_grid_id.split("-")[-1]
        ax1.text(cell.origin_center_x, cell.origin_center_y, short_sub_id, 
                 ha='center', va='center', fontsize=4, color='black', alpha=0.3)
        
        # Highlight Region (Detected on Cleaned Data)
        rid = region_map.get(cell.sub_grid_id, 0)
        if rid > 0:
            rect_reg = plt.Rectangle((cell.origin_min_x, cell.origin_min_y), cell.width, cell.height,
                                     linewidth=1.5, edgecolor='blue', facecolor='none')
            ax1.add_patch(rect_reg)
            ax1.text(cell.origin_min_x, cell.origin_min_y, str(rid), 
                     color='blue', fontsize=6, fontweight='bold', ha='left', va='bottom')

    # Draw Panels (solid)
    panel_bounds = df_panels.group_by("panel_id").agg([
        pl.col("x").min().alias("min_x"),
        pl.col("x").max().alias("max_x"),
        pl.col("y").min().alias("min_y"),
        pl.col("y").max().alias("max_y"),
        pl.col("sequence_no").first().alias("seq")
    ])
    
    for row in panel_bounds.iter_rows(named=True):
        min_x, max_x, min_y, max_y = row["min_x"], row["max_x"], row["min_y"], row["max_y"]
        rect = plt.Rectangle((min_x, min_y), max_x - min_x, max_y - min_y,
                             linewidth=2, edgecolor='black', facecolor='none')
        ax1.add_patch(rect)
        
        label = get_panel_label(row["seq"])
        ax1.text(min_x + 10, max_y - 20, label, fontsize=12, fontweight='bold', color='black')

    ax1.set_xlim(-900, 900)
    ax1.set_ylim(-700, 700)
    plt.colorbar(cm.ScalarMappable(norm=norm_raw, cmap=cmap), ax=ax1, label="Raw Defect Count")

    # --- Plot 2: Cleaned Map (Sub-grid based, Noise Removed) ---
    ax2 = axes[1]
    ax2.set_title("Cleaned Map: Sub-grid Heatmap (Cleaned) & Regions")
    
    max_clean_count = df_subgrid_counts_clean["count"].max()
    norm_clean = mcolors.Normalize(vmin=0, vmax=max_clean_count)
    
    # Draw Sub-grids on Cleaned Map
    for cell in grid_cells:
        clean_cnt = clean_count_map.get(cell.sub_grid_id, 0)
        color = cmap(norm_clean(clean_cnt))
        
        # Calculate corner from center (clean coords)
        min_x = cell.clean_x - cell.width / 2
        min_y = cell.clean_y - cell.height / 2
        
        # Fill
        rect = plt.Rectangle((min_x, min_y), cell.width, cell.height,
                             linewidth=0, facecolor=color, alpha=0.7)
        ax2.add_patch(rect)
        
        # Border (dashed)
        rect_border = plt.Rectangle((min_x, min_y), cell.width, cell.height,
                             linewidth=0.5, edgecolor='black', linestyle=':', facecolor='none', alpha=0.3)
        ax2.add_patch(rect_border)
        
        # Label
        short_sub_id = cell.sub_grid_id.split("-")[-1]
        ax2.text(cell.clean_x, cell.clean_y, short_sub_id, 
                 ha='center', va='center', fontsize=4, color='black', alpha=0.3)

    # Draw Region Boxes on Cleaned Map
    # Aggregate clean bounds for regions
    region_bounds = {}
    for cell in grid_cells:
        rid = region_map.get(cell.sub_grid_id, 0)
        if rid > 0:
            min_x = cell.clean_x - cell.width / 2
            max_x = cell.clean_x + cell.width / 2
            min_y = cell.clean_y - cell.height / 2
            max_y = cell.clean_y + cell.height / 2
            
            if rid not in region_bounds:
                region_bounds[rid] = {"min_x": min_x, "max_x": max_x, "min_y": min_y, "max_y": max_y}
            else:
                region_bounds[rid]["min_x"] = min(region_bounds[rid]["min_x"], min_x)
                region_bounds[rid]["max_x"] = max(region_bounds[rid]["max_x"], max_x)
                region_bounds[rid]["min_y"] = min(region_bounds[rid]["min_y"], min_y)
                region_bounds[rid]["max_y"] = max(region_bounds[rid]["max_y"], max_y)
                
    for rid, bounds in region_bounds.items():
        min_x, max_x, min_y, max_y = bounds["min_x"], bounds["max_x"], bounds["min_y"], bounds["max_y"]
        
        rect = plt.Rectangle((min_x, min_y), max_x - min_x, max_y - min_y,
                             linewidth=1.5, edgecolor='blue', facecolor='none')
        ax2.add_patch(rect)
        ax2.text(min_x, min_y, str(rid), color='blue', fontsize=8, fontweight='bold', ha='left', va='bottom')

    # Draw Panels (solid) on Cleaned Map
    panel_clean_bounds = {}
    for cell in grid_cells:
        pid = cell.panel_id
        min_x = cell.clean_x - cell.width / 2
        max_x = cell.clean_x + cell.width / 2
        min_y = cell.clean_y - cell.height / 2
        max_y = cell.clean_y + cell.height / 2
        
        if pid not in panel_clean_bounds:
            panel_clean_bounds[pid] = {"min_x": min_x, "max_x": max_x, "min_y": min_y, "max_y": max_y}
        else:
            panel_clean_bounds[pid]["min_x"] = min(panel_clean_bounds[pid]["min_x"], min_x)
            panel_clean_bounds[pid]["max_x"] = max(panel_clean_bounds[pid]["max_x"], max_x)
            panel_clean_bounds[pid]["min_y"] = min(panel_clean_bounds[pid]["min_y"], min_y)
            panel_clean_bounds[pid]["max_y"] = max(panel_clean_bounds[pid]["max_y"], max_y)
            
    pid_to_seq = {row["panel_id"]: row["sequence_no"] for row in df_panels.select(["panel_id", "sequence_no"]).unique().iter_rows(named=True)}
    
    for pid, bounds in panel_clean_bounds.items():
        min_x, max_x, min_y, max_y = bounds["min_x"], bounds["max_x"], bounds["min_y"], bounds["max_y"]
        
        rect = plt.Rectangle((min_x, min_y), max_x - min_x, max_y - min_y,
                             linewidth=1.5, edgecolor='black', facecolor='none')
        ax2.add_patch(rect)
        
        seq = pid_to_seq.get(pid, 0)
        ax2.text(min_x + 10, max_y - 20, get_panel_label(seq), fontsize=10, fontweight='bold', color='black')
    
    # Calculate limits
    if panel_clean_bounds:
        all_min_x = min(b["min_x"] for b in panel_clean_bounds.values())
        all_max_x = max(b["max_x"] for b in panel_clean_bounds.values())
        all_min_y = min(b["min_y"] for b in panel_clean_bounds.values())
        all_max_y = max(b["max_y"] for b in panel_clean_bounds.values())
    else:
        all_min_x, all_max_x, all_min_y, all_max_y = -900, 900, -700, 700

    ax2.set_xlim(all_min_x - 50, all_max_x + 50)
    ax2.set_ylim(all_min_y - 50, all_max_y + 50)
    plt.colorbar(cm.ScalarMappable(norm=norm_clean, cmap=cmap), ax=ax2, label="Cleaned Defect Count")

    plt.tight_layout()
    plt.savefig("final_result.png")
    print("Saved final_result.png")
    
    # 7. Generate Report
    print("7. Generating Report...")
    with open("final_report.md", "w") as f:
        f.write("# Grid Map Analysis Final Report\n\n")
        f.write("## Overview\n")
        f.write("This report summarizes the analysis of defect patterns on the panel grid. ")
        f.write("The analysis includes gap removal, sub-grid defect counting, noise removal, and region detection.\n")
        f.write("Regions are detected based on the **Cleaned Defect Counts** (after noise removal).\n\n")
        
        f.write("## Visualization\n")
        f.write("![Final Result](final_result.png)\n\n")
        f.write("- **Left**: Original Map showing Raw Defect Counts. Blue boxes indicate regions detected on the *Cleaned* data.\n")
        f.write("- **Right**: Cleaned Map showing Cleaned Defect Counts (Noise Removed). Blue boxes indicate the same regions.\n\n")
        
        f.write("## Detected Regions (High Defect Density)\n")
        f.write("| Region ID | Total Defects (Cleaned) | Sub-grid Count | Avg Defects/Grid | Sub-grids |\n")
        f.write("|---|---|---|---|---|\n")
        
        if not stats_df.is_empty():
            for row in stats_df.iter_rows(named=True):
                sub_grids = str(row["sub_grids"])
                if len(sub_grids) > 50:
                    sub_grids = sub_grids[:47] + "..."
                
                f.write(f"| {row['region_id']} | {row['total_defects']} | {row['sub_grid_count']} | {row['avg_defects_per_grid']:.2f} | {sub_grids} |\n")
        else:
            f.write("| None | - | - | - | - |\n")
            
    print("Saved final_report.md")

if __name__ == "__main__":
    main()
