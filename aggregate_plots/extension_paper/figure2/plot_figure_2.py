import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.transforms import offset_copy
import scienceplots
plt.style.use('science')
import os
from matplotlib.ticker import ScalarFormatter
import matplotlib
import matplotlib.collections as mcol
from matplotlib.legend_handler import HandlerLineCollection, HandlerTuple
from matplotlib.lines import Line2D
import numpy as np
import matplotlib.patches as mpatches
import sys
plt.rcParams['text.usetex'] = False

# Global configuration: set the time range as multipliers of the delay.
# For example, (2, 4) means only data with time between delay*2 and delay*4 will be used.
GLOBAL_TIME_RANGE_MULTIPLIERS = (2, 4)

script_dir = os.path.dirname(__file__)
mymodule_dir = os.path.join(script_dir, '../../..')
sys.path.append(mymodule_dir)
from core.config import *
from core.plotting import *
COORD_KEYS = ('x1', 'y1', 'x2', 'y2')
plt.rcParams['ytick.labelsize'] = 7


def load_pacing(path):
    with open(path, 'r') as f:
        lines = f.read().splitlines()

    df = pd.DataFrame({'raw': lines})

    df['time'] = df['raw'].str.split(',').str[0].astype(float)

    df['pacing_rate'] = (
        df['raw']
          .str.extract(r'pacing_rate\s+(\d+)bps')[0]
          .astype(float)
    )

    t0 = df['time'].iloc[0]
    df['time'] = df['time'] - t0
    df['pacing_rate'] = df['pacing_rate'] / 1e6
    # 6) rename pacing_rate → bandwidth for downstream compatibility
    return df[['time','pacing_rate']].rename(columns={'pacing_rate':'bandwidth'})

class HandlerDashedLines(HandlerLineCollection):
    """
    Custom Handler for LineCollection instances.
    """
    def create_artists(self, legend, orig_handle,
                       xdescent, ydescent, width, height, fontsize, trans):
        # figure out how many lines there are
        numlines = len(orig_handle.get_segments())
        xdata, xdata_marker = self.get_xdata(legend, xdescent, ydescent,
                                             width, height, fontsize)
        leglines = []
        # divide the vertical space where the lines will go
        # into equal parts based on the number of lines
        ydata = np.full_like(xdata, height / (numlines + 1))
        # for each line, create the line at the proper location
        # and set the dash pattern
        for i in range(numlines):
            legline = Line2D(xdata, ydata * (numlines - i) - ydescent)
            self.update_prop(legline, orig_handle, legend)
            # set color, dash pattern, and linewidth to that
            # of the lines in linecollection
            try:
                color = orig_handle.get_colors()[i]
            except IndexError:
                color = orig_handle.get_colors()[0]
            try:
                dashes = orig_handle.get_dashes()[i]
            except IndexError:
                dashes = orig_handle.get_dashes()[0]
            try:
                lw = orig_handle.get_linewidths()[i]
            except IndexError:
                lw = orig_handle.get_linewidths()[0]
            if dashes[1] is not None:
                legline.set_dashes(dashes[1])
            legline.set_color(color)
            legline.set_transform(trans)
            legline.set_linewidth(lw)
            leglines.append(legline)
        return leglines

