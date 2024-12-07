import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.transforms import offset_copy
import scienceplots
plt.style.use('science')
import os, sys
from matplotlib.ticker import ScalarFormatter
import matplotlib
import matplotlib.collections as mcol
from matplotlib.legend_handler import HandlerLineCollection, HandlerTuple
from matplotlib.lines import Line2D
import numpy as np
import matplotlib.patches as mpatches

script_dir = os.path.dirname( __file__ )
mymodule_dir = os.path.join( script_dir, '../..')
sys.path.append( mymodule_dir )
from core.config import *


plt.rcParams['text.usetex'] = False



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
   
def plot_all_delays(QMULT):
    ROOT_PATH = f"{HOME_DIR}/cctestbed/mininet/results_fairness_intra_rtt_async/fifo"
    BW = 100
    SCALE = 'linear'
    LINEWIDTH = 1
    FIGSIZE = (12, 10)  # Adjusted figure size to accommodate subplots
    COLOR = {
        'cubic': '#0C5DA5',
        'orca': '#00B945',
        'bbr3': '#FF9500',
        'bbr': '#FF2C01',
        'sage': '#845B97',
        'pcc': '#686868',
    }
    LINESTYLE = 'dashed'

    PROTOCOLS = ['cubic', 'orca', 'bbr3', 'bbr', 'sage', 'pcc']
    DELAYS = [10, 20, 30, 40, 50, 60 , 70, 80, 90, 100]  # Adjust delay for simplicity in this example

    for DELAY in DELAYS:
        BDP_IN_BYTES = int(BW * (2 ** 20) * 2 * DELAY * (10 ** -3) / 8)
        BDP_IN_PKTS = BDP_IN_BYTES / 1500

        PROTOCOL_DATA = {protocol: {'x': [], 'y': []} for protocol in PROTOCOLS}

        # Aggregate data across 5 runs
        for RUN in range(1, 2):
            for protocol in PROTOCOLS:
                PATH = f"{ROOT_PATH}/Dumbell_{BW}mbit_{DELAY}ms_{int(QMULT * BDP_IN_PKTS)}pkts_0loss_2flows_22tcpbuf_{protocol}/run{RUN}"
                if os.path.exists(PATH + '/csvs/c1_ss.csv') and os.path.exists(PATH + '/csvs/c2_ss.csv'):
                    sender1 = pd.read_csv(PATH + '/csvs/c1_ss.csv')
                    sender2 = pd.read_csv(PATH + '/csvs/c2_ss.csv')

                    PROTOCOL_DATA[protocol]['x'].append(sender1['time'])
                    PROTOCOL_DATA[protocol]['y'].append(sender1['cwnd'])
                    PROTOCOL_DATA[protocol]['x'].append(sender2['time'])
                    PROTOCOL_DATA[protocol]['y'].append(sender2['cwnd'])

        # Create a subplot for each protocol
        fig, axes = plt.subplots(len(PROTOCOLS), 1, figsize=FIGSIZE, sharex=True)
        for ax, protocol in zip(axes, PROTOCOLS):
            all_x = pd.concat(PROTOCOL_DATA[protocol]['x'], ignore_index=True)
            all_y = pd.concat(PROTOCOL_DATA[protocol]['y'], ignore_index=True)

            avg_y = all_y.groupby(all_x).mean()

            # Plot individual runs with alternating transparency
            for i, (x, y) in enumerate(zip(PROTOCOL_DATA[protocol]['x'], PROTOCOL_DATA[protocol]['y'])):
                if i % 2 == 1:  # Second flow
                    ax.plot(x, y, linewidth=LINEWIDTH, alpha=0.3, color=COLOR[protocol])
                else:  # First flow
                    ax.plot(x, y, linewidth=LINEWIDTH, alpha=0.6, color=COLOR[protocol])

            # Plot average line
            ax.plot(avg_y.index, avg_y.values, linewidth=LINEWIDTH * 2, alpha=1, color=COLOR[protocol], label=protocol)
            ax.set(yscale=SCALE)
            ax.grid()
            ax.set_title(f"{protocol.upper()} (Delay = {DELAY} ms)")
            ax.set_ylabel("CWND (pkts)")

        # Set common x-axis label
        axes[-1].set_xlabel("Time (s)")
        plt.tight_layout()

        # Save the plot
        for format in ['pdf', 'png']:
            plt.savefig(f"cwnd_delay_{DELAY}ms_qmult_{QMULT}.{format}", dpi=300)



if __name__ == "__main__":
    for mult in [0.2, 1, 4]:
        plot_all_delays(mult)
