

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("telsam_1T(1).csv")
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
ax.bar_label(bars, labels=[str(c) if c > 0 else "" for c in counts], fontsize=18)
ax.set_xlabel("pH", fontsize=18)
ax.set_ylabel("Number of constructs with crystals", fontsize=18)
ax.set_title(f"pH of crystallization for 1TEL constructs "
             f"(n={df['protein_canonical'].nunique()} constructs, {len(df)} crystals)", fontsize=18)
ax.tick_params(axis="both", which="major", labelsize=18)
fig.tight_layout()
fig.savefig("telsam_1TEL_pH_hist.png", dpi=200)
plt.show()
