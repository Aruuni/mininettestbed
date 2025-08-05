import matplotlib.pyplot as plt
import matplotlib.lines as mlines
import os, sys

plt.rcParams['text.usetex'] = True

# Setup paths
script_dir = os.path.dirname(__file__)
mymodule_dir = os.path.join(script_dir, '../..')
sys.path.append(mymodule_dir)
sys.dont_write_bytecode = True 

# Import protocol styling dictionaries
from core.plotting import (
    COLORS_LEO,
    PROTOCOLS_FRIENDLY_NAME_LEO,
    PROTOCOLS_LEO
)

# Create the legend strip figure
fig, ax = plt.subplots(figsize=(40, 1))  # very thin strip
ax.axis('off')

# Build handles with lines only (no markers)
handles = [
    mlines.Line2D(
        [], [], color=COLORS_LEO[p],
        linestyle='-', linewidth=30,
        label=PROTOCOLS_FRIENDLY_NAME_LEO[p]
    )
    for p in PROTOCOLS_LEO
]

# Add dummy invisible handles for left/right padding
padding = mlines.Line2D([], [], color='none', linestyle='None', label='')
#handles = [padding] + handles + [padding]

# Create the legend
legend = ax.legend(
    handles=handles,
    loc='center',
    bbox_to_anchor=(0.52, 0.5),  # nudge horizontally (x=0.5 is center)
    ncol=len(handles),
    columnspacing=8,
    handletextpad=0.5,
    fontsize=200,
    frameon=False,
    borderaxespad=1
)

# Save the legend-only plot
legend_fig_path = "protocol_legend_lines.pdf"
fig.savefig(legend_fig_path, bbox_inches='tight', pad_inches=0, transparent=True)

print(f"Legend saved to: {legend_fig_path}")
