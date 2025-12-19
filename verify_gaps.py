import polars as pl
import os
from generate_mock_data import generate_data
from gap_analysis import find_gaps, remove_gaps, filter_valid_points

def verify_process():
    # 1. Regenerate fresh mock data with outliers
    n_outliers = 5
    print("Generating mock data...")
    generate_data(n_outliers=n_outliers)
    
    # 2. Load data
    df_panels = pl.read_parquet("panels.parquet")
    df_defects = pl.read_parquet("defects.parquet")
    
    print(f"Initial Defect Count: {len(df_defects)}")

    # 3. Filter Outliers
    print("\nFiltering outliers...")
    df_filtered_defects = filter_valid_points(df_defects, df_panels)
    print(f"Filtered Defect Count: {len(df_filtered_defects)}")
    
    # Assert outliers removed
    n_removed = len(df_defects) - len(df_filtered_defects)
    print(f"Removed {n_removed} points (Expected {n_outliers})")
    assert n_removed == n_outliers, f"Expected to remove {n_outliers}, but removed {n_removed}"

    # 4. Find gaps
    print("\nFinding gaps...")
    shift_x, shift_y = find_gaps(df_panels)
    
    print("Shift X Map:")
    print(shift_x)
    print("Shift Y Map:")
    print(shift_y)
    
    # 5. Remove Gaps
    print("\nRemoving gaps from defects...")
    # Use filtered defects now
    df_clean_defects = remove_gaps(df_filtered_defects, shift_x, shift_y)
    
    print("\nRemoving gaps from panels (for validation)...")
    df_clean_panels = remove_gaps(df_panels, shift_x, shift_y)
    
    # 5. Validation Logic
    # Original Config:
    # 3 Cols (width 100), Gap X = 10 -> Total Width = 300 + 20 = 320
    # 2 Rows (height 50), Gap Y = 20 -> Total Height = 100 + 20 = 120
    
    # Expected Clean Config:
    # 3 Cols (width 100), Gap X = 0 -> Total Width = 300
    # 2 Rows (height 50), Gap Y = 0 -> Total Height = 100
    
    max_x_original = df_panels["x"].max()
    max_y_original = df_panels["y"].max()
    
    max_x_clean = df_clean_panels["x"].max()
    max_y_clean = df_clean_panels["y"].max()
    
    print(f"\nOriginal Max X: {max_x_original} (Expected ~320)")
    print(f"Original Max Y: {max_y_original} (Expected ~120)")
    
    print(f"Clean Max X: {max_x_clean} (Expected 300.0)")
    print(f"Clean Max Y: {max_y_clean} (Expected 100.0)")
    
    # Assertions with small tolerance
    assert abs(max_x_clean - 300.0) < 1.0, f"Max X {max_x_clean} != 300.0"
    assert abs(max_y_clean - 100.0) < 1.0, f"Max Y {max_y_clean} != 100.0"
    
    # Verify defect count remains same as filtered
    assert len(df_filtered_defects) == len(df_clean_defects), "Defect count mismatch after gap removal"
    
    # Verify defects are within new bounds
    assert df_clean_defects["x"].max() <= 300.0, "Defect X out of bounds"
    assert df_clean_defects["y"].max() <= 100.0, "Defect Y out of bounds"
    
    print("\nSUCCESS: Gap removal verification passed!")

if __name__ == "__main__":
    verify_process()
