#%%
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import mwc.viz
import scipy.io
import mwc.image
import scipy.ndimage
import scipy.signal
import skimage.morphology
import skimage.filters
import skimage.measure
import skimage.io
import glob
colors, color_list = mwc.viz.personal_style()

#%%
# Find the root folders for each snapshot
folders = glob.glob('../../data/example_mats/*')
fig, ax = plt.subplots(1, 2, figsize=(5, 2.5), dpi=100)

for a in ax:
    a.set_ylabel('length [µm]')
    a.xaxis.grid(False)

locs = {32:0, 37: 20, 42: 40, 'acetate': 0, 'glycerol': 20, 'glucose': 40}
temp_colors = {32: colors['blue'], 37:colors['purple'], 42: colors['red']}
carb_colors = {'acetate':colors['dark_brown'], 'glucose':colors['purple'], 
               'glycerol':colors['green']}
for f in folders:
    # Determine the temperature
    carbon, temp, _ = f.split('/')[-1].split('_')
    temp = int(temp[:-1])

    # Determine the axis
    if carbon != 'glucose':
        _ax = [ax[0]]
        color = carb_colors[carbon]
        loc = [locs[carbon]]
    if temp != 37:
        _ax = [ax[1]]
        color = temp_colors[temp]
        loc = [locs[temp]]
    if (carbon == 'glucose') & (temp==37):
        _ax = ax
        color = colors['purple']
        loc = [locs[carbon], locs[temp]]

    # Get the mat files
    mats = glob.glob(f'{f}/*.mat')

    # Instantiate a data frame for easy calculation of the mean. 
    dfs = [] 
    for j, m in enumerate(mats):
        mat = scipy.io.loadmat(m)
        seg = mat['CellA'][0][0][0][0][3]
        lab = skimage.measure.label(seg)
        props = skimage.measure.regionprops(lab)
        prop = [p for p in props]
        o = props[0].orientation
        rot = scipy.ndimage.rotate(seg, -o * 180/np.pi)
        conts = skimage.measure.find_contours(rot, 0)[0]
        _conts_x = conts[:,0] - np.min(conts[:, 0])
        _conts_y = conts[:, 1] - np.min(conts[:, 1])

        if (np.sum(seg) < 1000) & (np.sum(seg) > 50):
            # Circularly permute the contour from the minimum x
            ind = np.where(_conts_y == 0)[0][0]
            perm_conts_y = np.roll(_conts_y, -ind)
            filt_conts_y = scipy.signal.savgol_filter(perm_conts_y, polyorder=2, window_length=15)
            perm_conts_x = np.roll(_conts_x, -ind)
            filt_conts_x = scipy.signal.savgol_filter(perm_conts_x, polyorder=2, window_length=15)
            _df = pd.DataFrame().from_dict({'x':filt_conts_x, 'idx':np.arange(len(conts)),
                                          'y':filt_conts_y * 0.065})
            _df['cell_id'] = j
            dfs.append(_df)
            for i, a in enumerate(_ax):
                a.plot(filt_conts_x + loc[i], filt_conts_y * 0.065, lw=0.15, 
                        alpha=1, color=color)


ax[0].set_xlim([0, 60])    
ax[0].set_xticks([10, 30, 50])
ax[0].set_xticklabels(['acetate', 'glycerol', 'glucose'], fontsize=8)
ax[1].set_xlim([0, 60])    
ax[1].set_xticks([10, 30, 50])
ax[1].set_xticklabels(['32° C', '37° C', '42° C'], fontsize=8)
plt.tight_layout()
plt.savefig('../../figs/cell_length_traces.svg', bbox_inches='tight')


#%%
