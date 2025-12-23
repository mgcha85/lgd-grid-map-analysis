import numpy as np
import polars as pl
from scipy.ndimage import label, find_objects
import matplotlib.pyplot as plt

def generate_heatmap(data_df: pl.DataFrame, x_range=(-800, 800), y_range=(-600, 600), bin_size=10):
    """
    Generates a 2D heatmap from defect coordinates.
    """
    x_bins = np.arange(x_range[0], x_range[1] + bin_size, bin_size)
    y_bins = np.arange(y_range[0], y_range[1] + bin_size, bin_size)
    
    # Filter data within range
    df_filtered = data_df.filter(
        (pl.col("x") >= x_range[0]) & (pl.col("x") <= x_range[1]) &
        (pl.col("y") >= y_range[0]) & (pl.col("y") <= y_range[1])
    )
    
    heatmap, x_edges, y_edges = np.histogram2d(
        df_filtered["x"].to_numpy(),
        df_filtered["y"].to_numpy(),
        bins=[x_bins, y_bins]
    )
    
    return heatmap, x_edges, y_edges

def generate_background_noise(shape, mean_val=2.0, std_val=0.5):
    """
    Generates a synthetic background noise map.
    """
    rng = np.random.default_rng(42)
    noise = rng.normal(mean_val, std_val, size=shape)
    return np.maximum(noise, 0) # Ensure non-negative

def remove_noise(heatmap, noise_map):
    """
    Subtracts noise from heatmap and clips negative values to 0.
    """
    cleaned = heatmap - noise_map
    return np.maximum(cleaned, 0)

def find_connected_components(heatmap, threshold=1.0):
    """
    Finds connected components in the heatmap.
    """
    # Binarize
    mask = heatmap > threshold
    
    # Label
    labeled_array, num_features = label(mask)
    
    return labeled_array, num_features

def map_points_to_components(data_df: pl.DataFrame, labeled_array, x_edges, y_edges):
    """
    Maps each point in data_df to a component ID based on the labeled_array.
    """
    x_idxs = np.digitize(data_df["x"].to_numpy(), x_edges) - 1
    y_idxs = np.digitize(data_df["y"].to_numpy(), y_edges) - 1
    
    x_idxs = np.clip(x_idxs, 0, labeled_array.shape[0] - 1)
    y_idxs = np.clip(y_idxs, 0, labeled_array.shape[1] - 1)
    
    component_ids = labeled_array[x_idxs, y_idxs]
    
    return data_df.with_columns(pl.Series("component_id", component_ids))

def calculate_original_bounds(df_with_components: pl.DataFrame):
    """
    Calculates the bounding box of each component in the ORIGINAL coordinates.
    """
    df_comps = df_with_components.filter(pl.col("component_id") > 0)
    
    if df_comps.is_empty():
        return pl.DataFrame()
        
    stats = df_comps.group_by("component_id").agg([
        pl.col("orig_x").min().alias("min_x"),
        pl.col("orig_x").max().alias("max_x"),
        pl.col("orig_y").min().alias("min_y"),
        pl.col("orig_y").max().alias("max_y"),
        pl.count("orig_x").alias("point_count")
    ]).sort("component_id")
    
    return stats

# --- Sub-grid Analysis Functions ---

def count_defects_per_subgrid(defects_df: pl.DataFrame, grid_cells: list):
    """
    Counts defects within each sub-grid cell.
    Uses 'clean_x', 'clean_y' of defects and cell bounds in clean space?
    Actually, we can use original coordinates if we have them.
    The user wants "heatmap... Reds...".
    Let's use ORIGINAL coordinates for counting since we have 'orig_x', 'orig_y' in defects
    and 'origin_min_x', 'width', 'height' in grid_cells.
    This avoids any mapping artifacts.
    """
    # We can do a spatial join or just iterate if N is small.
    # Grid cells: 40 * 9 = 360 cells. Defects: ~1000.
    # Iteration is fine.
    
    counts = {}
    
    # Pre-calculate cell bounds for faster lookup?
    # Or use polars conditional counting.
    
    # Let's add a 'sub_grid_id' to defects_df.
    # Since cells are regular in logical grid but irregular in physical space (gaps),
    # we can't just digitize easily unless we use the clean map which IS regular?
    # No, clean map removes gaps, so it's continuous.
    # Let's use clean coordinates for mapping points to cells!
    # GridCell has clean_x (center).
    # We need clean bounds.
    # Assuming clean map is continuous and regular?
    # remove_gaps shifts things.
    # If we use clean coordinates, we can digitize.
    
    # But wait, grid_cells are generated from panel bounds.
    # Let's trust the clean coordinates in GridCell.
    # We need the edges.
    
    # Alternative: Just use the original bounds in GridCell.
    # For each cell, filter defects in its box.
    
    cell_counts = []
    
    # This is O(N_cells * N_points) -> 360 * 1000 = 360,000 ops. Fast enough.
    # But Polars filter is faster.
    
    # Let's try to do it efficiently.
    # We can assign each defect to a panel first (using panel_id if available or bounds).
    # Then within panel, assign to sub-grid.
    
    # Do we have panel_id in defects? No.
    # But we can spatial join.
    
    # Let's use the clean coordinates approach if possible, but original is safer for "truth".
    
    # Let's iterate cells and count.
    for cell in grid_cells:
        min_x = cell.origin_min_x
        max_x = min_x + cell.width
        min_y = cell.origin_min_y
        max_y = min_y + cell.height
        
        count = defects_df.filter(
            (pl.col("orig_x") >= min_x) & (pl.col("orig_x") < max_x) &
            (pl.col("orig_y") >= min_y) & (pl.col("orig_y") < max_y)
        ).height
        
        cell_counts.append({
            "sub_grid_id": cell.sub_grid_id,
            "count": count,
            "global_row": cell.global_row,
            "global_col": cell.global_col
        })
        
    return pl.DataFrame(cell_counts)

def create_subgrid_matrix(cell_counts_df: pl.DataFrame):
    """
    Creates a 2D matrix of defect counts.
    """
    max_row = cell_counts_df["global_row"].max()
    max_col = cell_counts_df["global_col"].max()
    
    matrix = np.zeros((max_row + 1, max_col + 1), dtype=int)
    
    for row in cell_counts_df.iter_rows(named=True):
        r = row["global_row"]
        c = row["global_col"]
        cnt = row["count"]
        matrix[r, c] = cnt
        
    return matrix

def analyze_regions(matrix, cell_counts_df: pl.DataFrame, threshold=0):
    """
    Finds connected components of sub-grids with defects > threshold.
    Returns a DataFrame with region statistics.
    """
    mask = matrix > threshold
    # 8-connectivity (diagonals included)
    structure = np.ones((3, 3), dtype=int)
    labeled_array, num_features = label(mask, structure=structure)
    
    # Map back to sub-grids
    # We need to assign region_id to each sub-grid in cell_counts_df
    
    region_ids = []
    for row in cell_counts_df.iter_rows(named=True):
        r = row["global_row"]
        c = row["global_col"]
        region_ids.append(labeled_array[r, c])
        
    df_with_regions = cell_counts_df.with_columns(pl.Series("region_id", region_ids))
    
    # Aggregate stats
    stats = df_with_regions.filter(pl.col("region_id") > 0).group_by("region_id").agg([
        pl.col("sub_grid_id").alias("sub_grids"),
        pl.col("count").sum().alias("total_defects"),
        pl.count("sub_grid_id").alias("sub_grid_count"),
        pl.col("count").mean().alias("avg_defects_per_grid")
    ]).sort("total_defects", descending=True)
    
    return df_with_regions, stats, labeled_array
