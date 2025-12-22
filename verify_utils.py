import polars as pl
from data_utils import extract_panel_addr

def verify_extraction():
    # Setup Mock Data
    data = {
        "product_id": ["PROD_A", "PROD_A", "X", "TEST_LONG_NAME"],
        "panel_id": ["PROD_A01", "PROD_B99", "XA1", "TEST_LONG_NAME_ADDR_1"] # PROD_B99 is intentional mismatch to test slice? 
        # Wait, requirement says "panel_id composed of product_id + panel_addr".
        # If product_id="PROD_A" and panel_id="PROD_B99", logic slice(len) => slice(6) => "99".
        # The logic holds for "extracting suffix after len(product_id)".
    }
    
    df = pl.DataFrame(data)
    
    result = extract_panel_addr(df, "panel_id", "product_id", "addr")
    
    print("Result:")
    print(result)
    
    # Assertions
    # 1. PROD_A (6 chars) -> PROD_A01 -> "01"
    row0 = result.row(0, named=True)
    assert row0["addr"] == "01", f"Expected '01', got '{row0['addr']}'"
    
    # 2. PROD_A (6 chars) -> PROD_B99 -> "B99" ? No, PROD_B is 6 chars?
    # No, product_id is "PROD_A" (length 6).
    # panel_id is "PROD_B99".
    # Slice at 6: "P", "R", "O", "D", "_", "B" -> 99?
    # "PROD_B" is index 0-5. 
    # Wait. "PROD_A" is 6 chars. 
    # "PROD_B99" is 8 chars.
    # Slice(6) -> chars at 6,7 -> "99". 
    # Yes.
    row1 = result.row(1, named=True)
    assert row1["addr"] == "99", f"Expected '99', got '{row1['addr']}'"
    
    # 3. X (1 char) -> XA1 -> "A1"
    row2 = result.row(2, named=True)
    assert row2["addr"] == "A1", f"Expected 'A1', got '{row2['addr']}'"
    
    # 4. Long
    row3 = result.row(3, named=True)
    # len("TEST_LONG_NAME") = 14
    # Suffix "_ADDR_1"
    assert row3["addr"] == "_ADDR_1", f"Expected '_ADDR_1', got '{row3['addr']}'"
    
    print("SUCCESS: Extraction verified.")

if __name__ == "__main__":
    verify_extraction()
