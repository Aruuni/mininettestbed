#!/usr/bin/env python3

import os, sys, re, glob
from typing import List, Tuple, Dict, Iterable
import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

# Matplotlib
plt.rcParams['text.usetex'] = False
mpl.rcParams.update({
    "figure.figsize": (8.0, 5.8),
    "axes.titlesize": 12,
    "axes.labelsize": 11,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "legend.fontsize": 10,
})

# Project paths / imports
script_dir = os.path.dirname(__file__)
mymodule_dir = os.path.join(script_dir, '../..')
sys.path.append(mymodule_dir)
from core.config import *  # HOME_DIR, etc.

EXPERIMENT_PATH = f"{HOME_DIR}/cctestbed/benchmarks/resutls_delay_jump_threading"

# Analysis window
CHANGE_START = 25
DURATION     = 50
WINDOW_START = CHANGE_START
WINDOW_END   = DURATION

# Filters
FILTER_BWS       : Iterable[int]  = [100]
FILTER_PROTOCOLS : Iterable[str]  = ['athena_delay_reduced', 'sage_delay_real2', 'sage', 'bbr', 'cubic']
FILTER_AQMS      : Iterable[str]  = ['fifo']
FILTER_RUNS      : Iterable[int]  = [1, 2, 3]
FILTER_DELAYS    : Iterable[int]  = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
QMULT            : float          = 2.0  # New: cap for RTT-ratio colorbar => vmax = QMULT + 1

def _require(name: str, seq: Iterable):
    if seq is None:
        raise ValueError(f"{name} must be set (not None).")
    try:
        seq = list(seq)
    except Exception:
        raise ValueError(f"{name} must be an iterable.")
    if len(seq) == 0:
        raise ValueError(f"{name} is empty. Provide at least one value.")
    return seq

def find_run_dirs(base_dir: str) -> List[str]:
    pat = os.path.join(base_dir, "Dumbell_*mbit_*ms_to_*ms_*pkts_*loss_*flows_*_*", "run*")
    return sorted(glob.glob(pat))

def parse_meta_from_path(path: str) -> Dict[str, object] | None:
    """
    Parse metadata from a run directory path using simple string operations,
    so protocol names can safely contain underscores.

    Expected directory structure (parent of run dir):
      Dumbell_{bw}mbit_{delay}ms_to_{delay2}ms_{...pkts...}_{...loss...}_{flows}flows_{protocol}_{aqm}
    """
    try:
        # Path ends in ".../Dumbell_.../runX"
        path = path.rstrip("/")

        # --- Run number ---
        run_name = os.path.basename(path)
        if not run_name.startswith("run"):
            return None
        run = int(run_name[3:])

        # --- Experiment directory name ---
        exp_dir = os.path.basename(os.path.dirname(path))
        prefix = "Dumbell_"
        if not exp_dir.startswith(prefix):
            return None

        s = exp_dir[len(prefix):]  # strip "Dumbell_"

        # bw: "{bw}mbit_..."
        i = s.find("mbit_")
        if i == -1:
            return None
        bw = int(s[:i])
        s = s[i + len("mbit_"):]

        # delay: "{delay}ms_to_..."
        i = s.find("ms_to_")
        if i == -1:
            return None
        delay = int(s[:i])
        s = s[i + len("ms_to_"):]

        # delay2: "{delay2}ms_..."
        i = s.find("ms_")
        if i == -1:
            return None
        delay2 = int(s[:i])
        s = s[i + len("ms_"):]
        # now s looks like: "{pkts}pkts_{loss}loss_{flows}flows_{protocol}_{aqm}"

        # find "flows_"
        flows_pos = s.find("flows_")
        if flows_pos == -1:
            return None

        before_flows = s[:flows_pos]      # "..._{flows}"
        after_flows  = s[flows_pos + len("flows_"):]  # "{protocol}_{aqm}"

        # flows is the last underscore-separated token before "flows_"
        last_us = before_flows.rfind("_")
        if last_us == -1:
            return None
        flows_str = before_flows[last_us + 1:]
        flows = int(flows_str)

        # protocol and aqm: protocol can contain underscores, aqm is after the last "_"
        last_us2 = after_flows.rfind("_")
        if last_us2 == -1:
            return None
        protocol = after_flows[:last_us2]
        aqm = after_flows[last_us2 + 1:]

        return {
            "bw":       bw,
            "delay":    delay,
            "delay2":   delay2,
            "flows":    flows,
            "protocol": protocol,
            "aqm":      aqm,
            "run":      run,
        }

    except Exception:
        # Any parsing failure => this path is not a valid run dir for us
        return None
