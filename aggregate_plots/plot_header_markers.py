import matplotlib.pyplot as plt
import matplotlib.lines as mlines
import os, sys
script_dir = os.path.dirname(__file__)
mymodule_dir = os.path.join(script_dir, '../..')
sys.path.append(mymodule_dir)
sys.dont_write_bytecode = True 

from core.plotting import (
    COLORS_EXTENSION,
    PROTOCOLS_MARKERS_EXTENSION,
    PROTOCOLS_FRIENDLY_NAME_EXTENSION,
    PROTOCOLS_EXTENSION
)

fig, ax = plt.subplots(figsize=(40, 3))
ax.axis('off')

handles = [
    mlines.Line2D(
        [], [], color=COLORS_EXTENSION[p],
        marker=PROTOCOLS_MARKERS_EXTENSION[p],
        linestyle='None', linewidth=3.0,
        markersize=180, label=PROTOCOLS_FRIENDLY_NAME_EXTENSION[p],
        markeredgewidth=30,                          # make border thicker
    )
    for p in PROTOCOLS_EXTENSION
]


padding = mlines.Line2D([], [], color='none', linestyle='None', label='')
#handles = [padding] + handles + [padding]
legend = ax.legend(
    handles=handles,
    loc='center',
    bbox_to_anchor=(0.52, 0.5),  # nudge horizontally (x=0.5 is center)
    ncol=len(handles),
    columnspacing=6,
    handletextpad=0.5,
    fontsize=200,
    frameon=False,  # No border around the legend
    borderaxespad=1       # optional: distance from axes box
)
# Save the legend-only plot with tight bounding box
legend_fig_path = "protocol_legend_markers.pdf"
fig.savefig(legend_fig_path, bbox_inches='tight', pad_inches=0, transparent=True)

print(f"Legend saved to: {legend_fig_path}")
