#!/usr/bin/env python3
import argparse
import os
import sys
from typing import List, Tuple, Dict

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages


# ---- Column map reconstructed from the C++ sprintf layout ----
# 0  : time_on_trace_sec
# 1  : max_tmp
# 2..7: basic TCP info in “message_extra” prelude:
#   2  rtt_100x_ms
#   3  rttvar_ms
#   4  rto_100x_ms
#   5  ato_100x_ms
#   6  pacing_rate_(100x Mbps/BW_NORM_FACTOR)
#   7  delivery_rate_(100x Mbps/BW_NORM_FACTOR)
# 8  : snd_ssthresh
# 9  : ca_state
# 10..18 : rtt_s/m/l (avg,min,max)   (3x triplets)
# 19..27 : thr_s/m/l (avg,min,max)
# 28..36 : rtt_rate_s/m/l (avg,min,max)
# 37..45 : rtt_var_s/m/l (avg,min,max)
# 46..54 : inflight_s/m/l (avg,min,max)
# 55..63 : lost_s/m/l (avg,min,max)
# 64..76 : tail metrics:
#   64 dr_w_mbps_minus_l_w_mbps
#   65 time_delta_norm
#   66 rtt_rate_scalar
#   67 l_w_mbps_norm
#   68 acked_rate_norm
#   69 dr_w_ratio
#   70 queue_delay_proxy
#   71 dr_w_mbps_norm
#   72 cwnd_unacked_rate
#   73 dr_w_max_ratio
#   74 dr_w_max_norm
#   75 reward
#   76 cwnd_rate

COLS: Dict[str, int] = {
    "time": 0,
    "max_tmp": 1,
    "rtt_100x_ms": 2, "rttvar_ms": 3, "rto_100x_ms": 4, "ato_100x_ms": 5,
    "pacing_rate_norm": 6, "delivery_rate_norm": 7,
    "snd_ssthresh": 8, "ca_state": 9,

    "rtt_s_avg": 10, "rtt_s_min": 11, "rtt_s_max": 12,
    "rtt_m_avg": 13, "rtt_m_min": 14, "rtt_m_max": 15,
    "rtt_l_avg": 16, "rtt_l_min": 17, "rtt_l_max": 18,

    "thr_s_avg": 19, "thr_s_min": 20, "thr_s_max": 21,
    "thr_m_avg": 22, "thr_m_min": 23, "thr_m_max": 24,
    "thr_l_avg": 25, "thr_l_min": 26, "thr_l_max": 27,

    "rtt_rate_s_avg": 28, "rtt_rate_s_min": 29, "rtt_rate_s_max": 30,
    "rtt_rate_m_avg": 31, "rtt_rate_m_min": 32, "rtt_rate_m_max": 33,
    "rtt_rate_l_avg": 34, "rtt_rate_l_min": 35, "rtt_rate_l_max": 36,

    "rtt_var_s_avg": 37, "rtt_var_s_min": 38, "rtt_var_s_max": 39,
    "rtt_var_m_avg": 40, "rtt_var_m_min": 41, "rtt_var_m_max": 42,
    "rtt_var_l_avg": 43, "rtt_var_l_min": 44, "rtt_var_l_max": 45,

    "inflight_s_avg": 46, "inflight_s_min": 47, "inflight_s_max": 48,
    "inflight_m_avg": 49, "inflight_m_min": 50, "inflight_m_max": 51,
    "inflight_l_avg": 52, "inflight_l_min": 53, "inflight_l_max": 54,

    "lost_s_avg": 55, "lost_s_min": 56, "lost_s_max": 57,
    "lost_m_avg": 58, "lost_m_min": 59, "lost_m_max": 60,
    "lost_l_avg": 61, "lost_l_min": 62, "lost_l_max": 63,

    "dr_minus_loss": 64,
    "time_delta_norm": 65,
    "rtt_rate_scalar": 66,
    "loss_norm": 67,
    "acked_rate_norm": 68,
    "dr_w_ratio": 69,
    "queue_delay_proxy": 70,
    "dr_w_norm": 71,
    "cwnd_unacked_rate": 72,
    "dr_w_max_ratio": 73,
    "dr_w_max_norm": 74,
    "reward": 75,
    "cwnd_rate": 76,
}

TRIPLETS: List[Tuple[str, str]] = [
    ("rtt_s", "ms (avg/min/max)"),
    ("rtt_m", "ms (avg/min/max)"),
    ("rtt_l", "ms (avg/min/max)"),

    ("thr_s", "norm (avg/min/max)"),
    ("thr_m", "norm (avg/min/max)"),
    ("thr_l", "norm (avg/min/max)"),

    ("rtt_rate_s", "1/s (avg/min/max)"),
    ("rtt_rate_m", "1/s (avg/min/max)"),
    ("rtt_rate_l", "1/s (avg/min/max)"),

    ("rtt_var_s", "ms (avg/min/max)"),
    ("rtt_var_m", "ms (avg/min/max)"),
    ("rtt_var_l", "ms (avg/min/max)"),

    ("inflight_s", "k pkts (avg/min/max)"),
    ("inflight_m", "k pkts (avg/min/max)"),
    ("inflight_l", "k pkts (avg/min/max)"),

    ("lost_s", "x/100 (avg/min/max)"),
    ("lost_m", "x/100 (avg/min/max)"),
    ("lost_l", "x/100 (avg/min/max)"),
]

