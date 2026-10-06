"""Execution-availability figure only, no performance charts."""
import os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
config=ROOT/'data/interim/stage4b/mplcache';config.mkdir(parents=True,exist_ok=True)
os.environ.setdefault('MPLCONFIGDIR',str(config))
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


def run():
    s=pd.read_csv(ROOT/'results/tables/stage4b/execution_feasibility_summary.csv').set_index('candidate')
    states=pd.read_csv(ROOT/'results/tables/stage4b/operational_decision_states.csv',parse_dates=['decision_date'])
    models=['uni_reversal_5','ridge'];labels=['Reversal','Ridge']
    fig,axes=plt.subplots(1,2,figsize=(12,4),constrained_layout=True)
    base=[0,0]
    for col,label,color in [('exits_resolved_delay_1','First subsequent open','#238b45'),
                            ('missing_exit_open_with_measurable_cash_replacement','Verified cash replacement','#4678a3'),
                            ('unresolved_execution_or_quantity_positions','Unverified successor quantity','#c44536')]:
        values=[s.loc[m,col] for m in models]
        axes[0].bar(labels,values,bottom=base,label=label,color=color)
        base=[a+b for a,b in zip(base,values)]
    axes[0].set_title('Missing scheduled parent opens: execution/asset paths')
    axes[0].set_ylabel('Submitted name orders');axes[0].legend(fontsize=8)
    for y,(model,label) in enumerate(zip(models,labels)):
        d=states[states.candidate==model].sort_values('decision_date')
        halt=d.loc[~d.operational,'decision_date'].min()
        axes[1].plot([pd.Timestamp('2003-01-02'),halt],[y,y],lw=14,color='#238b45',solid_capstyle='butt')
        axes[1].plot([halt,pd.Timestamp('2003-04-11')],[y,y],lw=14,color='#c44536',solid_capstyle='butt')
    axes[1].set_yticks([0,1]);axes[1].set_yticklabels(labels);axes[1].set_ylim(-.6,1.6)
    axes[1].set_xlim(pd.Timestamp('2003-01-02'),pd.Timestamp('2003-04-11'))
    axes[1].xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
    axes[1].set_title('Operational decisions: 60 / 4,279 (1.4022%), both')
    axes[1].grid(axis='x',alpha=.2)
    fig.suptitle('Stage 4B simulation under prespecified execution assumptions — no return statistics')
    folder=ROOT/'results/figures/stage4b';folder.mkdir(parents=True,exist_ok=True)
    fig.savefig(folder/'execution_feasibility.png',dpi=160);plt.close(fig)
