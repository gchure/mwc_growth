#%%
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import mwc.viz
import mwc.model
import mwc.stats
colors, color_list = mwc.viz.personal_style()

# Load the data sets and restrict
pooled_entropy = pd.read_csv('../../data/pooled_entropic_parameter_samples.csv')
entropy = pd.read_csv('../../data/entropic_parameter_samples.csv')
stats = pd.read_csv('../../data/DNA_binding_energy_summary.csv')
stats = stats[(stats['carbon']=='glucose')]

#%%
# Set up the figure canvas
fig, ax = plt.subplots(3, 3, figsize=(4, 4), dpi=100)

# Format the axes
ax[0, 1].axis(False)
ax[0, 2].axis(False)
ax[1, 2].axis(False)
ax[0, 0].yaxis.grid(False)
ax[0, 0].set_yticks([])
ax[1, 1].yaxis.grid(False)
ax[1, 1].set_yticks([])
ax[2, 2].yaxis.grid(False)
ax[2, 2].set_yticks([])
ax[0, 0].set_xticklabels([])
ax[1, 0].set_xticklabels([])
ax[1, 1].set_xticklabels([])
ax[2, 1].set_yticklabels([])

# Set the titles of the marginals for clarity
mwc.viz.titlebox(ax[0, 0], '$\Delta S_{RA}$', boxsize="15%", pad=0.03, color=colors['black'])
mwc.viz.titlebox(ax[1, 1], '$\Delta S_{AI}$', boxsize="15%", pad=0.03, color=colors['black'])
mwc.viz.titlebox(ax[2, 2], '$\sigma$', boxsize="15%", pad=0.03, color=colors['black'])

# Add the axis labels
ax[1, 0].set_ylabel('$\Delta S_{AI}$ [$k_BT / K$]')
ax[2, 0].set_ylabel('$\sigma$')
ax[2, 0].set_xlabel('$\Delta S_{RA}$ [$k_BT / K$]')
ax[2, 1].set_xlabel('$\Delta S_{AI}$ [$k_BT / K$]')
ax[2, 2].set_xlabel('$\sigma$')


# Define the bins for the marginal histograms
RA_bins = np.linspace(0, 0.3, 50)
AI_bins = np.linspace(-0.3, 0.3, 50)
sigma_bins = np.linspace(0.3, 0.9, 50)

# Plot the pooled results
pooled_S_RA = pooled_entropy[pooled_entropy['parameter']=='delta_S']['value'].values[::5]
pSRA_hist, _= np.histogram(pooled_S_RA, RA_bins, density=True)
pooled_S_AI = pooled_entropy[pooled_entropy['parameter']=='delta_S_vib']['value'].values[::5]
pSAI_hist, _ = np.histogram(pooled_S_AI, AI_bins, density=True)
pooled_sigma = pooled_entropy[pooled_entropy['parameter']=='sigma']['value'].values[::5]
sig_hist, _ = np.histogram(pooled_sigma, sigma_bins, density=True)

# Joints
ax[1, 0].plot(pooled_S_RA, pooled_S_AI, 'k.', ms=0.4, alpha=0.5)
ax[2, 0].plot(pooled_S_RA, pooled_sigma, 'k.', ms=0.4, alpha=0.5)
ax[2, 1].plot(pooled_S_AI, pooled_sigma, 'k.', ms=0.4, alpha=0.5)

# Marginals
ax[0, 0].step(RA_bins[:-1], pSRA_hist, 'k-', lw=1)
ax[1, 1].step(AI_bins[:-1], pSAI_hist, 'k-', lw=1)
ax[2, 2].step(sigma_bins[:-1], sig_hist, 'k-', lw=1)

# Plot the 32 results
S_RA_32 = entropy[(entropy['parameter']=='delta_S') & 
                  (entropy['temp']==32)]['value'].values[::5]
SRA32_hist, _= np.histogram(S_RA_32, RA_bins, density=True)
S_AI_32 = entropy[(entropy['parameter']=='delta_S_vib') & 
                  (entropy['temp']==32)]['value'].values[::5]
SAI32_hist, _= np.histogram(S_AI_32, AI_bins, density=True)
sigma_32 = entropy[(entropy['parameter']=='sigma') & 
                  (entropy['temp']==32)]['value'].values[::5]
sigma32_hist, _= np.histogram(sigma_32, sigma_bins, density=True)

# Joints
ax[1, 0].plot(S_RA_32, S_AI_32, '.', color=colors['blue'], ms=0.4, alpha=0.5)
ax[2, 0].plot(S_RA_32, sigma_32, '.', color=colors['blue'], ms=0.4, alpha=0.5)
ax[2, 1].plot(S_AI_32, sigma_32, '.', color=colors['blue'], ms=0.4, alpha=0.5)

# Marginals
ax[0, 0].step(RA_bins[:-1], SRA32_hist, '-', color=colors['dark_blue'], lw=1)
ax[1, 1].step(AI_bins[:-1], SAI32_hist, '-', color=colors['dark_blue'], lw=1)
ax[2, 2].step(sigma_bins[:-1], sigma32_hist, '-', color=colors['dark_blue'], lw=1)


# Plot the 42 results
S_RA_42 = entropy[(entropy['parameter']=='delta_S') & 
                  (entropy['temp']==42)]['value'].values[::5]
SRA42_hist, _= np.histogram(S_RA_42, RA_bins, density=True)
S_AI_42 = entropy[(entropy['parameter']=='delta_S_vib') & 
                  (entropy['temp']==42)]['value'].values[::5]
SAI42_hist, _= np.histogram(S_AI_42, AI_bins, density=True)
sigma_42 = entropy[(entropy['parameter']=='sigma') & 
                  (entropy['temp']==42)]['value'].values[::5]
sigma42_hist, _= np.histogram(sigma_42, sigma_bins, density=True)

# Joints
ax[1, 0].plot(S_RA_42, S_AI_42, '.', color=colors['red'], ms=0.4, alpha=0.5)
ax[2, 0].plot(S_RA_42, sigma_42, '.', color=colors['red'], ms=0.4, alpha=0.5)
ax[2, 1].plot(S_AI_42, sigma_42, '.', color=colors['red'], ms=0.4, alpha=0.5)

# Marginals
ax[0, 0].step(RA_bins[:-1], SRA42_hist, '-', color=colors['dark_red'], lw=1)
ax[1, 1].step(AI_bins[:-1], SAI42_hist, '-', color=colors['dark_red'], lw=1)
ax[2, 2].step(sigma_bins[:-1], sigma42_hist, '-', color=colors['dark_red'], lw=1)

plt.subplots_adjust(wspace=0.05, hspace=0.05)
plt.savefig('../../figs/FigSX_entropy_cornerplot.pdf', bbox_inches='tight', 
            facecolor='white')




