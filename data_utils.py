import polars as pl

def extract_panel_addr(
    df: pl.DataFrame, 
    panel_id_col: str, 
    product_id_col: str, 
    alias: str = "panel_addr"
) -> pl.DataFrame:
    """
    Extracts the panel address suffix from the panel_id column.
    
    Logic:
        Suffix = panel_id[len(product_id):]
        
    Args:
        df: Input DataFrame.
        panel_id_col: Column name containing the full panel specific ID (e.g. 'ABC01').
        product_id_col: Column name containing the product ID prefix (e.g. 'ABC').
        alias: Name of the new column to be created (default 'panel_addr').
        
    Returns:
        DataFrame with the new column attached.
    """
    
    # Calculate length of the prefix
    # Note: slice in polars takes (offset, length). If length is None, until end.
    # However, `str.slice` takes offset and length. 
    # To slice until end dynamically based on another column's length is tricky in some versions using simple slice.
    # But `str.slice(offset)` (only one arg) might not be standard in all Polars versions/expression APIs depending on binding.
    # Standard Polars `str.slice(offset, length)`.
    # A cleaner way: `str.replace(prefix, "")` if strict prefix? 
    # But user said "panel_id composed of product_id + panel_addr".
    # Assuming exact prefix.
    # `str.strip_prefix` exists in newer Polars.
    
    # Let's try strip_prefix interaction if columns are involved? 
    # Expression based strip_prefix might typically take a literal.
    
    # Generic solution:
    # 1. Get length of product_id.
    # 2. Slice panel_id from that length.
    
    return df.with_columns(
        pl.col(panel_id_col)
        .str.slice(pl.col(product_id_col).str.len_chars())
        .alias(alias)
    )