def pick_latest(dirs: List[str], pattern: str) -> str | None:
    matches: List[str] = []
    for d in dirs:
        matches.extend(glob.glob(os.path.join(d, pattern)))
    if not matches:
        return None
    return max(matches, key=os.path.getmtime)

# Loaders

def _normalize_time_col(df: pd.DataFrame, candidates=('time','t','sec','seconds')) -> str | None:
    for c in candidates:
        if c in df.columns:
            df['time'] = df[c].apply(lambda x: int(float(x)))
            return 'time'
    return None

def load_goodput_series(run_dir: str) -> pd.DataFrame | None:
    search_dirs = [os.path.join(run_dir, "csvs"), run_dir]
    x_path = pick_latest(search_dirs, "x1*.csv") or pick_latest(search_dirs, "x2*.csv")
    if not x_path:
        return None
    try:
        df = pd.read_csv(x_path).reset_index(drop=True)
    except Exception:
        return None
    tcol = _normalize_time_col(df)
    bcol = next((c for c in ('bandwidth','throughput','goodput','rate_mbps','bw') if c in df.columns), None)
    if not tcol or not bcol:
        return None
    return df[['time', bcol]].rename(columns={bcol: 'bandwidth'})

def load_rtt_series_pair(run_dir: str) -> Tuple[pd.DataFrame | None, pd.DataFrame | None]:
    search_dirs = [os.path.join(run_dir, "csvs"), run_dir]
    c1 = pick_latest(search_dirs, "c1*_ss.csv") or pick_latest(search_dirs, "c1*.csv")
    c2 = pick_latest(search_dirs, "c2*_ss.csv") or pick_latest(search_dirs, "c2*.csv")
    out = []
    for path in (c1, c2):
        if not path:
            out.append(None); continue
        try:
            df = pd.read_csv(path).reset_index(drop=True)
        except Exception:
            out.append(None); continue
        tcol = _normalize_time_col(df)
        rcol = 'rtt' if 'rtt' in df.columns else None
        if not tcol or not rcol:
            out.append(None); continue
        out.append(df[['time','rtt']])
    return out[0], out[1]

# Window reducers

def mean_goodput_in_window(df: pd.DataFrame, start: int, end: int) -> float | None:
    if df is None or df.empty: return None
    w = df.drop_duplicates('time')
    w = w[(w['time'] >= start) & (w['time'] <= end)]
    if w.empty: return None
    return float(w['bandwidth'].mean())

def mean_rtt_in_window(c1: pd.DataFrame | None, c2: pd.DataFrame | None, start: int, end: int) -> float | None:
    vals = []
    for df in (c1, c2):
        if df is None or df.empty: continue
        w = df.drop_duplicates('time')
        w = w[(w['time'] >= start) & (w['time'] <= end)]
        if not w.empty:
            vals.append(float(w['rtt'].mean()))
    if not vals:
        return None
    return float(np.mean(vals))

# Plot helpers

def _robust_vmin_vmax(matrix: np.ndarray) -> Tuple[float, float]:
    if np.all(np.isnan(matrix)):
        return 0.0, 1.0
    try:
        vmin = float(np.nanquantile(matrix, 0.05))
        vmax = float(np.nanquantile(matrix, 0.95))
        if not np.isfinite(vmin) or not np.isfinite(vmax) or vmin >= vmax:
            raise ValueError
    except Exception:
        vmin = float(np.nanmin(matrix))
        vmax = float(np.nanmax(matrix))
        if not np.isfinite(vmin) or not np.isfinite(vmax) or vmin >= vmax:
            vmin, vmax = 0.0, max(1.0, vmin if np.isfinite(vmin) else 1.0)
    return vmin, vmax

