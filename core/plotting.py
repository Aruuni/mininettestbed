
LINEWIDTH = 0.30
ELINEWIDTH = 0.75
CAPTHICK = ELINEWIDTH
CAPSIZE= 2

PROTOCOLS_EXTENSION = ['cubic', 'sage', 'orca', 'astraea', 'bbr3', 'vivace', 'vivace-uspace', 'bbr1']
PROTOCOLS_MARKERS_EXTENSION = {'cubic': 'x', 'orca': '+', 'bbr3': '^', 'sage': '*', 'vivace': '_', 'astraea': '2', 'vivace-uspace': '4', 'bbr1': '1', }
COLORS_EXTENSION = {'cubic': '#0C5DA5', 'orca': '#00B945', 'bbr3': '#FF9500', 'sage': '#FF2C01', 'vivace': '#845B97', 'astraea': '#686868', 'vivace-uspace': '#ADD8E6', 'bbr1': '#964B00'}

QMULTS = [0.2,1,4]
RUNS = [1, 2, 3, 4, 5]
LOSSES=[0]

def plot_points(ax, df, data, error,  marker, color, label, delay=False):
    if not df.empty:
        if delay:
            xvals = df.index * 2
        else:
            xvals = df.index
        yvals = df[data]
        yerr  = df[error]
        markers, caps, bars = ax.errorbar(
            xvals, yvals,
            yerr=yerr,
            marker=marker,
            linewidth=LINEWIDTH,
            elinewidth=ELINEWIDTH,
            capsize=CAPSIZE,
            capthick=CAPTHICK,
            color=color,
            label=label
        )
        [bar.set_alpha(0.5) for bar in bars]
        [cap.set_alpha(0.5) for cap in caps]

def plot_retrans_points(ax, df, mean_col, std_col, marker, color, label):
    if not df.empty:
        xvals = df.index
        # Convert mean retransmissions to Mbps
        yvals = df[mean_col] * 1448.0 * 8.0 / (1024.0 * 1024.0)

        # Convert both columns for two-sided error
        yerr_lower = df[[mean_col, std_col]].min(axis=1) * 1448.0 * 8.0 / (1024.0 * 1024.0)
        yerr_upper = df[std_col] * 1448.0 * 8.0 / (1024.0 * 1024.0)

        markers, caps, bars = ax.errorbar(
            xvals,
            yvals,
            yerr=(yerr_lower, yerr_upper),
            marker=marker,
            linewidth=LINEWIDTH,
            elinewidth=ELINEWIDTH,
            capsize=CAPSIZE,
            capthick=CAPTHICK,
            color=color,
            label=label
        )
        [bar.set_alpha(0.5) for bar in bars]
        [cap.set_alpha(0.5) for cap in caps]