SINGLES_IN_ORDER: List[Tuple[str, str]] = [
    ("rtt_100x_ms", "RTT (100x ms)"),
    ("rttvar_ms", "RTTVar (ms)"),
    ("rto_100x_ms", "RTO (100x ms)"),
    ("ato_100x_ms", "ATO (100x ms)"),
    ("pacing_rate_norm", "Pacing rate (norm)"),
    ("delivery_rate_norm", "Delivery rate (norm)"),
    ("snd_ssthresh", "snd_ssthresh"),
    ("ca_state", "TCP CA state"),

    ("rtt_rate_scalar", "RTT rate (scalar)"),
    ("dr_minus_loss", "Delivered − Loss (Mbps)"),
    ("time_delta_norm", "time_delta (norm)"),
    ("loss_norm", "loss (norm)"),
    ("acked_rate_norm", "acked_rate (norm)"),
    ("dr_w_ratio", "dr_w ratio"),
    ("queue_delay_proxy", "queue delay proxy"),
    ("dr_w_norm", "dr_w (norm)"),
    ("cwnd_unacked_rate", "cwnd_unacked_rate"),
    ("dr_w_max_ratio", "dr_w_max ratio"),
    ("dr_w_max_norm", "dr_w_max (norm)"),
    ("cwnd_rate", "cwnd_rate"),
    ("reward", "reward"),
    ("max_tmp", "max_tmp (capacity)"),
]


def load_data(path: str) -> np.ndarray:
    try:
        data = np.loadtxt(path, dtype=float)
        if data.ndim == 1:
            data = data.reshape(1, -1)
        return data
    except Exception as e:
        print(f"Error reading '{path}': {e}", file=sys.stderr)
        sys.exit(1)


def ensure_cols(data: np.ndarray) -> None:
    needed = max(COLS.values())
    if data.shape[1] <= needed:
        raise ValueError(
            f"File has {data.shape[1]} cols; expected ≥ {needed+1} from the C++ logger."
        )


def pick(data: np.ndarray, key: str) -> np.ndarray:
    return data[:, COLS[key]]


def plot_triplet(ax, t, base_key: str, ylabel: str):
    ax.plot(t, pick(data, f"{base_key}_avg"), label=f"{base_key} avg")
    ax.plot(t, pick(data, f"{base_key}_min"), "--", label=f"{base_key} min")
    ax.plot(t, pick(data, f"{base_key}_max"), ":", label=f"{base_key} max")
    ax.set_ylabel(ylabel)
    ax.grid(True, linewidth=0.3, alpha=0.7)
    ax.legend(loc="best", frameon=False)


def page(fig_title: str, rows: int = 6):
    fig, axes = plt.subplots(rows, 1, figsize=(11, 14), sharex=True, constrained_layout=True)
    fig.suptitle(fig_title)
    return fig, axes


