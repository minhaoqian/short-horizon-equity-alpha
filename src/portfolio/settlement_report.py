"""Conditional execution availability figures only; no performance."""
import os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
config = ROOT/'data/interim/stage4e_scenarios/mplcache'
config.mkdir(parents=True, exist_ok=True)
os.environ.setdefault('MPLCONFIGDIR', str(config))
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def run():
    f = pd.read_csv(ROOT/'results/tables/stage4e/conditional_merger_cohort_accounting.csv')
    s = pd.read_csv(ROOT/'results/tables/stage4e/conditional_feasibility_summary.csv')
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), constrained_layout=True)
    scenarios = ['D0', 'D2', 'D5']
    # Both candidate cohort schedules match: no candidate ranking implied.
    f = f[f.candidate == 'ridge']
    for j, (signal, color) in enumerate(zip(sorted(f.signal_date.unique()), ['#4477aa', '#66aabb', '#aa6677'])):
        g = f[f.signal_date == signal].set_index('scenario')
        axes[0].bar([i+(j-1)*.24 for i in range(3)], [g.loc[x, 'delay'] for x in scenarios],
                    width=.24, label=f'Signal {signal}', color=color)
    axes[0].set_xticks(range(3), scenarios)
    axes[0].set_ylabel('Delay from original scheduled exit (global dates)')
    axes[0].set_title('Original merger: 6 / 6 cohorts resolve per scenario')
    axes[0].legend(fontsize=8)
    axes[0].set_ylim(0, 6)
    for j, (model, color) in enumerate([('uni_reversal_5', '#4477aa'), ('ridge', '#aa6677')]):
        g = s[s.candidate == model].set_index('scenario')
        axes[1].bar([i+(j-.5)*.3 for i in range(3)], [g.loc[x, 'operational_decision_dates'] for x in scenarios],
                    width=.3, label='Reversal' if j == 0 else 'Ridge', color=color)
    axes[1].set_xticks(range(3), scenarios)
    axes[1].set_ylim(0, 90)
    axes[1].set_ylabel('Operational development decision dates')
    axes[1].set_title('72 / 4,279 dates (1.6826%) in every run')
    axes[1].legend(fontsize=8)
    axes[1].text(.5, .94, 'New unresolved merger: halt close 2003-04-16',
                 transform=axes[1].transAxes, ha='center', va='top', fontsize=9)
    fig.suptitle('Stage 4E conditional settlement feasibility — no portfolio performance')
    out = ROOT/'results/figures/stage4e'; out.mkdir(parents=True, exist_ok=True)
    fig.savefig(out/'conditional_execution_feasibility.png', dpi=160)
    plt.close(fig)
