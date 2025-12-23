# Grid Map Analysis Final Report

## Overview
This report summarizes the analysis of defect patterns on the panel grid. The analysis includes gap removal, sub-grid defect counting, noise removal, and region detection.
Regions are detected based on the **Cleaned Defect Counts** (after noise removal).

## Visualization
![Final Result](final_result.png)

- **Left**: Original Map showing Raw Defect Counts. Blue boxes indicate regions detected on the *Cleaned* data.
- **Right**: Cleaned Map showing Cleaned Defect Counts (Noise Removed). Blue boxes indicate the same regions.

## Detected Regions (High Defect Density)
| Region ID | Total Defects (Cleaned) | Sub-grid Count | Avg Defects/Grid | Sub-grids |
|---|---|---|---|---|
| 7 | 85 | 4 | 21.25 | ['D3-a1', 'D3-b1', 'D3-b2', 'D3-b3'] |
| 9 | 80 | 2 | 40.00 | ['G4-b3', 'G5-a1'] |
| 2 | 41 | 1 | 41.00 | ['H1-c1'] |
| 1 | 38 | 1 | 38.00 | ['F1-c1'] |
| 12 | 34 | 1 | 34.00 | ['F5-c3'] |
| 5 | 29 | 1 | 29.00 | ['F2-a2'] |
| 3 | 26 | 1 | 26.00 | ['D1-c2'] |
| 8 | 24 | 1 | 24.00 | ['H3-b1'] |
| 4 | 22 | 1 | 22.00 | ['C2-b1'] |
| 6 | 22 | 1 | 22.00 | ['A2-c3'] |
| 10 | 19 | 1 | 19.00 | ['C5-a1'] |
| 11 | 2 | 1 | 2.00 | ['D5-b3'] |
