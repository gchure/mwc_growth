"""
Author: 
    Griffin Chure
License: 
     MIT
Description:
    This script generates the example ATC titration shown in Fig. 1 

Required Data Sets:
    analyzed_foldchange.csv
"""
#%%
import numpy as np 
import matplotlib.pyplot as plt
import pandas as pd
import mwc.stats
import mwc.viz
colors, color_list = mwc.viz.personal_style()

#%% Load the lineages and isolate the glucose samples
carbon = 'glucose'
temp = 37 
snaps = pd.read_csv('../../data/analyzed_foldchange.csv', comment='#')
glucose = snaps[(snaps['carbon']==carbon) & (snaps['temp']==temp) & 
                (snaps['strain']=='dilution') & (snaps['fold_change']>=0) & 
                (snaps['repressors']> 0)]

replicates = glucose.groupby(['date', 'run_number', 'atc_ngml']).mean().reset_index()
summarized = replicates.groupby(['atc_ngml']).agg(('mean', 'sem')).reset_index()
# %%
# Instantiate figure
fig, ax = plt.subplots(1, 1, figsize=(2.5, 2.5), sharex=True, sharey=True)

ax2 = ax.twinx()
ax2.yaxis.grid(False)
ax2.spines['right'].set_visible(True)
ax.set_xscale('log')
ax.xaxis.set_tick_params(labelsize=6)
ax.yaxis.set_tick_params(labelsize=6, labelcolor=colors['dark_orange'])
ax2.yaxis.set_tick_params(labelsize=6, labelcolor=colors['dark_red'])
ax.set_xlabel('ATC [ng / mL]',  fontsize=8)
ax.set_ylabel('relative YFP intensity',  fontsize=8, 
             color=colors['dark_orange'])
ax2.set_ylabel('relative mCherry intensity', fontsize=8, rotation=-90,
               labelpad=10, color=colors['dark_red'])
mwc.viz.titlebox(ax2, 'GLUCOSE, 37 °C', size=6, color=colors['purple'],
                 bgcolor=colors['pale_purple'], pad=0.4)

# Set the maximum to normalize
max_yfp = 2.5E5
max_mch = 1.4E5
ax.errorbar(summarized['atc_ngml'], summarized['yfp_sub']['mean']/max_yfp, summarized['yfp_sub']['sem']/max_yfp, linestyle='-', fmt='.',
                    color=colors['orange'], label='__nolegend__', markerfacecolor=colors['light_orange'],
                    capsize=2, lw=0.75, ms=8, markeredgewidth=0.75)
ax2.errorbar(summarized['atc_ngml'], summarized['mch_sub']['mean']/max_mch, summarized['mch_sub']['sem']/max_mch, linestyle='-', fmt='.',
                    color=colors['dark_red'], label='__nolegend__', markerfacecolor=colors['light_red'],
                    capsize=2, lw=0.75, ms=8, markeredgewidth=0.75)

plt.tight_layout()
ax.set_ylim([ax.get_ylim()[0], 1.2])
ax2.set_ylim([ax2.get_ylim()[0], 1.2])
ax.yaxis.set_ticks([0.2, 0.4, 0.6, 0.8, 1.0])
ax2.yaxis.set_ticks([0.2, 0.4, 0.6, 0.8, 1.0])

plt.savefig(f'../../figs/Fig2_atc_titration.pdf', bbox_inches='tight',
            facecolor='none')


#%%