def plot_heatmap_on_axes(ax, matrix: np.ndarray, y_labels: List[int], x_labels: List[float],
                         title: str, cbar_label: str, cmap: str, annotate: bool = True,
                         xfmt=lambda r: f"{r:g}x", std_mat: np.ndarray | None = None,
                         n_mat: np.ndarray | None = None, d2_mat: np.ndarray | None = None):
    data = np.ma.masked_invalid(matrix)
    vmin, vmax = 0.0, 100.0
    im = ax.imshow(data, origin="lower", aspect="auto", interpolation="nearest",
                   vmin=vmin, vmax=vmax, cmap=cmap)
    ax.set_xticks(range(len(x_labels))); ax.set_xticklabels([xfmt(r) for r in x_labels])
    ax.set_yticks(range(len(y_labels))); ax.set_yticklabels([str(d) for d in y_labels])
    ax.set_xlabel("Step size (delay2 / delay)")
    ax.set_ylabel("Base RTT (ms)")
    ax.set_title(title)
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label(cbar_label)
    if annotate:
        for (i, j), val in np.ndenumerate(matrix):
            if np.isnan(val):
                ax.text(j, i, 'x', ha='center', va='center', fontsize=10, color='white', fontweight='bold')
            else:
                rgba = im.cmap(im.norm(val))
                r, g, b = rgba[:3]
                L = 0.2126*r + 0.7152*g + 0.0722*b
                txt_color = 'black' if L > 0.6 else 'white'
                main = f"{val:.2f}"
                if std_mat is not None and np.isfinite(std_mat[i, j]):
                    main = f"{val:.2f} ± {std_mat[i, j]:.2f}"
                extras = []
                txt = f"{main}\n{', '.join(extras)}" if extras else main
                ax.text(j, i, txt, ha='center', va='center', fontsize=8, color=txt_color)

def plot_one_sided_ratio_on_axes(ax, matrix: np.ndarray, y_labels: List[int], x_labels: List[float],
                                 title: str, cbar_label: str, vmin: float = 1.0,
                                 xfmt=lambda r: f"{r:g}x", std_mat: np.ndarray | None = None,
                                 n_mat: np.ndarray | None = None, d2_mat: np.ndarray | None = None):
    data = np.array(matrix, dtype=float, copy=True)
    with np.errstate(invalid='ignore'):
        data[data < vmin] = vmin
    if np.all(np.isnan(data)):
        vmax = vmin + 0.2
    else:
        try:
            vmax = float(np.nanquantile(data, 0.95))
            if vmax <= vmin:
                vmax = vmin + 0.1
        except Exception:
            vmax = float(np.nanmax(data)) if np.isfinite(np.nanmax(data)) else (vmin + 0.1)

    # Cap the RTT ratio ("delay bar") maximum at QMULT + 1
    vmax = max(vmin, float(QMULT) + 1.0)

    im = ax.imshow(np.ma.masked_invalid(data), origin="lower", aspect="auto",
                   interpolation="nearest", cmap="RdYlGn_r",
                   vmin=vmin, vmax=vmax)
    ax.set_xticks(range(len(x_labels))); ax.set_xticklabels([xfmt(r) for r in x_labels])
    ax.set_yticks(range(len(y_labels))); ax.set_yticklabels([str(d) for d in y_labels])
    ax.set_xlabel("Step size (delay2 / delay)")
    ax.set_ylabel("Base RTT (ms)")
    ax.set_title(title)
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label(cbar_label)
    for (i, j), val in np.ndenumerate(matrix):
        if np.isnan(val):
            ax.text(j, i, 'x', ha='center', va='center', fontsize=10, color='white', fontweight='bold')
        else:
            rgba = im.cmap(im.norm(max(val, vmin)))
            r, g, b = rgba[:3]
            L = 0.2126*r + 0.7152*g + 0.0722*b
            txt_color = 'black' if L > 0.6 else 'white'
            main = f"{val:.3f}"
            if std_mat is not None and np.isfinite(std_mat[i, j]):
                main = f"{val:.3f} ± {std_mat[i, j]:.3f}"
            extras = []
            txt = f"{main}\n{', '.join(extras)}" if extras else main
            ax.text(j, i, txt, ha='center', va='center', fontsize=8, color=txt_color)

# Matrix builder

def build_stats_matrices(buckets: Dict[Tuple[int, float], List[float]],
                         delay_to_i: Dict[int, int], step_to_j: Dict[float, int],
                         shape: Tuple[int, int]) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    mean_mat = np.full(shape, np.nan, dtype=float)
    std_mat  = np.full(shape, np.nan, dtype=float)
    n_mat    = np.zeros(shape, dtype=float)
    d2_mat   = np.full(shape, np.nan, dtype=float)
    for (delay, ratio), vals in buckets.items():
        if delay in delay_to_i and ratio in step_to_j:
            i, j = delay_to_i[delay], step_to_j[ratio]
            arr = np.asarray(vals, dtype=float)
            if arr.size:
                mean_mat[i, j] = float(np.nanmean(arr))
                std_mat[i, j]  = float(np.nanstd(arr, ddof=0))
                n_mat[i, j]    = float(arr.size)
                d2_mat[i, j]   = float(round(delay * ratio))
    return mean_mat, std_mat, n_mat, d2_mat

