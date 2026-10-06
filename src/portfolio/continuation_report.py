"""Non-performance figure for the continuation-feasibility audit."""
from pathlib import Path
import os
_cache=Path(__file__).resolve().parents[2]/'data/interim/stage4a_continuation/mplcache'
_cache.mkdir(parents=True,exist_ok=True)
os.environ.setdefault('MPLCONFIGDIR',str(_cache))
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Patch

ROOT=Path(__file__).resolve().parents[2]


def run():
    d=pd.read_csv(ROOT/'results/tables/stage4a/continuation_decision_states.csv',parse_dates=['decision_date'])
    fig,axes=plt.subplots(2,1,figsize=(11,6),constrained_layout=True)
    candidates=['uni_reversal_5','ridge']
    labels=['Univariate reversal','Eight-feature Ridge']
    for ax,zoom in zip(axes,[False,True]):
        for y,(model,label) in enumerate(zip(candidates,labels)):
            row=d[d.candidate==model].sort_values('decision_date')
            start=row.decision_date.min();end=row.decision_date.max()
            halt=row.loc[~row.new_primary_orders_permitted,'decision_date'].min()
            ax.plot([start,halt],[y,y],color='#238b45',lw=12,solid_capstyle='butt')
            ax.plot([halt,end],[y,y],color='#c44536',lw=12,solid_capstyle='butt')
        ax.set_yticks([0,1]);ax.set_yticklabels(labels);ax.set_ylim(-.6,1.6)
        ax.grid(axis='x',alpha=.2)
        if zoom:
            ax.set_xlim(pd.Timestamp('2003-01-02'),pd.Timestamp('2003-01-24'))
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
            ax.axvline(pd.Timestamp('2003-01-13'),color='#333333',ls='--',lw=1)
            ax.set_title('Initial decision-close window: halt Jan 13; first blocked new-entry open Jan 14')
        else:
            ax.set_xlim(pd.Timestamp('2003-01-02'),pd.Timestamp('2019-12-31'))
            ax.set_title('Development-wide feasibility: 7 / 4,279 decision dates permit new orders (0.1636%)')
    axes[0].legend(handles=[Patch(color='#238b45',label='New orders permitted'),Patch(color='#c44536',label='Unresolved execution: no independently proven resumption')],loc='upper center',fontsize=8)
    fig.suptitle('Strict continuation feasibility — no PnL or returns',fontsize=14)
    folder=ROOT/'results/figures/stage4a';folder.mkdir(parents=True,exist_ok=True)
    fig.savefig(folder/'continuation_feasibility.png',dpi=160);plt.close(fig)
