import argparse
import pandas as pd
import numpy as np
import os
import sys

def load_xyce_csv(filepath):
    """Loads Xyce output CSV."""
    try:
        df = pd.read_csv(filepath)
        return df
    except Exception as e:
        print(f"Error loading Xyce CSV {filepath}: {e}")
        return None

def load_comsol_csv(filepath):
    """Loads COMSOL output CSV. Assumes first row is header."""
    try:
        # COMSOL often has comment lines starting with %
        df = pd.read_csv(filepath, comment='%')
        return df
    except Exception as e:
        print(f"Error loading COMSOL CSV {filepath}: {e}")
        return None

def align_data(xyce_df, comsol_df, time_col='TIME'):
    """
    Aligns Xyce and COMSOL data based on time column.
    Interpolates COMSOL data to match Xyce time steps if necessary.
    """

    # TODO: Add support for different time columns
    if time_col not in xyce_df.columns or time_col not in comsol_df.columns:
        print(f"Error: '{time_col}' column missing from one of the files.")
        return None, None
        
    # Sort by time
    xyce_df = xyce_df.sort_values(by=time_col)
    comsol_df = comsol_df.sort_values(by=time_col)
    
    # We will interpolate COMSOL to Xyce times
    target_times = xyce_df[time_col].values
    
    aligned_comsol = pd.DataFrame()
    aligned_comsol[time_col] = target_times
    
    for col in comsol_df.columns:
        if col == time_col: continue
        # TODO: Add support for different column names
        try:
             aligned_comsol[col] = np.interp(target_times, comsol_df[time_col], comsol_df[col])
        except Exception as e:
            print(f"Skipping column {col} due to interpolation error: {e}")
            
    return xyce_df, aligned_comsol

def calculate_error(xyce_df, comsol_df, mapping=None):
    """
    Calculates error between matched columns.
    mapping: dict of {xyce_col: comsol_col}
    """
    report = []
    
    if mapping is None:
        # TODO: Add support for different column names
        common_cols = set(xyce_df.columns) & set(comsol_df.columns)
        mapping = {c: c for c in common_cols if c != 'TIME'}
        
    for x_col, c_col in mapping.items():
        if x_col not in xyce_df.columns:
            print(f"Warning: {x_col} not in Xyce data")
            continue
        if c_col not in comsol_df.columns:
            print(f"Warning: {c_col} not in COMSOL data")
            continue
            
        x_val = xyce_df[x_col].values
        c_val = comsol_df[c_col].values
        
        abs_err = np.abs(x_val - c_val)
        rel_err = np.abs((x_val - c_val) / (np.where(c_val==0, 1e-9, c_val))) * 100
        
        stats = {
            'Variable': x_col,
            'COMSOL_Var': c_col,
            'Max_Abs_Error': np.max(abs_err),
            'Mean_Abs_Error': np.mean(abs_err),
            'Max_Rel_Error_%': np.max(rel_err),
            'Mean_Rel_Error_%': np.mean(rel_err)
        }
        report.append(stats)
        
    return pd.DataFrame(report)

def main():
    parser = argparse.ArgumentParser(description="Compare Xyce vs COMSOL results")
    parser.add_argument("xyce_file", help="Path to Xyce output CSV")
    parser.add_argument("comsol_file", help="Path to COMSOL output CSV")
    parser.add_argument("--output", "-o", default="benchmark_report.csv", help="Output report file")
    parser.add_argument("--map", nargs='+', help="Column mapping in format xyce_col=comsol_col")
    
    args = parser.parse_args()
    
    xyce_df = load_xyce_csv(args.xyce_file)
    comsol_df = load_comsol_csv(args.comsol_file)
    
    if xyce_df is None or comsol_df is None:
        sys.exit(1)
        
    mapping = None
    if args.map:
        mapping = {}
        for m in args.map:
            k, v = m.split('=')
            mapping[k] = v
            
    print("Aligning data...")
    xyce_aligned, comsol_aligned = align_data(xyce_df, comsol_df)
    
    if xyce_aligned is None:
        sys.exit(1)
        
    print("Calculating error...")
    report_df = calculate_error(xyce_aligned, comsol_aligned, mapping)
    
    print("\n--- Benchmark Report ---")
    print(report_df.to_string())
    
    report_df.to_csv(args.output, index=False)
    print(f"\nReport saved to {args.output}")

if __name__ == "__main__":
    main()
