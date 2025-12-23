import polars as pl

def find_gaps(panel_df: pl.DataFrame):
    """
    Analyzes panel coordinates to find gaps between panel boundaries.
    
    Args:
        panel_df: DataFrame with 'PanelID', 'x', 'y'
        
    Returns:
        (shift_map_x, shift_map_y)
        Each is a DataFrame mapping ranges to a shift amount.
    """
    # 1. Determine bounding box for each panel
    bounds = panel_df.group_by("panel_id").agg([
        pl.col("x").min().alias("min_x"),
        pl.col("x").max().alias("max_x"),
        pl.col("y").min().alias("min_y"),
        pl.col("y").max().alias("max_y"),
    ])
    
    # 2. Analyze X Gaps
    # Get all unique X intervals occupied by panels
    # Sort by start position
    x_intervals = (
        bounds.select(["min_x", "max_x"])
        .unique()
        .sort("min_x")
    )
    
    # Logic:
    # Iterate through sorted intervals.
    # If Start(i) > End(i-1), there is a gap.
    # Gap size = Start(i) - End(i-1).
    # Shift for interval i = Sum of all previous gap sizes.
    
    shift_x_rows = []
    current_shift_x = 0.0
    previous_end_x = None
    
    # iterate using rows (since logic is iterative/accumulative)
    for row in x_intervals.iter_rows(named=True):
        min_x, max_x = row["min_x"], row["max_x"]
        
        if previous_end_x is not None:
            gap = min_x - previous_end_x
            if gap > 0.001: # tolerance
                current_shift_x += gap
        
        shift_x_rows.append({
            "min_val": min_x,
            "max_val": max_x,
            "shift": current_shift_x
        })
        previous_end_x = max_x
        
    shift_map_x = pl.DataFrame(shift_x_rows)
    # Ensure float types
    if not shift_map_x.is_empty():
        shift_map_x = shift_map_x.with_columns([
            pl.col("min_val").cast(pl.Float64),
            pl.col("max_val").cast(pl.Float64),
            pl.col("shift").cast(pl.Float64)
        ])
    
    # 3. Analyze Y Gaps (Same logic)
    y_intervals = (
        bounds.select(["min_y", "max_y"])
        .unique()
        .sort("min_y")
    )
    
    shift_y_rows = []
    current_shift_y = 0.0
    previous_end_y = None
    
    for row in y_intervals.iter_rows(named=True):
        min_y, max_y = row["min_y"], row["max_y"]
        
        if previous_end_y is not None:
            gap = min_y - previous_end_y
            if gap > 0.001:
                current_shift_y += gap
                
        shift_y_rows.append({
            "min_val": min_y,
            "max_val": max_y,
            "shift": current_shift_y
        })
        previous_end_y = max_y
        
    shift_map_y = pl.DataFrame(shift_y_rows)
    if not shift_map_y.is_empty():
        shift_map_y = shift_map_y.with_columns([
            pl.col("min_val").cast(pl.Float64),
            pl.col("max_val").cast(pl.Float64),
            pl.col("shift").cast(pl.Float64)
        ])
    
    return shift_map_x, shift_map_y

def filter_valid_points(data_df: pl.DataFrame, panel_df: pl.DataFrame):
    """
    Filters out data points that do not fall within the bounding box of any panel.
    Checks X and Y dimensions independently against the valid intervals defined by the panels.
    Note: This assumes panels form a grid where columns align in X and rows align in Y.
          If panels are scattered arbitrarily, checks must be against specific rectangles.
          Based on the problem description, coordinates form a table/grid.
          
    Strict check: A point must belong to a valid X-interval AND a valid Y-interval.
    """
    
    # 1. Get Bounds per panel
    # We can get unique X intervals and unique Y intervals from all panels
    bounds = panel_df.group_by("panel_id").agg([
        pl.col("x").min().alias("min_x"),
        pl.col("x").max().alias("max_x"),
        pl.col("y").min().alias("min_y"),
        pl.col("y").max().alias("max_y"),
    ])
    
    # 2. X Validation
    # Build a lookup for valid X ranges
    valid_x = bounds.select(["min_x", "max_x"]).unique().sort("min_x")
    
    # Use join_asof to find which interval a point might belong to
    # Sort data by x for join_asof
    df_sorted_x = data_df.sort("x")
    
    # We join data to valid_x intervals (keys=min_x)
    # backward strategy means we find the start of the interval <= point.x
    x_checked = df_sorted_x.join_asof(
        valid_x,
        left_on="x",
        right_on="min_x",
        strategy="backward"
    ).with_columns(
        # Check if x is also <= max_x of that interval
        (pl.col("x") <= pl.col("max_x")).fill_null(False).alias("is_valid_x")
    )
    
    # 3. Y Validation
    valid_y = bounds.select(["min_y", "max_y"]).unique().sort("min_y")
    
    # We need to sort by y now. But let's keep the is_valid_x from previous step.
    df_sorted_y = x_checked.sort("y")
    
    y_checked = df_sorted_y.join_asof(
        valid_y,
        left_on="y",
        right_on="min_y",
        strategy="backward"
    ).with_columns(
        (pl.col("y") <= pl.col("max_y")).fill_null(False).alias("is_valid_y")
    )
    
    # 4. Filter
    # Only keep points where both X and Y are valid
    df_filtered = y_checked.filter(
        pl.col("is_valid_x") & pl.col("is_valid_y")
    ).select(data_df.columns) # Clean up temporary columns
    
    return df_filtered

def remove_gaps(data_df: pl.DataFrame, shift_map_x: pl.DataFrame, shift_map_y: pl.DataFrame):
    """
    Applies the shifts to data_df to remove gaps.
    
    Args:
        data_df: DataFrame containing 'x' and 'y' columns (and others).
        shift_map_x: DataFrame with min_val, max_val, shift
        shift_map_y: DataFrame with min_val, max_val, shift
    """
    
    # Processing X
    df_sorted_x = data_df.sort("x")
    shift_x_sorted = shift_map_x.sort("min_val")
    
    # We join on 'x' vs 'min_val'. 'backward' finds the largest min_val <= x.
    # This identifies the start of the interval this x belongs to.
    df_mapped_x = df_sorted_x.join_asof(
        shift_x_sorted,
        left_on="x",
        right_on="min_val",
        strategy="backward"
    ).select(
        pl.all().exclude(["min_val", "max_val", "shift"]),
        pl.col("shift").alias("shift_x")
    )
    
    # Calculate new x
    # Note: If point is outside any known panel, shift_x might be null or incorrect.
    # Assuming valid data.
    df_res_x = df_mapped_x.with_columns(
        (pl.col("x") - pl.col("shift_x").fill_null(0.0)).alias("x")
    ).drop("shift_x")
    
    # Processing Y (on the result of X processing)
    # Re-sort by y for asof join
    df_sorted_y = df_res_x.sort("y")
    shift_y_sorted = shift_map_y.sort("min_val")
    
    df_mapped_y = df_sorted_y.join_asof(
        shift_y_sorted,
        left_on="y",
        right_on="min_val",
        strategy="backward"
    ).select(
        pl.all().exclude(["min_val", "max_val", "shift"]),
        pl.col("shift").alias("shift_y")
    )
    
    df_res_y = df_mapped_y.with_columns(
        (pl.col("y") - pl.col("shift_y").fill_null(0.0)).alias("y")
    ).drop("shift_y")
    
    return df_res_y
