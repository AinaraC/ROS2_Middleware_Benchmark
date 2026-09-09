#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import re
import matplotlib.pyplot as plt
import seaborn as sns
import warnings

warnings.filterwarnings("ignore")
sns.set(style="darkgrid")

DIST_KEYS = ["fast", "cyclone", "zenoh", "fastqos", "cycloneqos", "zenohqos"]

def find_csvs(base_dir: Path):
    return list(base_dir.rglob("*.csv"))

def load_and_extract(path: Path):
    df = pd.read_csv(path)
    # exact column names
    lat_col = "latency" if "latency" in df.columns else None
    jitter_col = "jitter" if "jitter" in df.columns else None
    time_col = "timestamp_s" if "timestamp_s" in df.columns else None

    warmup = 15
    # drop first samples (warm-up)
    if len(df) <= warmup:
        raise ValueError(f"Not enough rows in {path} after dropping first {warmup}")
    df = df.iloc[warmup:].reset_index(drop=True)

    if lat_col is None:
        num = df.select_dtypes(include=[np.number])
        if num.shape[1] == 0:
            raise ValueError(f"No numeric columns found in {path}")
        lat_col = num.var().idxmax()

    df[lat_col] = pd.to_numeric(df[lat_col], errors="coerce")
    if jitter_col is not None:
        df[jitter_col] = pd.to_numeric(df[jitter_col], errors="coerce")

    # Build relative seconds starting at 1; if timestamp_s exists use it, otherwise interpolate 1..60
    if time_col is not None:
        df[time_col] = pd.to_numeric(df[time_col], errors="coerce")
        if df[time_col].notna().any():
            first = df[time_col].dropna().iloc[0]
            df["_ts"] = (df[time_col] - first).astype(float)
            df["_ts"] = df["_ts"] + 1.0
        else:
            df["_ts"] = np.linspace(1.0, 60.0, len(df))
    else:
        df["_ts"] = np.linspace(1.0, 60.0, len(df))

    return df, lat_col, jitter_col

def compute_stats_for_df(df, lat_col, jitter_col):
    # select only samples in 1..60 s
    mask = df["_ts"].notna() & (df["_ts"] >= 1.0) & (df["_ts"] <= 60.0)
    lat = df.loc[mask, lat_col].dropna().astype(float).reset_index(drop=True)
    if lat.empty:
        return None, pd.Series(dtype=float), pd.Series(dtype=float), pd.Series(dtype=float)
    if jitter_col and jitter_col in df.columns:
        jit = df.loc[mask, jitter_col].dropna().astype(float).reset_index(drop=True)
    else:
        jit = lat.diff().abs().dropna().reset_index(drop=True)
    stats = {
        "lat_mean": lat.mean(),
        "lat_min": lat.min(),
        "lat_max": lat.max(),
        "jit_mean": jit.mean() if not jit.empty else np.nan,
        "jit_min": jit.min() if not jit.empty else np.nan,
        "jit_max": jit.max() if not jit.empty else np.nan
    }
    ts_used = df.loc[mask, "_ts"].reset_index(drop=True)
    return stats, lat, jit, ts_used

def group_by_distribution(paths):
    groups = {k: [] for k in DIST_KEYS}
    other = []
    for p in paths:
        name = p.name.lower()
        normalized = re.sub(r'[^a-z0-9]', '', name)
        placed = False
        for k in sorted(DIST_KEYS, key=len, reverse=True):
            if k in normalized:
                groups[k].append(p)
                placed = True
                break
        if not placed:
            parts = [re.sub(r'[^a-z0-9]', '', s.lower()) for s in p.parts]
            for k in DIST_KEYS:
                if any(k == part for part in parts):
                    groups[k].append(p)
                    placed = True
                    break
        if not placed:
            other.append(p)
    return groups, other

def aggregate_stats(file_stats):
    if not file_stats:
        return None
    all_lat = pd.concat([s["lat"] for s in file_stats], ignore_index=True)
    all_jit = pd.concat([s["jit"] for s in file_stats], ignore_index=True) if any(not s["jit"].empty for s in file_stats) else pd.Series(dtype=float)
    if all_lat.empty:
        return None
    return {
        "lat_mean": all_lat.mean(),
        "lat_min": all_lat.min(),
        "lat_max": all_lat.max(),
        "jit_mean": all_jit.mean() if not all_jit.empty else np.nan,
        "jit_min": all_jit.min() if not all_jit.empty else np.nan,
        "jit_max": all_jit.max() if not all_jit.empty else np.nan,
        "lat_series": all_lat,
        "jit_series": all_jit
    }

