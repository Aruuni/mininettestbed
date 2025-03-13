
LINEWIDTH = 0.30
ELINEWIDTH = 0.75
CAPTHICK = ELINEWIDTH
CAPSIZE= 2

def plot_points_rtt(ax, df, data, error,  marker, label):
    if not df.empty:
        xvals = df.index * 2
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
            label=label
        )
        [bar.set_alpha(0.5) for bar in bars]
        [cap.set_alpha(0.5) for cap in caps]

def plot_points_bw(ax, df, data, error,  marker, label):
    if not df.empty:
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
            label=label
        )
        [bar.set_alpha(0.5) for bar in bars]
        [cap.set_alpha(0.5) for cap in caps]