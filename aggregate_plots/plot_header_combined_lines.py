import matplotlib.pyplot as plt
import matplotlib.collections as mcol
from matplotlib.lines import Line2D
from matplotlib.legend_handler import HandlerLineCollection
import os, sys
import numpy as np

plt.rcParams['text.usetex'] = True

# Setup paths (same as your script)
script_dir = os.path.dirname(__file__)
mymodule_dir = os.path.join(script_dir, '../..')
sys.path.append(mymodule_dir)
sys.dont_write_bytecode = True

# Your style dicts
from core.plotting import *
class HandlerDashedLines(HandlerLineCollection):
    """Custom handler: draws each LineCollection's segments at different vertical offsets"""
    def create_artists(self, legend, orig_handle,
                       xdescent, ydescent, width, height, fontsize, trans):
        numlines = len(orig_handle.get_segments())
        xdata, _ = self.get_xdata(legend, xdescent, ydescent,
                                  width, height, fontsize)
        lines = []
        # divide vertical space: dashed at lower, solid above
        y_positions = [(i+1)*height/(numlines+1) - ydescent
                       for i in range(numlines)]
        for i, y in enumerate(y_positions):
            ln = Line2D(xdata, [y]*len(xdata))
            self.update_prop(ln, orig_handle, legend)
            # apply style from the original collection
            ln.set_linestyle(orig_handle.get_linestyles()[i])
            ln.set_color(orig_handle.get_colors()[i])
            ln.set_linewidth(orig_handle.get_linewidths()[i])
            ln.set_transform(trans)
            lines.append(ln)
        return lines

# Build the header‐only legend
fig, ax = plt.subplots(figsize=(40, 3))
ax.axis('off')

segment = [[(0, 0)]]
handles = []
labels = []



# protocols: dashed then solid, thicker lines
for proto in PROTOCOLS_LEOEM:
    lc = mcol.LineCollection(
        segments=2 * segment,
        linestyles=['dashed', 'solid'],
        colors=[COLORS_LEO[proto]] * 2,
        linewidths=[10, 20],   
                  # thicker lines
    )
    handles.append(lc)
    labels.append(PROTOCOLS_FRIENDLY_NAME_LEO[proto])

# Optimal dashed‐only, thicker
opt = Line2D([], [], color='red',
             linestyle='dotted',
             linewidth=20)
handles.append(opt)
labels.append("Base RTT")

# right padding


# Draw legend: one row, padded edges
ax.legend(
    handles, labels,
    handler_map={mcol.LineCollection: HandlerDashedLines()},
    loc='center',
    ncol=len(handles),
    columnspacing=2,    # more space between entries
    handletextpad=1.0,
    handlelength=4,     # shrink horizontal length to 0.5× default
    handleheight=1.0,     # keep full vertical box for stacking
    fontsize=200,
    frameon=False,
)

plt.savefig(
    "protocol_legend_twoflows.pdf",
    bbox_inches='tight',
    pad_inches=0,
    transparent=True
)
print("Saved protocol_legend_combined_header.pdf")