def main():
    parser = argparse.ArgumentParser(
        description="Plot ALL metrics (gradients, reward, RTT, rates, inflight, loss, etc.) from DeepCC logs."
    )
    parser.add_argument("file", help="Path to measurement log file (whitespace-separated).")
    parser.add_argument("--out", help="Output PDF path (default: <file>_all_metrics.pdf).")
    args = parser.parse_args()

    global data
    data = load_data(args.file)
    ensure_cols(data)

    out_path = args.out or (os.path.splitext(args.file)[0] + "_all_metrics.pdf")
    t = pick(data, "time")
    title_suffix = os.path.basename(args.file)

    with PdfPages(out_path) as pdf:
        # Page 1: Headline signals
        fig, axes = page(f"Headline: Gradients & Reward — {title_suffix}", rows=5)
        ax = axes[0]; plot_triplet(ax, t, "rtt_rate_s", "Short grad (1/s)")
        ax = axes[1]; plot_triplet(ax, t, "rtt_rate_m", "Med grad (1/s)")
        ax = axes[2]; plot_triplet(ax, t, "rtt_rate_l", "Long grad (1/s)")
        ax = axes[3]; ax.plot(t, pick(data, "rtt_rate_scalar")); ax.set_ylabel("rtt_rate scalar"); ax.grid(True, lw=0.3, alpha=0.7)
        ax = axes[4]; ax.plot(t, pick(data, "reward")); ax.set_ylabel("reward"); ax.set_xlabel("time (s)"); ax.grid(True, lw=0.3, alpha=0.7)
        pdf.savefig(fig); plt.close(fig)

        # Page 2: Base TCP variables
        fig, axes = page("Base TCP / pacing / delivery", rows=6)
        singles = ["rtt_100x_ms","rttvar_ms","rto_100x_ms","ato_100x_ms","pacing_rate_norm","delivery_rate_norm"]
        for ax, key in zip(axes, singles):
            ax.plot(t, pick(data, key)); ax.set_ylabel(key); ax.grid(True, lw=0.3, alpha=0.7)
        axes[-1].set_xlabel("time (s)")
        pdf.savefig(fig); plt.close(fig)

        # Page 3: Congestion state
        fig, axes = page("Congestion state", rows=3)
        ax = axes[0]; ax.plot(t, pick(data, "snd_ssthresh")); ax.set_ylabel("snd_ssthresh"); ax.grid(True, lw=0.3, alpha=0.7)
        ax = axes[1]; ax.step(t, pick(data, "ca_state"), where="post"); ax.set_ylabel("ca_state"); ax.grid(True, lw=0.3, alpha=0.7)
        ax = axes[2]; ax.plot(t, pick(data, "cwnd_rate")); ax.set_ylabel("cwnd_rate"); ax.set_xlabel("time (s)"); ax.grid(True, lw=0.3, alpha=0.7)
        pdf.savefig(fig); plt.close(fig)

        # Page 4: RTT smoothed windows
        fig, axes = page("RTT smoothed windows", rows=3)
        plot_triplet(axes[0], t, "rtt_s", "RTT short (ms)")
        plot_triplet(axes[1], t, "rtt_m", "RTT med (ms)")
        plot_triplet(axes[2], t, "rtt_l", "RTT long (ms)")
        axes[-1].set_xlabel("time (s)")
        pdf.savefig(fig); plt.close(fig)

        # Page 5: Throughput smoothed windows
        fig, axes = page("Throughput (normalized) windows", rows=3)
        plot_triplet(axes[0], t, "thr_s", "thr short (norm)")
        plot_triplet(axes[1], t, "thr_m", "thr med (norm)")
        plot_triplet(axes[2], t, "thr_l", "thr long (norm)")
        axes[-1].set_xlabel("time (s)")
        pdf.savefig(fig); plt.close(fig)

        # Page 6: RTT gradient windows (already page 1, but grouped again for clarity)
        fig, axes = page("RTT gradient windows", rows=3)
        plot_triplet(axes[0], t, "rtt_rate_s", "grad short (1/s)")
        plot_triplet(axes[1], t, "rtt_rate_m", "grad med (1/s)")
        plot_triplet(axes[2], t, "rtt_rate_l", "grad long (1/s)")
        axes[-1].set_xlabel("time (s)")
        pdf.savefig(fig); plt.close(fig)

        # Page 7: RTT variance windows
        fig, axes = page("RTT variance windows", rows=3)
        plot_triplet(axes[0], t, "rtt_var_s", "rttvar short (ms)")
        plot_triplet(axes[1], t, "rtt_var_m", "rttvar med (ms)")
        plot_triplet(axes[2], t, "rtt_var_l", "rttvar long (ms)")
        axes[-1].set_xlabel("time (s)")
        pdf.savefig(fig); plt.close(fig)

        # Page 8: Inflight windows
        fig, axes = page("Inflight windows", rows=3)
        plot_triplet(axes[0], t, "inflight_s", "inflight short (k pkts)")
        plot_triplet(axes[1], t, "inflight_m", "inflight med (k pkts)")
        plot_triplet(axes[2], t, "inflight_l", "inflight long (k pkts)")
        axes[-1].set_xlabel("time (s)")
        pdf.savefig(fig); plt.close(fig)

        # Page 9: Loss windows
        fig, axes = page("Loss windows", rows=3)
        plot_triplet(axes[0], t, "lost_s", "lost short (x/100)")
        plot_triplet(axes[1], t, "lost_m", "lost med (x/100)")
        plot_triplet(axes[2], t, "lost_l", "lost long (x/100)")
        axes[-1].set_xlabel("time (s)")
        pdf.savefig(fig); plt.close(fig)

        # Page 10: Tail metrics (64..76) plus capacity
        fig, axes = page("Tail metrics", rows=7)
        tail_keys = [
            "dr_minus_loss","time_delta_norm","rtt_rate_scalar","loss_norm","acked_rate_norm",
            "dr_w_ratio","queue_delay_proxy","dr_w_norm","cwnd_unacked_rate",
            "dr_w_max_ratio","dr_w_max_norm","reward","max_tmp",
        ]
        rows = len(axes)
        for ax, key in zip(axes, tail_keys[:rows]):
            ax.plot(t, pick(data, key))
            ax.set_ylabel(key)
            ax.grid(True, lw=0.3, alpha=0.7)
        axes[-1].set_xlabel("time (s)")
        pdf.savefig(fig); plt.close(fig)

    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