# Main

def main():
    bws    = _require("FILTER_BWS", FILTER_BWS)
    prots  = _require("FILTER_PROTOCOLS", FILTER_PROTOCOLS)
    aqms   = _require("FILTER_AQMS", FILTER_AQMS)
    runs   = _require("FILTER_RUNS", FILTER_RUNS)
    delays = _require("FILTER_DELAYS", FILTER_DELAYS)

    run_dirs = find_run_dirs(EXPERIMENT_PATH)
    if not run_dirs:
        print(f"No run directories found under: {EXPERIMENT_PATH}")
        return

    records: list[tuple[str, Dict[str, object]]] = []
    for rd in run_dirs:
        meta = parse_meta_from_path(rd)
        if not meta:
            continue
        if (meta["bw"] in bws and
            meta["protocol"] in prots and
            meta["aqm"] in aqms and
            meta["run"] in runs and
            meta["delay"] in delays):
            records.append((rd, meta))

    if not records:
        print("No matching runs after filters. Check your FILTER_* values.")
        return

    base_delays = list(dict.fromkeys(delays))
    step_ratios = sorted({round(m["delay2"] / m["delay"], 6) for _, m in records})
    delay_to_i = {d: i for i, d in enumerate(base_delays)}
    step_to_j  = {r: j for j, r in enumerate(step_ratios)}
    shape = (len(base_delays), len(step_ratios))

    buckets_gp_by_proto : Dict[str, Dict[Tuple[int, float], List[float]]] = {p:{} for p in prots}
    buckets_rt_by_proto : Dict[str, Dict[Tuple[int, float], List[float]]] = {p:{} for p in prots}

    for rd, meta in records:
        ratio = round(meta["delay2"] / meta["delay"], 6)
        df_g = load_goodput_series(rd)
        gp = mean_goodput_in_window(df_g, WINDOW_START, WINDOW_END)
        c1, c2 = load_rtt_series_pair(rd)
        rt = mean_rtt_in_window(c1, c2, WINDOW_START, WINDOW_END)
        rt_ratio = (rt / meta["delay2"]) if (rt is not None and meta["delay2"] > 0) else None
        key = (meta["delay"], ratio)
        if gp is not None:
            buckets_gp_by_proto.setdefault(meta["protocol"], {}).setdefault(key, []).append(gp)
        if rt_ratio is not None:
            buckets_rt_by_proto.setdefault(meta["protocol"], {}).setdefault(key, []).append(rt_ratio)

    out_pdf = "heatmaps_delay_jump_by_protocol.pdf"
    with PdfPages(out_pdf) as pdf:
        for p in prots:
            gp_mean, gp_std, gp_n, gp_d2 = build_stats_matrices(buckets_gp_by_proto.get(p, {}), delay_to_i, step_to_j, shape)
            rt_mean, rt_std, rt_n, rt_d2 = build_stats_matrices(buckets_rt_by_proto.get(p, {}), delay_to_i, step_to_j, shape)

            fig, axes = plt.subplots(1, 2, figsize=(12.0, 5.8))
            plt.subplots_adjust(wspace=0.25)

            plot_heatmap_on_axes(
                ax=axes[0],
                matrix=gp_mean,
                y_labels=base_delays, x_labels=step_ratios,
                title=f"Goodput (t ≥ 20 s) — {p}",
                cbar_label="Average goodput (Mbps)",
                cmap="RdYlGn",
                std_mat=gp_std, n_mat=gp_n, d2_mat=gp_d2,
            )

            plot_one_sided_ratio_on_axes(
                ax=axes[1],
                matrix=rt_mean,
                y_labels=base_delays, x_labels=step_ratios,
                title=f"RTT ratio (avg srtt / delay2) — {p}",
                cbar_label="RTT ratio (≥ 1 is ideal)",
                vmin=1.0,
                std_mat=rt_std, n_mat=rt_n, d2_mat=rt_d2,
            )

            fig.suptitle(f"Delay jump heatmaps — {p}")
            fig.tight_layout(rect=[0, 0.0, 1, 0.96])
            pdf.savefig(fig)
            plt.close(fig)
    print(f"Wrote multi-page PDF: {out_pdf}")

if __name__ == "__main__":
    main()