def plot_time_series(per_dist_series, outdir: Path):
    groups = {
        'sin_qos': ['fast', 'cyclone', 'zenoh'],
        'con_qos': ['fastqos', 'cycloneqos', 'zenohqos']
    }

    def plot_group(group_keys, prefix, title_suffix):
        plt.figure(figsize=(12, 6))
        any_plotted = False
        for dist in group_keys:
            data = per_dist_series.get(dist, {})
            lat_concat = data.get('lat_concat')
            ts_concat = data.get('ts_concat')
            if lat_concat is None or len(lat_concat) == 0:
                continue
            any_plotted = True
            x = ts_concat if ts_concat is not None else np.linspace(1, 60, len(lat_concat))
            plt.plot(x, lat_concat, label=dist)
        if not any_plotted:
            plt.close()
            return
        plt.xlabel('Experiment duration (s)')
        plt.ylabel('Latency')
        plt.title(f'Latency over time (1-60 s) {title_suffix}')
        plt.xlim(1, 60)
        plt.legend()
        plt.tight_layout()
        plt.savefig(outdir / f'{prefix}_latency_timeseries.png')
        plt.close()

        plt.figure(figsize=(12, 6))
        any_plotted = False
        for dist in group_keys:
            data = per_dist_series.get(dist, {})
            jit_concat = data.get('jit_concat')
            ts_concat = data.get('ts_concat')
            if jit_concat is None or len(jit_concat) == 0:
                continue
            any_plotted = True
            x = ts_concat if ts_concat is not None else np.linspace(1, 60, len(jit_concat))
            plt.plot(x, jit_concat, label=dist)
        if not any_plotted:
            plt.close()
            return
        plt.xlabel('Experiment duration (s)')
        plt.ylabel('Jitter')
        plt.title(f'Jitter over time (1-60 s) {title_suffix}')
        plt.xlim(1, 60)
        plt.legend()
        plt.tight_layout()
        plt.savefig(outdir / f'{prefix}_jitter_timeseries.png')
        plt.close()

    plot_group(groups['sin_qos'], 'sin_qos', '(sin QoS)')
    plot_group(groups['con_qos'], 'con_qos', '(con QoS)')

def main():
    parser = argparse.ArgumentParser(description="Calcular métricas de latencia y jitter y plotear series")
    parser.add_argument("--dir", "-d", default=".", help="Directorio raíz donde buscar CSVs")
    parser.add_argument("--out", "-o", default="results", help="Directorio de salida para gráficos")
    args = parser.parse_args()

    base = Path(args.dir).resolve()
    outdir = Path(args.out).resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    csvs = find_csvs(base)
    if not csvs:
        print("No se encontraron archivos CSV en", base)
        sys.exit(1)

    groups, other = group_by_distribution(csvs)
    summary_rows = []
    per_dist_series = {}

    for dist in DIST_KEYS:
        files = groups.get(dist, [])
        file_stats = []
        lat_series_all = []
        jit_series_all = []
        ts_all = []
        for f in files:
            try:
                df, lat_col, jitter_col = load_and_extract(f)
            except Exception as e:
                print(f"Warning: fallo al leer {f}: {e}")
                continue
            stats, lat, jit, ts = compute_stats_for_df(df, lat_col, jitter_col)
            if stats is None:
                continue
            file_stats.append({"stats": stats, "lat": lat, "jit": jit})
            lat_series_all.append(lat)
            jit_series_all.append(jit)
            if not ts.empty:
                ts_all.append(ts)
        agg = aggregate_stats(file_stats)
        if agg:
            summary_rows.append({
                "distribution": dist,
                "lat_mean": agg["lat_mean"],
                "lat_min": agg["lat_min"],
                "lat_max": agg["lat_max"],
                "jit_mean": agg["jit_mean"],
                "jit_min": agg["jit_min"],
                "jit_max": agg["jit_max"],
                "n_samples": len(agg["lat_series"])
            })
            lat_concat = pd.concat(lat_series_all, ignore_index=True) if lat_series_all else pd.Series(dtype=float)
            jit_concat = pd.concat(jit_series_all, ignore_index=True) if jit_series_all else pd.Series(dtype=float)
            ts_concat = pd.concat(ts_all, ignore_index=True) if ts_all else None
            per_dist_series[dist] = {
                "lat_concat": lat_concat.values if not lat_concat.empty else None,
                "jit_concat": jit_concat.values if not jit_concat.empty else None,
                "ts_concat": ts_concat.values if ts_concat is not None else None
            }
        else:
            summary_rows.append({
                "distribution": dist,
                "lat_mean": np.nan,
                "lat_min": np.nan,
                "lat_max": np.nan,
                "jit_mean": np.nan,
                "jit_min": np.nan,
                "jit_max": np.nan,
                "n_samples": 0
            })

    summary_df = pd.DataFrame(summary_rows)
    print("\nResumen por distribución:")
    print(summary_df.to_string(index=False, float_format="%.6f"))

    plot_time_series(per_dist_series, outdir)
    print(f"\nGráficas guardadas en: {outdir}")
    print("Archivos: latency_timeseries.png, jitter_timeseries.png")

if __name__ == "__main__":
    main()