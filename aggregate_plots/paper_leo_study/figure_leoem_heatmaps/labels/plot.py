import os
import sys
import matplotlib.pyplot as plt
from matplotlib import font_manager

# --- Linux Libertine font setup (unchanged) ---
libertine_reg  = "/usr/share/fonts/opentype/linux-libertine/LinLibertine_R.otf"
libertine_bold = "/usr/share/fonts/opentype/linux-libertine/LinLibertine_RB.otf"
font_manager.fontManager.addfont(libertine_reg)
font_manager.fontManager.addfont(libertine_bold)

plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif']  = ['Linux Libertine O']
plt.rcParams['font.weight'] = 'bold'
plt.rcParams['font.size']   = 40
plt.rcParams['text.usetex'] = True

# --- ensure core.plotting is importable ---
script_dir   = os.path.dirname(__file__)
mymodule_dir = os.path.abspath(os.path.join(script_dir, "../../../.."))
sys.path.append(mymodule_dir)

from core.plotting import PATHS_INFO

# --- extract & trim labels at the first ')' ---
raw_labels = [PATHS_INFO[key]['label'] for key in PATHS_INFO]
clean_labels = []
for lbl in raw_labels:
    if ')' in lbl:
        clean = lbl.split(')')[0] + ')'  # keep up to and including the first ')'
    else:
        clean = lbl
    clean_labels.append(clean.strip())

# --- plot only the labels ---
fig, ax = plt.subplots(figsize=(2, 5))

ax.set_yticks(range(len(clean_labels)))
ax.set_yticklabels(
    [rf"\textbf{{{lbl}}}" for lbl in clean_labels],
    fontsize=18
)
ax.invert_yaxis()  # match origin='upper'

# hide x-axis and all spines
ax.tick_params(axis='x', which='both', bottom=False, top=False, labelbottom=False)
for spine in ax.spines.values():
    spine.set_visible(False)
ax.margins(x=0)

plt.tight_layout(pad=0)
fig.savefig(
    "heatmap_ylabels_only_nodash.pdf",
    dpi=1080,
    bbox_inches='tight',
    pad_inches=0
)
