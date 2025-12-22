import polars as pl
from generate_mock_data import generate_data
from gap_analysis import find_gaps, remove_gaps
from grid_mapping import generate_grid_cells, GridCell

def verify_grid_mapping():
    # 1. Setup Data
    generate_data() # standard mock data
    df_panels = pl.read_parquet("panels.parquet")
    
    # 2. Gap analysis
    shift_x, shift_y = find_gaps(df_panels)
    
    # 3. Calculate max clean dimensions
    # Original max: ~320x120
    # Clean max: 300x100
    
    max_x_clean = 300.0
    max_y_clean = 100.0
    
    # 4. Generate Grid
    # Test different sizes
    # X size = 40.0
    # Y size = 20.0
    
    n_split_x = 3
    n_split_y = 3
    
    cells = generate_grid_cells(
        n_split_x=n_split_x,
        n_split_y=n_split_y,
        shift_map_x=shift_x, 
        shift_map_y=shift_y, 
        panel_df=df_panels
    )
    
    print(f"Generated {len(cells)} grid cells.")
    
    # 5. Verification
    
    # Panel Size 100x50. Split 3x3.
    # Cell Size X = 33.333
    # Cell Size Y = 16.666
    
    # Check P_0_0 (0,0) -> First cell (a1)
    # Origin X = 0 + 16.66 = 16.66
    # Origin Y = 0 + 8.33 = 8.33
    # P_0_0 has no shift (Shift 0,0).
    # So clean_x = 16.66, clean_y = 8.33.
    
    cell_0 = next((c for c in cells if abs(c.clean_x - 16.66)<1 and abs(c.clean_y - 8.33)<1), None)
    
    if cell_0:
        print(f"Check Cell P_0_0a1 (approx 16.66, 8.33): {cell_0}")
        assert abs(cell_0.origin_x - 16.66) < 1.0
        assert abs(cell_0.origin_y - 8.33) < 1.0
        assert cell_0.panel_id == "P_0_0"
        assert cell_0.sub_grid_id.endswith("a1")
    else:
        print("Cell P_0_0a1 not found!")
        exit(1)
        
    # Check shifted cell P_1_1 (Row 1, Col 1).
    # Panel Origin (110, 70). Side 100x50.
    # We want middle cell (b2).
    # Center relative to panel: 50, 25.
    # Origin X = 110 + 50 = 160.
    # Origin Y = 70 + 25 = 95.
    
    # Shift X for Col 1 is -10. Clean X = 150.
    # Shift Y for Row 1 is -20. Clean Y = 75.
    
    cell_shifted = next((c for c in cells if abs(c.clean_x - 150.0)<1 and abs(c.clean_y - 75.0)<1), None)
    if cell_shifted:
        print(f"Check Cell P_1_1b2 (Clean 150, 75): {cell_shifted}")
        assert abs(cell_shifted.origin_x - 160.0) < 1.0
        assert abs(cell_shifted.origin_y - 95.0) < 1.0
        assert cell_shifted.panel_id == "P_1_1"
        assert cell_shifted.sub_grid_id.endswith("b2")
    else:
        print("Cell P_1_1b2 not found!")
        exit(1)
        
        # Check Sub-ID
        # P_1_1 Start X = 110 (Shift +10, Clean 100?). No.
        # Original P_1_1 Bounds:
        # X: Panel Width 100. Col 1 -> 110 to 210. (Gap 10).
        # Y: Panel Height 50. Row 1 -> 70 to 120. (Gap 20).
        
        # This point Origin (150, 110).
        # Relative X = 150 - 110 = 40.
        # Relative Y = 110 - 70 = 40.
        
        # Grid X Size = 40.
        # Col Idx = 40 // 40 = 1. -> 'b'
        # Grid Y Size = 20.
        # Row Idx = 40 // 20 = 2. -> '3' (1-based index 0->1, 1->2, 2->3)
        
        # Expected ID: P_1_1 + 'b' + '3' = P_1_1b3
        
        assert cell_shifted.sub_grid_id == "P_1_1b3", f"Expected P_1_1b3, got {cell_shifted.sub_grid_id}"
        
    # Check bounds of splitting
    # Panel Size 100x50. Grid 40x20.
    # X splits: 0-40(a), 40-80(b), 80-100(c). (Indices 0, 1, 2)
    # Y splits: 0-20(1), 20-40(2), 40-50(3). (Indices 0, 1, 2)
    # Total cells per panel should look at coverage.
    # Center points:
    # X: 20(a), 60(b), 100(edge? no 80-120 center is 100).
    # If global grid aligns with panel:
    # 0, 40, 80.
    # Centers: 20, 60, 100.
    # Panel is 0-100.
    # Center 20 -> idx 0 (a).
    # Center 60 -> idx 1 (b).
    # Center 100 -> idx 2 (c). But 100 is ON the border of 100.
    # Panel max_x is usually exclusive for containment? 
    # Or inclusive?
    # Our usage: origin_x <= p_max_x. 100 <= 100.
    # So idx 2 (c) exists if 100 is included. 
    # But wait, 100 would be the start of next cell?
    # Grid: [0,40), [40,80), [80,120).
    # Center 100 is in [80,120).
    # If panel ends at 100, checking center 100 (which is edge).
    # Is center 100 inside 0-100? Yes.
    # So we expect 3 cols (a,b,c).
    
    # Check count of cells for P_0_0
    cells_p00 = [c for c in cells if c.panel_id == "P_0_0"]
    print(f"P_0_0 Cell Count: {len(cells_p00)}")
    # Y: 50. Grid 20.
    # Centers: 10, 30, 50.
    # 50 is on edge 0-50.
    # So 3 rows (1,2,3).
    # Total 3x3 = 9 cells?
    
    # Let's verify ids
    ids = sorted([c.sub_grid_id for c in cells_p00])
    print("P_0_0 IDs:", ids)
    # Should contain a1, a2, a3, b1, b2, b3, c1, c2, c3?
    # Check for 'c3'
    if any('c3' in x for x in ids):
        print("Found c3 - splitting covers edges")
    
    
    print("SUCCESS: Grid mapping verified.")

if __name__ == "__main__":
    verify_grid_mapping()
