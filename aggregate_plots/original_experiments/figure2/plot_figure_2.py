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
HOME_DIR = "/home/mihai"

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

def plot_one(QMULT, RUN):
   # Plot congestion window, or sending rate
   ROOT_PATH = "%s/mininettestbed/nooffload/results_fairness_intra_rtt_async/fifo" % HOME_DIR
   BW = 100
   DELAY = 100
   SCALE = 'linear'
   LINEWIDTH = 1
   FIGSIZE = (4, 3)
   COLOR = {'cubic': '#0C5DA5',
             'orca': '#00B945',
             'bbr3': '#FF9500',
             'bbr': '#FF2C01',
             'sage': '#845B97',
             'pcc': '#686868',
             }
   LINESTYLE = 'dashed'
   XLIM = [0,175]

   PROTOCOLS = ['cubic', 'orca', 'bbr3', 'bbr', 'sage', 'pcc']

   BDP_IN_BYTES = int(BW * (2 ** 20) * 2 * DELAY * (10 ** -3) / 8)
   BDP_IN_PKTS = BDP_IN_BYTES / 1500

   PROTOCOL_DATA = {'cubic': {'x1': None, 'y1': None,'x2': None, 'y2': None},
                    'orca': {'x1': None, 'y1': None,'x2': None, 'y2': None},
                    'bbr3': {'x1': None, 'y1': None,'x2': None, 'y2': None},
                    'bbr': {'x1': None, 'y1': None,'x2': None, 'y2': None},
                    'sage': {'x1': None, 'y1': None,'x2': None, 'y2': None},
                    'pcc': {'x1': None, 'y1': None,'x2': None, 'y2': None},
                    }
   # Get the data:
   for protocol in PROTOCOLS:
      PATH = ROOT_PATH + '/Dumbell_%smbit_%sms_%spkts_0loss_2flows_22tcpbuf_%s/run%s' % (BW, DELAY, int(QMULT * BDP_IN_PKTS), protocol, RUN)
      if protocol != 'aurora':
         if os.path.exists(PATH + '/c1_ss.csv') and os.path.exists(PATH + '/c2_ss.csv'):
            sender1 = pd.read_csv(PATH + '/c1_ss.csv', names=['time', 'rtt', 'cwnd', 'minrtt'], header=None)
            sender2 = pd.read_csv(PATH + '/c2_ss.csv', names=['time', 'rtt', 'cwnd', 'minrtt'], header=None)
           
            sender1 = sender1.drop(index=0)
            sender2 = sender2.drop(index=0)

            sender1 = sender1[['time', 'cwnd']]
            sender2 = sender2[['time', 'cwnd']]

            sender1['time'] = sender1['time'].astype(float)
            sender2['time'] = sender2['time'].astype(float)

            min_time1 = sender1['time'].min()
            min_time2 = sender2['time'].min()

            sender1['time'] = sender1['time'] - min_time1
            sender2['time'] = sender2['time'] - min_time2


            sender1['time'] = sender1['time'].apply(lambda x: float(x))
            sender2['time'] = sender2['time'].apply(lambda x: float(x))

         else:
            print("Folder %s not found" % (PATH))
      else:
         if os.path.exists(PATH + '/csvs/c1.csv') and os.path.exists(PATH + '/csvs/c2.csv'):
            sender1 = pd.read_csv(PATH + '/csvs/c1.csv').reset_index(drop=True)
            sender2 = pd.read_csv(PATH + '/csvs/c2.csv').reset_index(drop=True)
            
            sender1 = sender1[['time', 'bandwidth']]
            sender2 = sender2[['time', 'bandwidth']]

            sender1['time'] = sender1['time'].apply(lambda x: float(x))
            sender2['time'] = sender2['time'].apply(lambda x: float(x))

            sender1['bandwidth'] = sender1['bandwidth'].ewm(alpha=0.5).mean()
            sender2['bandwidth'] = sender2['bandwidth'].ewm(alpha=0.5).mean()


      c1 = sender1
      c2 = sender2



      x1 = c1['time']
      x2 = c2['time']


      if protocol != 'aurora':
         y1 = c1['cwnd']
         y2 = c2['cwnd']
         if protocol != 'aurora':
            y1_2 = c1['cwnd'].mean()
            y2_2 = c2['cwnd'].mean()


      else:
         y1 = c1['bandwidth']
         y2 = c2['bandwidth']
      PROTOCOL_DATA[protocol]['x1'] = x1
      PROTOCOL_DATA[protocol]['x2'] = x2

      PROTOCOL_DATA[protocol]['y1'] = y1
      PROTOCOL_DATA[protocol]['y2'] = y2


   fig, axes = plt.subplots(nrows=len(PROTOCOLS), ncols=1, figsize=FIGSIZE, sharex=True)
   # get the max vlue for ylim
   max_cubic_y = max(PROTOCOL_DATA['cubic']['y1'].max(), PROTOCOL_DATA['cubic']['y2'].max())
   max_orca_y = max(PROTOCOL_DATA['orca']['y1'].max(), PROTOCOL_DATA['orca']['y2'].max())
   max_bbr_y = max(PROTOCOL_DATA['bbr']['y1'].max(), PROTOCOL_DATA['bbr']['y2'].max())
   max_sage_y = max(PROTOCOL_DATA['sage']['y1'].max(), PROTOCOL_DATA['sage']['y2'].max())
   max_pcc_y = max(PROTOCOL_DATA['pcc']['y1'].max(), PROTOCOL_DATA['pcc']['y2'].max())

   max_y =  max(max_cubic_y, max_orca_y, max_bbr_y, max_sage_y, max_pcc_y)


   for i,protocol in enumerate(PROTOCOLS):
      ax = axes[i]
      flow1, = ax.plot(PROTOCOL_DATA[protocol]['x1'], PROTOCOL_DATA[protocol]['y1'], linewidth=LINEWIDTH, alpha=1,color=COLOR[protocol], label=(lambda p: 'vivace' if p == 'pcc' else p)(protocol))
      flow2, = ax.plot(PROTOCOL_DATA[protocol]['x2'], PROTOCOL_DATA[protocol]['y2'], linewidth=LINEWIDTH, alpha=0.75,color=COLOR[protocol], linestyle=LINESTYLE)
      ax.set(yscale=SCALE, xlim=XLIM)
      ax.grid()
      if protocol == 'aurora':
         ax.set(ylabel='Rate (Mbps)')
         ax.axhline(50, c='red', linestyle='dashed')
         ax.set(xlabel="time (s)")

      else:
        #ax.set(ylabel='cwnd (pkts)')
         ax.set(ylim=[0, max_y])
         redline = ax.axhline(BDP_IN_PKTS/4, c='red', linestyle='dashed')


   # Create Legend
   line = [[(0, 0)]]
   # set up the proxy artist
   linecollections = []
   for protocol in PROTOCOLS:
      styles = ['solid', 'dashed']
      colors = [COLOR[protocol],COLOR[protocol]]
      lc = mcol.LineCollection(2 * line, linestyles=styles, colors=colors)
      linecollections.append(lc)


   PROTOCOLS.append('optimal')
   fig.legend(linecollections, PROTOCOLS, handler_map={type(lc): HandlerDashedLines()},
             handlelength=1, handleheight=0.5, ncol=4, columnspacing=0.8,handletextpad=0.5, loc='upper center', bbox_to_anchor=(0.5, 0.98))

   for format in [ 'pdf']:
      plt.savefig("sending_%srtt_%sqmult_run%s.%s" % (DELAY*2, QMULT, RUN, format), dpi=1080)




if __name__ == "__main__":
   for mult,run in zip([0.2,1,4],[1,2,3]):
      plot_one(mult,run)
