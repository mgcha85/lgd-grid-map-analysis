import polars as pl
from database import init_db, SessionLocal, Panel, AnalysisConfig, Recipient
import os

def seed_data():
    db = SessionLocal()
    
    # 1. Seed Panels from Parquet
    parquet_path = "data/panels.parquet"
    if os.path.exists(parquet_path):
        print(f"Loading panels from {parquet_path}...")
        df_panels = pl.read_parquet(parquet_path)
        
        # Calculate width/height (assuming uniform for now based on mock generation)
        # In generate_mock_data, width/height are derived. 
        # Let's infer from min/max if available or just use the generated logic.
        # Actually, the parquet only has x, y (center? no, corners).
        # Wait, generate_mock_data saves 4 corners per panel.
        # We need to aggregate to get center and dimensions for the DB 'Panel' entity.
        
        # Group by panel_id to get bounds
        panel_bounds = df_panels.group_by("panel_id").agg([
            pl.col("x").min().alias("min_x"),
            pl.col("x").max().alias("max_x"),
            pl.col("y").min().alias("min_y"),
            pl.col("y").max().alias("max_y"),
            pl.col("sequence_no").first().alias("seq")
        ])
        
        for row in panel_bounds.iter_rows(named=True):
            pid = row["panel_id"]
            # Check if exists
            if db.query(Panel).filter(Panel.panel_id == pid).first():
                continue
                
            width = row["max_x"] - row["min_x"]
            height = row["max_y"] - row["min_y"]
            center_x = (row["min_x"] + row["max_x"]) / 2
            center_y = (row["min_y"] + row["max_y"]) / 2
            
            panel = Panel(
                panel_id=pid,
                sequence_no=row["seq"],
                x=center_x,
                y=center_y,
                width=width,
                height=height
            )
            db.add(panel)
        
        print("Panels seeded.")
    else:
        print(f"Warning: {parquet_path} not found. Skipping panel seeding.")

    # 2. Seed Config
    defaults = {
        "grid_split_x": "3",
        "grid_split_y": "3",
        "defect_threshold": "2",
        "map_min_x": "-900",
        "map_max_x": "900",
        "map_min_y": "-700",
        "map_max_y": "700"
    }
    
    for key, val in defaults.items():
        if not db.query(AnalysisConfig).filter(AnalysisConfig.key == key).first():
            db.add(AnalysisConfig(key=key, value=val))
    print("Config seeded.")

    # 3. Seed Recipient (Dummy)
    if not db.query(Recipient).first():
        db.add(Recipient(email="user@example.com", name="Admin"))
        print("Dummy recipient seeded.")
        
    db.commit()
    db.close()

if __name__ == "__main__":
    print("Initializing Database...")
    init_db()
    seed_data()
    print("Database Initialized.")
