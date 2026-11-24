import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import filedialog

# Open a file dialog to select the CSV
root = tk.Tk()
root.withdraw()  # Hides the blank extra tkinter window
root.attributes("-topmost", True)  # Force the file picker to the front
csv_path = filedialog.askopenfilename(
    title="Select the CSV file",
    filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])

if not csv_path:
    raise SystemExit("No file selected.")

root.destroy()  # Clean up tkinter before Matplotlib starts

plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = ["Aptos", "Arial", "Helvetica", "Liberation Sans", "DejaVu Sans"]

df = pd.read_csv(csv_path)
df = df.dropna(subset=["pH", "protein_canonical"])  # drop rows with missing pH or protein_canonical

# Same 20 equal-width bins that ax.hist(bins=20) was using
bins = np.linspace(df["pH"].min(), df["pH"].max(), 21)
df["bin"] = pd.cut(df["pH"], bins=bins, include_lowest=True)

# Number of unique constructs with at least one crystal in each bin
counts = df.groupby("bin", observed=False)["protein_canonical"].nunique().values

centers = (bins[:-1] + bins[1:]) / 2
widths = np.diff(bins)

fig, ax = plt.subplots(figsize=(8, 5))
bars = ax.bar(centers, counts, width=widths, edgecolor="black", color="C0")
ax.bar_label(bars, labels=[str(c) if c > 0 else "" for c in counts], fontsize=18, label_type="edge", padding=3)
# ax.set_xlabel("pH", fontsize=24)
# ax.set_ylabel("Number of constructs with crystals", fontsize=24)
# ax.set_title(f"pH of crystallization for 1TEL constructs "
           #  f"(n={df['protein_canonical'].nunique()} constructs, {len(df)} crystals)", fontsize=24)
ax.tick_params(axis="both", which="major", labelsize=18)
ax.tick_params(axis="both", which="major", labelsize=18)
ax.margins(y=0.1)
fig.tight_layout()
fig.savefig("telsam_1TEL_pH_hist.png", dpi=200)
plt.show()
