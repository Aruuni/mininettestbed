
LINEWIDTH = 0.30
ELINEWIDTH = 0.75
CAPTHICK = ELINEWIDTH
CAPSIZE= 2
PROTOCOLS_FRIENDLY_NAME_EXTENSION = {'cubic': 'Cubic', 'orca': 'Orca', 'bbr3': 'BBRv3', 'sage': 'Sage', 'vivace': 'Vivace', 'astraea': 'Astraea', 'vivace-uspace': 'Vivace', 'bbr1': 'BBRv1', 'astraea_old': 'Astraea (old)', 'orca-100': 'Orca-100msMTP', 'sage-24h': 'Sage-24h'}
#PROTOCOLS_EXTENSION = ['orca', 'sage', 'astraea', 'vivace-uspace', 'cubic', 'bbr3' ]
PROTOCOLS_EXTENSION = ['sage']
PROTOCOLS_MARKERS_EXTENSION = {'cubic': 'x', 'orca': '+', 'bbr3': '.', 'sage': '*', 'astraea_old': '4', 'astraea': '2', 'vivace-uspace': '_', 'bbr1': '1', 'orca-100': '3', 'sage-24h': '_'}
COLORS_EXTENSION = {'cubic': '#0C5DA5', 'orca': '#00B945', 'bbr3': '#FF9500', 'sage': '#FF2C01', 'astraea_old': '#845B97', 'astraea': '#686868', 'vivace-uspace': '#845B97', 'bbr1': '#964B00', 'orca-100': "#056428", 'sage-24h': "#EA00FF"}

PROTOCOLS_FRIENDLY_NAME_LEO = {'cubic': 'Cubic', 'orca': 'Orca', 'bbr3': 'BBRv3', 'sage': 'Sage', 'vivace': 'Vivace', 'astraea': 'Astraea', 'vivace-uspace': 'Vivace', 'bbr1': 'BBRv1', 'satcp': 'SaTCP'}
PROTOCOLS_LEO = ['cubic', 'bbr3',  'vivace-uspace', 'sage', 'astraea']
PROTOCOLS_LEOEM = ["cubic", "satcp", "bbr3", "vivace-uspace", "sage", "astraea"]
PROTOCOLS_MARKERS_LEO = {'cubic': 'x', 'orca': '+', 'bbr3': '.', 'sage': '*', 'vivace': '4', 'astraea': '2', 'vivace-uspace': '_', 'bbr1': '1', }
COLORS_LEO = {'cubic': '#0C5DA5', 'orca': '#00B945', 'bbr3': '#FF9500', 'sage': '#FF2C01', 'vivace': '#845B97', 'astraea': '#00B945', 'vivace-uspace': '#845B97', 'bbr1': '#964B00', 'satcp': '#000000'}

PATHS_INFO = {
    "Starlink_SEA_NY_15_ISL_path":  {"queue": 388, "label": "SEA to NY (ISL)"},
    "Starlink_SEA_NY_15_BP_path":   {"queue": 326, "label": "SEA to NY (BP)"},
    "Starlink_SD_NY_15_ISL_path":   {"queue": 522, "label": "SD to NY (ISL)"},
    "Starlink_SD_NY_15_BP_path":    {"queue": 408, "label": "SD to NY (BP)"},
    "Starlink_NY_LDN_15_ISL_path":  {"queue": 696, "label": "NY to LDN (ISL)"},
    "Starlink_SD_Shanghai_15_ISL_path": {"queue": 740, "label": "SD to SHA (ISL)"}
}
AQM_FRIENDLY_NAME = {'fifo':'FIFO'}
# PROTOCOLS_EXTENSION = ['cubic', 'sage', 'orca', 'astraea', 'bbr3', 'vivace', 'vivace-uspace', 'bbr1']
# PROTOCOLS_MARKERS_EXTENSION = {'cubic': 'x', 'orca': '+', 'bbr3': '^', 'sage': '*', 'vivace': '_', 'astraea': '2', 'vivace-uspace': '4', 'bbr1': '1', }
# COLORS_EXTENSION = {'cubic': '#0C5DA5', 'orca': '#00B945', 'bbr3': '#FF9500', 'sage': '#FF2C01', 'vivace': '#845B97', 'astraea': '#686868', 'vivace-uspace': '#ADD8E6', 'bbr1': '#964B00'}



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