def plot_one(QMULT, RUN):
    # Plot congestion window, or sending rate
    ROOT_PATH = f"{HOME_DIR}/cctestbed/mininet/results_fairness_intra_rtt_async/fifo" 
    BW = 100
    DELAY = 40
    SCALE = 'linear'
    LINEWIDTH = 0.8
    FIGSIZE = (4, 3)

    LINESTYLE = 'dashed'
    # Compute the time slice limits based on delay and global multipliers.
    lower_time = DELAY * GLOBAL_TIME_RANGE_MULTIPLIERS[0]
    upper_time = DELAY * GLOBAL_TIME_RANGE_MULTIPLIERS[1]
    # Also use these values to set the x-axis limits.
    XLIM = [lower_time, upper_time]
    

    BDP_IN_BYTES = int(BW * (2 ** 20) * 2 * DELAY * (10 ** -3) / 8)
    BDP_IN_PKTS = BDP_IN_BYTES / 1500
    PROTOCOL_DATA = {
        proto: {k: None for k in COORD_KEYS}
        for proto in PROTOCOLS_EXTENSION
    }
    # Get the data:
    for protocol in PROTOCOLS_EXTENSION:
        PATH = f"{ROOT_PATH}/Dumbell_{BW}mbit_{DELAY}ms_{int(mult * BDP_IN_PKTS)}pkts_0loss_2flows_22tcpbuf_{protocol}/run{RUN}" 
        if protocol != 'vivace-uspace' and protocol != 'bbr3':
            p1 = f"{PATH}/csvs/c1_ss.csv" if os.path.exists(f"{PATH}/csvs/c1_ss.csv") else f"{PATH}/csvs/c1.csv"
            p2 = f"{PATH}/csvs/c2_ss.csv" if os.path.exists(f"{PATH}/csvs/c2_ss.csv") else f"{PATH}/csvs/c2.csv"

            sender1 = pd.read_csv(p1, usecols=['time','cwnd'])
            sender2 = pd.read_csv(p2, usecols=['time','cwnd'])

            sender1['time'] = sender1['time'].astype(float)
            sender2['time'] = sender2['time'].astype(float)
        else:
            if os.path.exists(f"{PATH}/csvs/c1.csv") and os.path.exists(f"{PATH}/csvs/c2.csv"):
                sender1 = pd.read_csv(f"{PATH}/csvs/c1.csv").reset_index(drop=True) if protocol == 'vivace-uspace' else load_pacing(f"{PATH}/c1_ss.csv").reset_index(drop=True)
                sender2 = pd.read_csv(f"{PATH}/csvs/c2.csv").reset_index(drop=True) if protocol == 'vivace-uspace' else load_pacing(f"{PATH}/c2_ss.csv").reset_index(drop=True)

                sender1 = sender1[['time', 'bandwidth']]
                sender2 = sender2[['time', 'bandwidth']]

                sender1['time'] = sender1['time'].astype(float)
                sender2['time'] = sender2['time'].astype(float)

                sender1['bandwidth'] = sender1['bandwidth'].ewm(alpha=0.5).mean()
                sender2['bandwidth'] = sender2['bandwidth'].ewm(alpha=0.5).mean()
        
        # Filter the data to only include rows within the desired time slice.
        sender1 = sender1[(sender1['time'] >= lower_time) & (sender1['time'] <= upper_time)]
        sender2 = sender2[(sender2['time'] >= lower_time) & (sender2['time'] <= upper_time)]
        
        c1 = sender1
        c2 = sender2

        x1 = c1['time']
        x2 = c2['time']
        # print(f"Protocol: {protocol}, x1: {c1}, x2: {x2} {c1}")
        if protocol in ('vivace-uspace','bbr3'):
            y1 = c1['bandwidth']
            y2 = c2['bandwidth']
        else:
            y1 = c1['cwnd']
            y2 = c2['cwnd']
        PROTOCOL_DATA[protocol]['x1'] = x1
        PROTOCOL_DATA[protocol]['x2'] = x2

        PROTOCOL_DATA[protocol]['y1'] = y1
        PROTOCOL_DATA[protocol]['y2'] = y2

    fig, axes = plt.subplots(nrows=len(PROTOCOLS_EXTENSION), ncols=1, figsize=FIGSIZE, sharex=True)


    for i, protocol in enumerate(PROTOCOLS_EXTENSION):
        ax = axes[i]
        flow1, = ax.plot(PROTOCOL_DATA[protocol]['x1'], PROTOCOL_DATA[protocol]['y1'],
                         linewidth=LINEWIDTH, alpha=1, color=COLORS_EXTENSION[protocol],
                         label=PROTOCOLS_FRIENDLY_NAME_EXTENSION[protocol])
        flow2, = ax.plot(PROTOCOL_DATA[protocol]['x2'], PROTOCOL_DATA[protocol]['y2'],
                         linewidth=LINEWIDTH, alpha=0.75, color=COLORS_EXTENSION[protocol], linestyle=LINESTYLE)
        ax.set(yscale=SCALE, xlim=XLIM)
        ax.grid()
        if protocol == 'vivace-uspace' or protocol == 'bbr3':
            ax.set(ylim=[0, None])
            ax.axhline(0.5 * BW, c='magenta', linestyle='dashed')
        else:
            ax.axhline(BDP_IN_PKTS/2, c='magenta', linestyle='dashed')
            ax.set(ylim=[0, None])
            if protocol == 'astraea':
                max_val = max(PROTOCOL_DATA[protocol]['y1'].max(), PROTOCOL_DATA[protocol]['y2'].max())
                ax.set(ylim=[0, max_val + 100])
    # Create Legend
    line = [[(0, 0)]]
    linecollections = []
    for protocol in PROTOCOLS_EXTENSION:
        styles = ['solid', 'dashed']
        colors = [COLORS_EXTENSION[protocol], COLORS_EXTENSION[protocol]]
        lc = mcol.LineCollection(2 * line, linestyles=styles, colors=colors)
        linecollections.append(lc)
    friendly_labels = [PROTOCOLS_FRIENDLY_NAME_EXTENSION[p] for p in PROTOCOLS_EXTENSION]
    optimal_handle = Line2D([0], [0],
                            color='magenta',
                            linestyle='dashed',
                            linewidth=LINEWIDTH)

    # append it to the same lists you already hand to the legend
    linecollections.append(optimal_handle)
    friendly_labels.append('Optimal')

    # now your existing legend call picks it up as one of the entries
    fig.legend(linecollections, friendly_labels,
            handler_map={type(lc): HandlerDashedLines()},
            handlelength=1, handleheight=0.5,
            ncol=4, columnspacing=1,
            handletextpad=0.5,
            loc='upper center', bbox_to_anchor=(0.5, 1.06))

    plt.savefig(f"sending_{DELAY*2}rtt_{QMULT}qmult_run{RUN}.pdf", dpi=1080)

if __name__ == "__main__":
    for mult, run in zip([0.2, 1, 4], [3, 3, 3]):
        plot_one(mult, run)
