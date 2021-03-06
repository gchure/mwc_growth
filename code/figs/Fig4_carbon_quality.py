"""
Author: 
    Griffin Chure
License:
    MIT
Description:
    This generates a single figure with 8 subplots. They show the fold-change in
    gene expression for each condition as well as the free energy shift plotted
    over the predictions.
Required Data Sets:
    analyzed_foldchange.csv
    inferred_empirical_F.csv

"""
#%%
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import mwc.viz
import mwc.stats
colors, color_list = mwc.viz.personal_style()

# Define the repressor copy number range. 
rep_range = np.logspace(0, 4, 200)

# Define the target points for the explanation
example_reps = np.array([25, 50, 100, 200, 400])
example_facecolors = {25:colors['light_purple'], 50: colors['light_orange'],
                    100:'white', 200:colors['light_red'], 400:colors['light_blue']}
example_edgecolors = {25:colors['dark_purple'], 50: colors['dark_orange'],
                    100:colors['black'], 200:colors['dark_red'], 400:colors['dark_blue']}
ref_rep = 100

# Define thermodynamic constants
ep_ai = 4.5 # in kT
ep_RA = -13.9 # in kT
Nns = 4.6E6 # in bp
sigma = 0.2

# Define the fold-change and the deltaF theory curves
pact = (1 + np.exp(-ep_ai))**-1
fc = (1 + pact * (rep_range / Nns) * np.exp(-ep_RA))**-1 
fc_min = (1 + pact * (rep_range / Nns) * np.exp(-(ep_RA + sigma)))**-1 
fc_max = (1 + pact * (rep_range / Nns) * np.exp(-(ep_RA - sigma)))**-1 
example_fc = (1 + pact * (example_reps/ Nns) * np.exp(-(ep_RA - sigma)))**-1 
example_delF = -np.log(example_reps / ref_rep)
F_ref = -np.log(pact) - np.log(ref_rep/Nns) + ep_RA
deltaF = -np.log(rep_range / ref_rep) # in kT

# Load the actual data. 
fc_data = pd.read_csv('../../data/analyzed_foldchange.csv', comment='#')
fc_data = mwc.process.condition_filter(fc_data, temp=37)
inferred_F = pd.read_csv('../../data/inferred_empirical_F.csv', comment='#')

# Isolate the fc data to the relevant measurements 
inferred_F = inferred_F[inferred_F['temp']==37].copy()

# Compute the summary statistics
rep_summary = fc_data.groupby(['date', 'run_number', 
                               'atc_ngml', 'carbon']).mean().reset_index()
summary = rep_summary.groupby(['atc_ngml', 'carbon']).agg(('mean', 'sem')).reset_index()

#%% Set up the figure axis
fig, ax = plt.subplots(2, 4, figsize=(7, 3.5), dpi=100)

# Define the axes and colors
ax_map = {'glucose':0, 'glycerol':1, 'acetate':2}
edgecolors = {'glucose':colors['dark_purple'], 'glycerol':colors['dark_green'],
              'acetate':colors['dark_brown']}
facecolors = {'glucose':colors['light_purple'], 'glycerol':colors['light_green'],
              'acetate':colors['light_brown']}

for g, d in summary.groupby(['carbon']):
    ax[0, ax_map[g]].errorbar(d['repressors']['mean'], d['fold_change']['mean'], 
                      xerr=d['repressors']['sem'], yerr=d['fold_change']['sem'],
                      fmt='.', ms=8, color=edgecolors[g], 
                      markerfacecolor=facecolors[g], markeredgewidth=0.75)

for g, d in inferred_F.groupby(['carbon']):
        _reps = summary[(summary['carbon']==g)]
        F = d[d['parameter']=='empirical_F']['median']
        F_max = d[d['parameter']=='empirical_F']['hpd_max']
        F_min = d[d['parameter']=='empirical_F']['hpd_min']
        delF = F - F_ref   
        delF_max = F_max - F_ref   
        delF_min = F_min - F_ref   
        ax[1, ax_map[g]].errorbar(_reps['repressors']['mean'] / ref_rep, delF, xerr=_reps['repressors']['sem'] / ref_rep, 
        fmt='.', color=edgecolors[g], markerfacecolor=facecolors[g], linestyle='none', linewidth=1,
        ms=8, markeredgewidth=0.75)
        ax[1, ax_map[g]].vlines(_reps['repressors']['mean'] / ref_rep, delF_max, delF_min, lw=0.75,
                        color=edgecolors[g])

for i in range(4):
    ax[0, i].fill_between(rep_range, fc_min,  fc_max, color='k', alpha=0.25)
    ax[0, i].set_xscale('log')
    # ax[1, i].set_xscale('log')
    ax[1, i].plot(rep_range / ref_rep, deltaF, 'k-')
    ax[0, i].set_yscale('log')
    ax[0, i].set_ylabel('fold-change', fontsize=8)
    ax[1, i].set_ylabel('$\Delta F$ [$k_BT$]', fontsize=8)

for i, a in enumerate(ax.ravel()):
    if i <= 3:
        a.set_xlabel('repressors per cell', fontsize=8)
    else: 
        a.set_xlabel('$R_C / R_{ref}$', fontsize=8)



# Plot the explanatory points. 
ax[0, -1].grid(False)
ax[1, -1].grid(False)
ax[0, -1].fill_between(rep_range, example_fc[2], 1.05, color=colors['light_red'],
            alpha=0.5)
ax[0, -1].fill_between(rep_range, example_fc[2], -.05, color=colors['light_green'],
            alpha=0.5)
ax[1, -1].fill_betweenx(np.linspace(-5, 5, 200), 1, 4.5, 
                    color=colors['light_red'], alpha=0.5)
ax[1, -1].fill_betweenx(np.linspace(-5, 5, 100), 0, 0.99, 
                    color=colors['light_green'], alpha=0.5)
for i, r in enumerate(example_reps):
    ax[0, -1].plot(r, example_fc[i], 'o', markerfacecolor=example_facecolors[r],
            markeredgecolor=example_edgecolors[r], markeredgewidth=0.75)
    ax[1, -1].plot(r / ref_rep, example_delF[i], 'o', markerfacecolor=example_facecolors[r],
            markeredgecolor=example_edgecolors[r], markeredgewidth=0.75)

ax[1, -1].set_xscale('log')
for i in range(2):
    for j in range(0, 3):
        ax[0, j].set_xlim([2, 300])
        ax[1, j].set_xlim([.01, 2.5])
        ax[1, j].set_xscale('log')
        ax[1, j].set_xticks([0.1, 0.5, 1, 1.5, 2])
        ax[0, j].set_ylim([1E-3, 1.1])
for i in range(4):
    ax[1, i].set_xticks([0.1, 1, 10])

ax[1, -1].set_xlim([0.1, 5])

plt.tight_layout()
plt.savefig('../../figs/Fig4_delF_carbon_quality.pdf', bbox_inches='tight', 
            facecolor='white')


#%%
