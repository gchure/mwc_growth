#%%
#%%[markdown]
# # Exploratory Data Analysis for Calculating Repressor Copy Number
#%%
import numpy as np 
import pandas as pd
import bokeh.io 
import bokeh.plotting
import bokeh_catplot as bkcat 
import scipy.optimize
import mwc.stats 
import mwc.bayes 
import mwc.viz
import bokeh.models
import bokeh.transform
import tqdm
import bokeh.palettes
import scipy.stats
import scipy.special
import statsmodels.tools.numdiff as smnd
colors, color_list = mwc.viz.bokeh_theme()
bokeh.io.output_notebook()

#%% [markdown]
# In this notebook, I explore all processing steps and inference for determining
# a fluorescence calibration factor. Here, we will take the pre-processed data
# (extracted from the `clist.mat` files in
# `code/processing/batch_processing.py`l)
# and explore any and all filtering steps that have to be performed to get a
# proper estimate of the mean autofluorescence background for both channels. #
# ## Exploring Size Dependence
# One of the first things we can do is explore the cell size distribution of the
# each condition and see how it scales with growthrate. As Zofii so kindly
# determined, the approximate growth rates (ignoring error for now) for each
# condition are given as follows and defined programmatically in the next code
# cell. 
#
# |**Carbon Source** | **Temperature (°C)** | **Growth Rate \[inv. min\]** |**Doubling Time \[min\]**|
# |:--:|:--:|:--:|:--:|
# | glucose | 37 | 0.01 | 65 |
# | glycerol | 37 | 0.006 | 106 | 
# | acetate | 37 | 0.003 | 201 |
# | glucose | 32 | 0.007 | 92 |
# | glucose | 42 | 0.008 | 86 |
# 

#%%
# Define the growth rates. 
carbon_growth = {'glucose': 0.01, 'glycerol':0.006, 'acetate':0.003}
temp_growth = {37: 0.01, 32:0.007, 42:0.008}

# Load the intensity data sets
snaps = pd.read_csv('../../data/raw_compiled_snaps.csv')

# Define the interpixel distance and convert area to square microns
IP_DIST = 0.065 # in nm / pix
snaps['area_um'] = snaps['area_birth'] * IP_DIST**2
# %%
# Look at the distribution of areas for each data source
carbon_var = snaps[snaps['temp']==37]
temp_var = snaps[snaps['carbon']=='glucose']

# Generate the two distributions using bokeh_catplot
carb_plot = bkcat.histogram(carbon_var, 'carbon', 'area_um', palette=color_list)
temp_plot = bkcat.histogram(temp_var, 'temp', 'area_um', palette=color_list)
row = bokeh.layouts.row(carb_plot, temp_plot)
carb_plot.title.text = 'carbon source variation'
temp_plot.title.text = 'temperature variation'
bokeh.io.show(row)

#%% [markdown]
# Looking at the distributions, there is certainly a spread in cell size,
# although the distributions significantly overlap. More importantly, it seems
# like there are some abnormally large cells (> 10 µm) and abnormally small
# cells (< 1 µm) that are likely segmentation errors or sick cells. 
# Another useful quantity to examine is the aspect ratio. Acetate cells should
# have a large aspect ratio (length / width) than the glucose. 
#
#%%
carb_plot = bkcat.ecdf(carbon_var, 'carbon', 'aspect_ratio', palette=color_list)
temp_plot = bkcat.histogram(temp_var, 'temp', 'aspect_ratio', palette=color_list)
bokeh.io.show(bokeh.layouts.row(carb_plot, temp_plot))


#%%
# Impose area bounds on the samples.
snaps_filtered = mwc.process.morphological_filter(snaps, IP_DIST, [1, 5], 
                                                  ar_bounds=[0.1, 0.5])
# Again look at the distributions
carbon_var = snaps_filtered[snaps_filtered['temp']==37]
temp_var = snaps_filtered[snaps_filtered['carbon']=='glucose']

# Set up the plots and add titles
carb_plot = bkcat.histogram(carbon_var, 'carbon', 'area_um', palette=color_list)
temp_plot = bkcat.histogram(temp_var, 'temp', 'area_um', palette=color_list)
row = bokeh.layouts.row(carb_plot, temp_plot)
carb_plot.title.text = 'carbon source variation (filtered)'
temp_plot.title.text = 'temperature variation (filtered)'
carb_plot.xaxis.axis_label = 'carbon source'
temp_plot.xaxis.axis_label = 'temperature (°C)'
bokeh.io.show(row)
#%% [markdown]
# Again, there is a lot of overlap in the cell size. What about the aspect
# ratio?

#%%
snaps_filtered
#%%
# Assign growthrates in the dataframe
for g, d in snaps_filtered.groupby(['carbon', 'temp']):
    if g[0] == 'glucose':
        rate = temp_growth[g[1]]
    else:
        rate = carbon_growth[g[0]]
    snaps_filtered.loc[(snaps_filtered['carbon']==g[0]) & 
                        (snaps_filtered['temp']==g[1]), 'growth_rate'] = rate

# %%
# Compute the mean and standard deviation of the sizes versus the growth rate. 
p = bokeh.plotting.figure(width=400, height=300, x_axis_label='growth rate [inv. min]',
                        y_axis_label='area [sq. µm]', x_range=[0.002,0.015])

for g, d in snaps_filtered.groupby(['carbon', 'temp', 'growth_rate']):

    # Do some preprocessing of the data to make annotation easier
    d = d.copy()
    d['label'] = f'{g[0]}, {g[1]} °C'

    # Color our 'reference' state
    if (g[0] == 'glucose') & (g[1]==37):
        glyph = p.square
        fill = colors['light_orange']
        line = colors['orange']

    # Use a different glyph for the temperature variation
    elif g[1] != 37:
        glyph = p.triangle
        fill = colors['light_purple']
        line = colors['purple']

    # Plot the carbon source variation as a circle
    else:
        glyph = p.circle
        fill = colors['light_grey']
        line = colors['black']

    # Make a new dataframe for easier annotation. 
    _df = pd.DataFrame()
    _df = _df.append({'label':f'{g[0]}, {g[1]} °C', 
                       'growth_rate':d['growth_rate'].mean(),
                       'area_um':d['area_um'].mean(), 
                       'rate_min': d['growth_rate'].mean() - d['growth_rate'].std(),
                       'rate_max': d['growth_rate'].mean() + d['growth_rate'].std(),
                       'area_min': d['area_um'].mean() - d['area_um'].sem(),
                       'area_max': d['area_um'].mean() + d['area_um'].sem()},
                       ignore_index=True)

    # Populate the canvas
    glyph('growth_rate', 'area_um', line_color=line,
           fill_color=fill, size=8, source=_df)
    p.segment(x0='growth_rate', x1='growth_rate', y0='area_min', y1='area_max',
             color=line, source=_df)
    labels = bokeh.models.LabelSet(x='growth_rate', y='area_um',
                                    text='label', level='glyph',
                                    render_mode='canvas', source=bokeh.models.ColumnDataSource(_df),
                                    text_font_size='10pt', x_offset=7)
    p.add_layout(labels)
bokeh.io.show(p)
#%%[markdown]
# That looks pretty linear with respect to carbon source variation. It's less
# clear what the relationship is with respect to the temperature variation.
# I should think about the scaling of the the average area with the range of the
# growth rate. What I am observing are pretty small differences. Next, we'll
# look at some of the intensities to make sure they are behaving as expected. 
#
# ## Exploring Intensity Distributions
# There are three different strains being used here. One is an autofluorescence
# control which we will use to figure out the baseline fluorescence in both the
# YFP and mCherry channels. Another one is the constitutively expressing YFP
# strain which should be the brightest in YFP, but have approximately the same
# mCherry expression, and (finally) our dilution strain. 
#
# We will first consider the expression of the ∆LacI strains in both YFP and
# mCherry. As we know from the Schaecter and Hwa papers, there should be a
# linear relationship between growth rate and total protein number, although it
# is not clear how the intensity will scale. We should (hopefully) see that the
# autofluorescence is constant across growth conditions. 
# 
#%%
# Restrict the data sets to delta lacI
delta_carb_var = carbon_var[carbon_var['strain']=='auto']
delta_temp_var = temp_var[temp_var['strain']=='auto']

# Set up the plots
carb_plot = bkcat.histogram(delta_carb_var, 'carbon', 'fluor1_mean_death',
                           palette=color_list) 
temp_plot = bkcat.histogram(delta_temp_var, 'temp', 'fluor1_mean_death',
                            palette=color_list) 

# Assign labels
carb_plot.title.text = 'carbon source variation'
temp_plot.title.text = 'temperature variation'
carb_plot.xaxis.axis_label = 'mean YFP pixel intensity (∆lacI)'
temp_plot.xaxis.axis_label = 'mean YFP pixel intensity (∆lacI)'

# Set the layout and display. 
row = bokeh.layouts.row(carb_plot, temp_plot)
bokeh.io.show(row)
#%% [markdown]
# There appears to be some bimodality in the mean intensity with a bunch of
# dark stuff. There also appears to be no real trend in the *intensity* with
# changing carbon source, but this does not necessarily mean the *expression*
# is unchanged as variations in the cell chemistry can change how bright a
# single fluorophore is. For the temperature variation, there is definitely a
# trend where lower temperatures leads to increased brightness. 
#
# Let's now look at the mCherry fluorescence of the ∆LacI strains. It is
# possible that there is variation resulting either from experimental
# inconsistencies or some weird condition dependent autofluorescence. 

#%%
delta_carb_var = carbon_var[carbon_var['strain']=='delta']
delta_temp_var = temp_var[temp_var['strain']=='delta']

# Set up the plots
carb_plot = bkcat.histogram(delta_carb_var, 'carbon', 'fluor2_mean_death',
                           palette=color_list) 
temp_plot = bkcat.histogram(delta_temp_var, 'temp', 'fluor2_mean_death',
                            palette=color_list) 

# Assign labels
carb_plot.title.text = 'carbon source variation'
temp_plot.title.text = 'temperature variation'
carb_plot.xaxis.axis_label = 'mean mCherry pixel intensity (∆lacI)'
temp_plot.xaxis.axis_label = 'mean mCherry pixel intensity (∆lacI)'

# Set the layout and display. 
row = bokeh.layouts.row(carb_plot, temp_plot)
bokeh.io.show(row)

#%%[markdown]
# Yikes, well there appears to be two distributions of mCherry background
# intensity, varying by about 100 counts per pixel for both. Let's see if this
# holds true for the autofluorescence samples (where there should be no
# fluorophores)

#%%
auto_carb_var = carbon_var[carbon_var['strain']=='auto']
auto_temp_var = temp_var[temp_var['strain']=='auto']

# Set up the plots
carb_plot = bkcat.histogram(auto_carb_var, 'carbon', 'fluor2_mean_death',
                           palette=color_list) 
temp_plot = bkcat.histogram(auto_temp_var, 'temp', 'fluor2_mean_death',
                            palette=color_list) 

# Assign labels
carb_plot.title.text = 'carbon source variation'
temp_plot.title.text = 'temperature variation'
carb_plot.xaxis.axis_label = 'mean mCherry pixel intensity (autofluorescence)'
temp_plot.xaxis.axis_label = 'mean mCherry pixel intensity (autofluorescence)'

# Set the layout and display. 
row = bokeh.layouts.row(carb_plot, temp_plot)
bokeh.io.show(row)

#%% [markdown]
# Yep, it seems like the bimodaility is there as well! That's certainly a pain
# in the ass. Let's check that it's not alos present in the YFP
# autofluorescence. 
#%%
# Set up the plots
carb_plot = bkcat.histogram(auto_carb_var, 'carbon', 'fluor1_mean_death',
                           palette=color_list) 
temp_plot = bkcat.histogram(auto_temp_var, 'temp', 'fluor1_mean_death',
                            palette=color_list) 

# Assign labels
carb_plot.title.text = 'carbon source variation'
temp_plot.title.text = 'temperature variation'
carb_plot.xaxis.axis_label = 'mean YFP pixel intensity (autofluorescence)'
temp_plot.xaxis.axis_label = 'mean YFP pixel intensity (autofluorescence)'

# Set the layout and display. 
row = bokeh.layouts.row(carb_plot, temp_plot)
bokeh.io.show(row)
#%% [markdown]
# Damn, it's there as well. Hopefully this arises from variations in the
# experimental parameters rather than in the actual strains themselves. To
# check, we choose one condition (say, the ∆lacI sample grown on acetate)  and
# plot the mCherry intensity distribution as a function of the date. 
#%%
delta_acetate_var = delta_carb_var[delta_carb_var['carbon']=='acetate']
acetate_plot = bkcat.ecdf(delta_acetate_var, 'date', 'fluor2_mean_death',
      palette=bokeh.palettes.Colorblind8, 
      height=400, width=600, x_axis_type='log')
acetate_plot.title.text = '∆lacI, acetate, 37°C'
acetate_plot.xaxis.axis_label = 'mean mCherry pixel intensity (autofluorescence)'
acetate_plot.legend.click_policy = 'hide'
bokeh.io.show(acetate_plot)

#%%[markdown]
# Note that in the above plot,t he legend entries are clickable such that it's
# easier to see what is changing. IT looks like the autofluorescence intensity
# varies day-to-day with no real clear relationship to the day. This means while
# doing the autofluorescence subtraction, I should really be sure to use that
# particular day and run number. As there are (for some reason) *very* bright
# cells on some of the days, it will be better to use the median rather than the
# mean of the distribution to perform the subtraction. 
# 
# For my own sanity, let's check that this holds true for the true
# autofluorescence samples before I do anything else. 
# 
#%%
# Check to see if this holds true for the autofluorescence strain
auto_acetate_var = auto_carb_var[auto_carb_var['carbon']=='acetate']
acetate_plot = bkcat.ecdf(auto_acetate_var, 'date', 'fluor2_mean_death',
      palette=bokeh.palettes.Colorblind8, 
      height=400, width=600, x_axis_type='log')
acetate_plot.title.text = 'auto, acetate, 37°C'
acetate_plot.xaxis.axis_label = 'mean mCherry pixel intensity (autofluorescence)'
acetate_plot.legend.click_policy = 'hide'
bokeh.io.show(acetate_plot)
#%%[markdown]
# IN the autofluorescence state, there seems to be one day in which the
# distribution is bimodal. That set will be dropped from the analysis completely
# I think. For my records, that day is `20181022`. Let's just drop that from the
# data set now

#%%
# Remove the problematic day
approved_snaps = snaps_filtered[snaps_filtered['date'] != 20181022]

#%%[markdown]
# With a solid dataset in hand, we will go through each date and run number and 
# subtract the background for each channel. 
#%%
approved_dfs = []
for g, d in approved_snaps.groupby(['carbon', 'temp', 'run_number', 'date']):
    d = d.copy()
    auto = d[d['strain']=='auto']
    median_mch = auto['fluor1_mean_death'].median()
    median_yfp = auto['fluor2_mean_death'].median()

    # Subtract
    d['fluor1_mean_sub'] = d['fluor1_mean_death'] - median_mch
    d['fluor2_mean_sub'] = d['fluor2_mean_death'] - median_yfp
    approved_dfs.append(d)
approved_snaps = pd.concat(approved_dfs)

#%%[markdown]
# I think with the current set of data, that's all that I can really say moving
# forward and computing the calibration factor so I can look at the actuall
# scaling of LacI expression. 
#


#%%[markdown]
# ## Exploring correlated expression
# Regardless of the condition, increasing mCherry intensity should negatively
# correlate with YFP intensity. We can check that for all dilution circuit cells

#%%
p = bokeh.plotting.figure(
                         x_axis_label='mean mCherry intensity [a.u.]',
                          y_axis_label='mean YFP intensity [a.u.]',
                          width=500, height=300)

# Only look at the dilution strain .
dilution = approved_snaps[approved_snaps['strain']=='dilution']
carb_var = dilution[dilution['temp']==37]
temp_var = dilution[dilution['carbon']=='glucose']
carb_summary = carb_var.groupby(['carbon', 'atc_ngml']).agg(('mean', 'sem'))
carb_summary['fluor1_low'] = carb_summary['fluor1_mean_sub']['mean'] - carb_summary['fluor1_mean_sub']['sem']
carb_summary['fluor1_high'] = carb_summary['fluor1_mean_sub']['mean'] + carb_summary['fluor1_mean_sub']['sem']
carb_summary['fluor2_low'] = carb_summary['fluor2_mean_sub']['mean'] - carb_summary['fluor2_mean_sub']['sem']
carb_summary['fluor2_high'] = carb_summary['fluor2_mean_sub']['mean'] + carb_summary['fluor2_mean_sub']['sem']
temp_summary = temp_var.groupby(['temp', 'atc_ngml']).agg(('mean', 'sem'))
temp_summary['fluor1_low'] = temp_summary['fluor1_mean_sub']['mean'] - temp_summary['fluor1_mean_sub']['sem']
temp_summary['fluor1_high'] = temp_summary['fluor1_mean_sub']['mean'] + temp_summary['fluor1_mean_sub']['sem']
temp_summary['fluor2_low'] = temp_summary['fluor2_mean_sub']['mean'] - temp_summary['fluor2_mean_sub']['sem']
temp_summary['fluor2_high'] = temp_summary['fluor2_mean_sub']['mean'] + temp_summary['fluor2_mean_sub']['sem']


p.circle(carb_summary['fluor1_mean_sub']['mean'], y=carb_summary['fluor2_mean_sub']['mean'],
         size=4, alpha=0.5, color=colors['purple'])
p.segment(x0=carb_summary['fluor1_mean_sub']['mean'], x1=carb_summary['fluor1_mean_sub']['mean'],
          y0=carb_summary['fluor2_low'], y1=carb_summary['fluor2_high'], color=colors['purple'])
p.segment(x0=carb_summary['fluor1_low'], x1=carb_summary['fluor1_high'],
          y0=carb_summary['fluor2_mean_sub']['mean'], y1=carb_summary['fluor2_mean_sub']['mean'], color=colors['purple'])
p.circle(temp_summary['fluor1_mean_sub']['mean'], y=temp_summary['fluor2_mean_sub']['mean'],
         size=4, alpha=0.5, color=colors['orange'])
p.segment(x0=temp_summary['fluor1_mean_sub']['mean'], x1=temp_summary['fluor1_mean_sub']['mean'],
          y0=temp_summary['fluor2_low'], y1=temp_summary['fluor2_high'], color=colors['orange'])
p.segment(x0=temp_summary['fluor1_low'], x1=temp_summary['fluor1_high'],
          y0=temp_summary['fluor2_mean_sub']['mean'], y1=temp_summary['fluor2_mean_sub']['mean'], color=colors['orange'])
bokeh.io.show(p)
#%%[markdown]
# ## Exploring the Lineage Data
# Now that the snapshot data seems to jibe with my intuition of how things
# should behave, I can now more on and work with examining the fluctuations. To
# begin, we will load the lineage data set and examine the area distributions.
# They should hopefully be similar to the snapshots, although maybe a bit wider
# as we are actually letting them divide (as is part of the experiment.)
#%%
# Load the lineages.
lineages = pd.read_csv('../../data/raw_compiled_lineages.csv')

# Remove the problematic day
# lineages = lineages[lineages['date']!=20181022]

# Convert the error frames from nan to num
lineages['error_frame'] = np.nan_to_num(lineages['error_frame'].values)

# Drop all measurements with an error frame. 
lineages = lineages[lineages['error_frame']==0]

# Convert daughter areas to sq micron. 
lineages['area_1_um'] = lineages['area_1'] * IP_DIST**2
lineages['area_2_um'] = lineages['area_2'] * IP_DIST**2

# Separate by carbon and temperature source variation
lin_carb_var = lineages[lineages['temp']==37]
lin_temp_var = lineages[lineages['carbon']=='glucose']

# Apply the area filter and remove 20181022.
carb_plot = bkcat.histogram(lin_carb_var, 'carbon', 'area_1_um', palette=color_list)
temp_plot = bkcat.histogram(lin_temp_var, 'temp', 'area_1_um', palette=color_list)

# Add labels
carb_plot.title.text = 'carbon variation'
temp_plot.title.text = 'temperature variation'
carb_plot.xaxis.axis_label = 'area [sq. µm]'
temp_plot.xaxis.axis_label = 'area [sq. µm]'

# Set the layout and show the plot
row = bokeh.layouts.row(carb_plot, temp_plot)
bokeh.io.show(row)

 #%%[markdown]
# As I expected, the distribution is a bit wider than for the snapshots. For
# this reason, we'll expand the bounds a bit such that we get everything that is
# important. We'll go with bounds of 0.5 to 8 sq µm.
#%%
# Morphologically filter the cells
lin_filt = lineages[(lineages['area_1_um'] >= 0.5) & (lineages['area_2_um'] >= 0.5) 
       & (lineages['area_1_um'] <= 5) & (lineages['area_2_um'] <= 5)].copy()
# %%
# With the lineages filtered, let's now look at the distribution of fluorescence
# between the two daughter cells. As is demanded by our assumption of binomial
# partitioning, we would expect the average fluorescence of a daughter to be
# half of the summation. We can check this in the mCherry fluorescence channel. 
#%%
# Only consider the pairs where there was partitioned intensities.
lin_int = lin_filt[(lin_filt['I_1'] > 0) & (lin_filt['I_2'] > 0)].copy()

# Compute the total integrated cell intensities.
lin_int['I_1_tot'] = lin_int['I_1'] * lin_int['area_1']
lin_int['I_2_tot'] = lin_int['I_2'] * lin_int['area_2']
lin_int['frac_int_1'] = lin_int['I_1_tot'] / (lin_int['I_1_tot'] +
                                              lin_int['I_2_tot'])
lin_int['frac_int_2'] = lin_int['I_2_tot'] / (lin_int['I_1_tot'] +
                                             lin_int['I_2_tot'])
# %%
# Instantiate the figure canvas
p = bokeh.plotting.figure(x_axis_label='fractional intensity', y_axis_label='count',
                        width=400, height=400)

# Compute the histogram
frac1_hist, frac1_bins = np.histogram(lin_int['frac_int_1'], bins=100)
frac2_hist, frac2_bins = np.histogram(lin_int['frac_int_2'], bins=100)

# populate the canvas and display
p.quad(bottom=np.zeros(len(frac1_bins[:-1])), right=frac1_bins[1:],  left=frac1_bins[:-1],
        top=frac1_hist,  color=colors['purple'], alpha=1, legend='daughter cell 1')
p.quad(bottom=np.zeros(len(frac2_bins[:-1])), right=frac2_bins[1:],  left=frac2_bins[:-1],
        top=frac2_hist,  color=colors['orange'], alpha=0.5, legend='daughter cell 2')
bokeh.io.show(p)
#%%[markdown]
# Now that is one symmetric distribution! they are partitioned basically right
# on average of 0.5, so the binomial assumption seems to hold true across all
# conditions. Any deviation would appear as shoulders in the distributions. 
#
#  ### Subtracting autofluorescence
# Our next task will be subtracting off the autofluorescence intensity from each
# cell. As described in the previous section, the autofluorescence will need to
# be subtracted off on a day-by-day basis. 
#%%
# Subtract off the autofluorescence from the `lin_int` datastructure
subtracted_lineages = []
for g, d in lin_int.groupby(['date', 'carbon', 'temp', 'run_number']):
    d = d.copy()
    # Isolate the autofluorescence sample from approved snaps
    bg = approved_snaps[(approved_snaps['date']==g[0]) & 
                          (approved_snaps['carbon']==g[1]) & 
                          (approved_snaps['temp']==g[2]) & 
                          (approved_snaps['run_number']==g[-1])&
                          (approved_snaps['strain']=='delta')]

    # Compute the median mcherry pixel intensity 
    median_mch = auto['fluor2_mean_death'].median()

    # Subtract it from both daughter cells. 
    d['I_1_sub'] = (d['I_1']  -  median_mch) * d['area_1']
    d['I_2_sub'] = (d['I_2'] -  median_mch) * d['area_2']

    # Append the new dataframe to the storage list
    subtracted_lineages.append(d)
lin_sub = pd.concat(subtracted_lineages)
#%%[markdown]
# With the autofluorescence background subtracted, let's take a look at the
# total distribution of intensities (for daughter 1 and 2) to see what fraction
# of intensities we have below zero.

#%%
# Generate ecdfs of the two intensities
y =  np.arange(0, len(lin_sub)) / len(lin_sub)
cell1_x = np.sort(lin_sub['I_1_sub'].values)
cell2_x = np.sort(lin_sub['I_2_sub'].values)

# Set up the figure canvas
p = bokeh.plotting.figure(width=400, height=300, x_axis_label='total YFP intensity',
                        y_axis_label='cumulative distribution')

# Populate the canvas 
p.step(x=cell1_x, y=y, color=colors['purple'], legend='daughter 1')
p.step(x=cell2_x, y=y, color=colors['orange'], legend='daughter 2')
bokeh.io.show(p)


#%%[markdown]
# Looking at teh distribution, it seems like about 20% of the values fall below
# zero, indicating that the protein expression is too low to be reliably
# measured. in these cases, we will remove any lineage pairings in which at
# least one of the daughter cells drops below zero in its intensity. 
#%%
# Drop the negative cells. 
lin_final = lin_sub[(lin_sub['I_1_sub'] >= 0) & (lin_sub['I_2_sub'] >= 0) &
                    ((lin_sub['I_1_sub'] != 0) & (lin_sub['I_2_sub'] !=0))].copy()

lin_final.to_csv('../../data/analyzed_lineages.csv', index=False)
#%%[markdown]
# ## Estimating a Fluorescence Calibration Factor
# With a thoroughly explored data set in place,we can now turn towards trying to
# calculate a fluorescence calibraton factor. As a reminder, we posit that
# protein production has ceased (after removal of ATC through repeated washings)
# and that there is no significant protein degradation. We can state these
# assumptions mathematically as 
#
# $$ I_\text{tot} = I_1 + I_2 \tag{1}, $$
# in which $I_1$ and $I_2$ are the intensities of daughter cell 1 and 2,
# repspectively. We assume that all fluorescent proteins are the same (which is
# in itself not a valid assumption) in that they emit a constant number of
# photons per molecule. This assumption allows us to relate the observed
# intensity of a cell to its repressor copy number by 
#
# $$I_\text{tot} = \alpha N_\text{tot} = \alpha \left( N_1 + N_2\right)$$.
#
# As I've derived in my notes, we can arrive at a very simple realationship for
# the determination of this fluorescence calibration factor $\alpha$ by noting
# that 
#
# $$\langle\left(I_1 - I_2\right)^2\rangle = \alpha \left(I_1 + I_2\right)$$.
# Thus, there should be a linear relationship between teh fluctuations in
# intensity and the sum total fluorescence with a slope of $\alpha$. 
#
# ### A Bayesian Approach
# While I could bin the data and fit a line to the means, I'd rather take a
# Bayesian approach to this estimation. For simplicity (at least to start with)
# will make the assumption that measurement noise is small compared to the noise
# resulting from the binomial partitioning of the proteins. Using Bayes' rule, I
# write that 
#
# $$ g(\alpha\,\vert\,[I_1, I_2]) \propto f([I_1]\,\vert\, [I_2], \alpha) g(\alpha)$$
#
# I will lookaback at my notes for teh full derivation (as I don't want to write
# it all out now), but the deterministic posterior for this problem is 
# 
#$$ g(\alpha\,\vert [I_1, I_2]) =g(\alpha){1 \over\alpha^k}\prod\limits_i^k{{\Gamma({I_1 + I_2\over \alpha} + 1)} \over{\Gamma({I_1 \over \alpha} + 1) \Gamma ({I_2\over\alpha}+1)}}2^{-{I_1+I_2\over\alpha}}.$$
#This is a relatively tidy expression with only a few annoying features. The
#first is that it makes some assumptions I know are not necessarily perfect and
#secondly, I have to choose a prior on $\alpha$ for which I have no good
#intuition *a priori*. What's really nice about this formulation is that it does
#not rely at all on computing sums or fluctuations. Rather, it takes every
#single cell division as its own experiment.  Ultimately, I think I'd rather
#takea hierarchical approach to this problem and model a global calibration factor.
#
# Let's now look at a few of the data sets I have in the lineage measurements
# and just directly plot the log posterior. Below, I will code up the log
# posterior (even though I already have this done).
#%%
# Define the log posterior function
def log_posterior(alpha, I1, I2, negative=False):
    """
    Computes the log posterior of a deterministic model for estimation of a
    fluorescence calibration factor. 

    Parameters
    ----------
    alpha : float
        Value of the calibration factor on which to estimate the value of the
        log posterior
    I1 : 1d-array, float 
        Integrated intensity values for daughter cell 1
    I2 : 1d-array, float 
        Integrated intensity values for daughter cell 2
    negative: bool
        If true, the negative log posterior is returned. Default is False.

    Returns
    -------
    logp: float
        Value of the log posterior evaluated at the provided value for alpha.
    """

    # Set the value of the prefactor
    if negative==True:
        prefactor = -1
    else: 
        prefactor = 1

    # Ensure there are no negatice values of I1 or I2
    if (I1 < 0).any() or (I2 < 0).any():
        raise ValueError("Negative values in I1 or I2")

    # Compute the approximate repressor copy number based on teh provided alpha
    n1 = I1 / alpha
    n2 = I2 / alpha
    ntot = (I1 + I2) / alpha
    # Code the gamma approximation of the binomial.
    binom = scipy.special.gammaln(ntot + 1).sum() -\
            scipy.special.gammaln(n1 + 1).sum() -\
            scipy.special.gammaln(n2 + 1).sum()

    # Define the log prior
    log_prior = scipy.stats.halfnorm(0, 500).logpdf(alpha)

    # Compute the partitioning probability portion
    prob = -ntot.sum() * np.log(2)

    # Compute the change of variables constant. 
    cov = -len(I1) * np.log(alpha)

    # Compute the entire log posterior 
    logp = prefactor * (prob + cov + binom + log_prior)
    return logp

# Define the range of alpha values over which to iterate
alpha_range = np.logspace(0, 4.01, 500)

# Set up a storage dataframe
post_dfs = []

# Iterate through each unique replicate and evaluate the log posterior. 
for g, d in lin_final.groupby(['carbon', 'temp', 'date', 'run_number']):
    # evaluate the log posterior
    logp = np.zeros(len(alpha_range))
    for i, a in enumerate(alpha_range):
        logp[i] = log_posterior(a, d['I_1_sub'].values, d['I_2_sub'].values)
    
    # Normalize the log posterior. 
    posterior = np.exp(logp - scipy.special.logsumexp(logp))

    # Set up the dataframe. 
    df = pd.DataFrame([])
    df['post'] = posterior
    df['log_post'] = logp
    df['alpha'] = alpha_range
    df['carbon'] = g[0]
    df['temp'] = g[1]
    df['date'] = g[2] 
    df['run_number'] = g[-1]

    # Append the dataframe to the list and move on. 
    post_dfs.append(df)

# Concatenate the posteriors.
post_df = pd.concat(post_dfs)
#
#%%[markdown]
# With the posteriors precomputed, we should be able to easily view all of the
# replicates using a colorfactor in bokeh.

#%%
# Set up the five(!) figure canvases
carb_ax = {c:bokeh.plotting.figure(width=350, height=300, x_axis_label='α [a.u. / repressor]', 
                                  y_axis_label='posterior probability', title=f'{c}, 37°C') for c in lin_final['carbon'].unique()}

temp_ax = {t:bokeh.plotting.figure(width=350, height=300, x_axis_label='α [a.u. / repressor]', 
                                  y_axis_label='posterior probability', title=f'glucose, {t}°C') for t in lin_final['temp'].unique()}

# Define a color palette
pal = bokeh.palettes.Category20_20

# Iterate through each unique posterior and plot on the appropriate axis.
for g, d in post_df[post_df['temp']==37].groupby(['carbon']):
    # Define the axis and assign an iterator for colors
    ax = carb_ax[g]
    iter = 0

    # Iterate through each date and plot the posteriors
    for _g, _d in d.groupby(['date', 'run_number']):
        ax.line(_d['alpha'], _d['post'], line_width=1, color=pal[iter])
        iter +=1
    

# Iterate through each unique posterior and plot on the appropriate axis.
for g, d in post_df[post_df['carbon']=='glucose'].groupby(['temp']):
    # Define the axis and assign an iterator for colors
    ax = temp_ax[g]
    iter = 0

    # Iterate through each date and plot the posteriors
    for _g, _d in d.groupby(['date']):
        ax.line(_d['alpha'], _d['post'], line_width=1, color=pal[iter])
        iter += 1
                
   
# Define the layout and show.
temps = bokeh.layouts.column(list(temp_ax.values()))
carbs = bokeh.layouts.column(list(carb_ax.values()))
bokeh.io.show(bokeh.layouts.row(temps, carbs))


#%%[markdown]

# The spread of the posteriors is pretty amazing from day to day! and some of
# them have pretty significant widths, meaning it will be hard to pin down a 
# solid value for the posteriors where there are not a lot of points. 
# We can get a point estimate and error for the calibration factor through
# minimization and approximating the posterior as a gaussian, which it more or
# less is. 
# 
#%%
# Find the MAP through minimization
for g, d in lin_final.groupby(['carbon', 'temp', 'date', 'run_number']):
    popt = scipy.optimize.minimize_scalar(log_posterior, [1, 1E4], args=(d['I_1_sub'], d['I_2_sub'], True))
    alpha_mu = popt.x
    hess = smnd.approx_hess([alpha_mu], log_posterior, args=(d['I_1_sub'], d['I_2_sub'], False))
    cov = -np.linalg.inv(hess)
    alpha_std = np.sqrt(cov[0])[0]

    # Add the alpha information to the lineage dataframe. 
    lin_final.loc[ (lin_final['date']==g[2]) & 
                  (lin_final['carbon']==g[0]) &
                  (lin_final['temp']==g[1]) &
                  (lin_final['run_number']==g[-1]), 
                  'alpha_opt'] = alpha_mu
    lin_final.loc[ (lin_final['date']==g[3]) & 
                  (lin_final['carbon']==g[0]) &
                  (lin_final['temp']==g[1])  &
                  (lin_final['run_number']==g[-1]),
                  'alpha_std'] = alpha_std
#%%[markdown]
# Now that we've found the map, we can see how well it describes the average
# result of the binomial partitioning method,
#
# $$ \langle \left(I_1 - I_2\right)^2\rangle = \alpha I_\text{tot}$$
# 
# To see how "right" it is, I can bin the data by a specific amount (say, 50
# divisions per bin) or within a certain intensity range, compute the means, and
# then plot the MAP and error to see if it passes through the means. Let's try
# this first just by choosing a single condition. 
#%%
# Look only at glucose 37.
glucose_37 = lin_final[(lin_final['temp']==37) &
                       (lin_final['carbon']=='glycerol')].copy()

# Compute the squared differences and the sum total. 
glucose_37['fluct'] = (glucose_37['I_1_sub'] - glucose_37['I_2_sub'])**2
glucose_37['summed'] = glucose_37['I_1_sub'] + glucose_37['I_2_sub']

# Define a function to compute the mean and sem of the data in the
def bin_by_value(df, bins):
    """
    Bins by predefined bins. Returns the mean and SEM of all points in that bin
    """
    # Iterate through the bins.
    df = df.copy()
    summed_means = np.zeros(len(bins) - 1)
    fluct_means = np.zeros(len(bins) - 1)
    summed_sems = np.zeros(len(bins) - 1)
    fluct_sems = np.zeros(len(bins) - 1)
    for i in range(len(bins) - 1):
        lower = bins[i] - 1
        upper = bins[i+1] + 1
        samps = df[(df['summed'] >= lower) & (df['summed'] <= upper)]
        summed_means[i] = np.mean(samps['summed'])
        fluct_means[i] = np.mean(samps['fluct'])
        summed_sems[i] = np.std(samps['summed']) / np.sqrt(len(samps))
        fluct_sems[i] = np.std(samps['fluct']) / np.sqrt(len(samps))
    # assemble into a dataframe
    _df = pd.DataFrame(np.array([summed_means, summed_sems, fluct_means, fluct_sems]).T,
                       columns=['summed_mean', 'summed_sem', 'fluct_mean', 'fluct_sem'])
    # Compute the mins and max for eaach. 
    _df['summed_min'] = _df['summed_mean'] - _df['summed_sem']
    _df['summed_max'] = _df['summed_mean'] + _df['summed_sem']
    _df['fluct_min'] = _df['fluct_mean'] - _df['fluct_sem']
    _df['fluct_max'] = _df['fluct_mean'] + _df['fluct_sem']
    return _df
        
#%%
# Set up the figure canvas. 
p = bokeh.plotting.figure(width=500, height=300, x_axis_type='log',
                        y_axis_type='log', x_axis_label='summed intensity',
                        y_axis_label='fluctuations')

# Plot all of the single cell division data. 
p.circle(x='summed', y='fluct', size=1, alpha=0.5, color=colors['black'],
        source=glucose_37, legend='division')

global_min, global_max = glucose_37['summed'].min(), glucose_37['summed'].max()
I_tot_range = np.logspace(np.log10(global_min) -0.5, np.log10(global_max) + 0.5)
# Iterate through each date, bin the data, and plot the means. 
pal = bokeh.palettes.viridis(30)
iter = 0
for g, d in glucose_37.groupby(['carbon', 'alpha_opt']):
    min_val, max_val = np.min(d['summed']) , np.max(d['summed'])
    bins = np.logspace(np.log10(min_val), np.log10(max_val), 5)
    binned = bin_by_value(d, bins)

    # # Plot the  errors
    p.segment(x0='summed_mean', x1='summed_mean', y0='fluct_min', y1='fluct_max',
            line_width=1, color=pal[iter], source=binned)
    p.segment(x0='summed_min', x1='summed_max', y0='fluct_mean', y1='fluct_mean',
            line_width=1, color=pal[iter], source=binned)

    # Plot the means
    p.circle(x='summed_mean', y='fluct_mean', size=6, fill_color='white', line_color=pal[iter],
            source=binned, line_width=2, fill_alpha=0.5)

    # Plot the line of best fit. 
    std = d['alpha_std'].unique() 
    low = I_tot_range * (g[-1] - std)
    high= I_tot_range * (g[-1] + std)
    # err = bokeh.models.Band(base='itot', lower='low', upper='high', 
                        #    fill_color=pal[iter], fill_alpha=0.5, source=bokeh.models.ColumnDataSource({'itot':I_tot_range,
                                                                                            # 'low':low, 'high':high})) 
    # p.add_layout(err)
    p.line(I_tot_range, g[-1] * I_tot_range, color=pal[iter])
    iter += 1
p.legend.location = 'top_left'
bokeh.io.show(p)
#%%
for g, d in approved_snaps.groupby(['carbon', 'temp', 'date', 'run_number']):
    # Get the calibration factor. 
    samp_lineages = lin_final[(lin_final['date']==g[2]) & (lin_final['carbon']==g[0]) &
                    (lin_final['temp']==g[1]) & (lin_final['run_number']==g[3])].copy()
    # Insert the cal factors. 
    approved_snaps.loc[(approved_snaps['carbon']==g[0]) & (approved_snaps['date']==g[2]) & 
                        (approved_snaps['temp']==g[1]) & (approved_snaps['run_number']==g[-1]), 'alpha_mean'] = samp_lineages['alpha_opt'].values[0]
    approved_snaps.loc[(approved_snaps['carbon']==g[0]) & (approved_snaps['date']==g[2]) & 
                        (approved_snaps['temp']==g[1])  & (approved_snaps['run_number']==g[3]), 'alpha_max'] = samp_lineages['alpha_opt'].values[0] - samp_lineages['alpha_std'].values[0]
    approved_snaps.loc[(approved_snaps['carbon']==g[0]) & (approved_snaps['date']==g[2]) & 
                        (approved_snaps['temp']==g[1]) & (approved_snaps['run_number']==g[3]), 'alpha_min'] = samp_lineages['alpha_opt'].values[0] + samp_lineages['alpha_std'].values[0]

#%%[markdown]
# Now that the calibration factors have been assigned, we can move forward and
# do the proper background subtraction, like we did with the lineages. 
# Now, compute the mean, min, and max repressor count. 

#%%
# Iterate through, perform the background subtraction, and compute the
# fold-change
fc_dfs = []
for g, d in approved_snaps.groupby(['carbon', 'temp', 'date', 'run_number']):
    d = d.copy()
    # Isolate the autofluorescence samples. 
    auto = d[d['strain']=='auto']
    median_auto_mch = d[d['strain']=='delta']['fluor2_mean_death'].median()
    median_auto_yfp = auto['fluor1_mean_death'].median()

    # Compute the integrated intensities for each. 
    d['mcherry_sub']= d['area_death'] * (d['fluor2_mean_death'] - median_auto_mch)
    d['yfp_sub']= d['area_death'] * (d['fluor1_mean_death'] - median_auto_yfp)

    # compute the mean, min, and max number of repressors. 
    d['rep_mean'] = d['mcherry_sub'] / d['alpha_mean']
    d['rep_min'] = d['mcherry_sub'] / d['alpha_max']
    d['rep_max'] = d['mcherry_sub'] / d['alpha_min']

    # Isolate delta and compute the mean yfp
    delta = d[d['strain']=='delta']
    delta_yfp = delta['yfp_sub'].mean()

    # Compute the fold-change
    d['fold_change'] = d['yfp_sub'] / delta_yfp

    # Reduce the dataframe to the informative columns and append to the storage
    # list. 
    d = d[['carbon', 'temp', 'date', 'atc_ngml', 'alpha_mean', 'rep_mean', 'rep_min', 'rep_max', 'fold_change', 'strain']]
    fc_dfs.append(d)

# Concatenate the fold-change dataframe
fc_df = pd.concat(fc_dfs)
#%%
fc_df.to_csv('../../data/analyzed_foldchange_improper.csv', index=False)
#%%
carb_var = fc_df[(fc_df['temp']==37) & (fc_df['strain']=='dilution') & (fc_df['date']!=20181021)]

iter = 0
p = bokeh.plotting.figure(x_axis_type='log', y_axis_type='log')
for g, d in carb_var.groupby(['carbon']):

    # round by the repressor copy number and compute the mean
    d['rep'] = np.round(d['rep_mean'])
    grouped = d.groupby('rep').agg(('mean', 'sem')).reset_index()
    grouped['low'] = (grouped['fold_change']['mean'] - grouped['fold_change']['sem'])
    grouped['high'] = (grouped['fold_change']['mean'] + grouped['fold_change']['sem'])
    # grouped = grouped[grouped['rep']['mean'] <= 500]
    p.circle(2 * grouped['rep'],  grouped['fold_change']['mean'], size=5, color=color_list[iter], 
    legend=g)
    # p.segment(x0=grouped['rep'], x1=grouped['rep'], y0=grouped['low'], y1=grouped['high'], line_width=1, color=color_list[iter],
    # legend=g)
    iter += 1

rep_range = np.logspace(0, 3, 200)
fc = (1 + 0.99 * (rep_range/4.6E6) * np.exp(13.9))**-1
p.line(rep_range, fc, color='tomato', legend='theory')

p.legend.click_policy='hide'
bokeh.io.show(p)

#%%
_df = carb_var[carb_var['carbon']=='glucose']
p = bokeh.plotting.figure(x_axis_type='log', y_axis_type='log') 
iter = 0
for g, d in _df.groupby(['date']):
    d['rep'] = np.round(d['rep_mean'], decimals=-1)
    grouped = d.groupby('rep').agg(('mean', 'sem')).reset_index()
    p.circle(grouped['rep'], grouped['fold_change']['mean'], color=color_list[iter], 
            legend=str(g))
    iter += 1

p.line(rep_range, 1/ fc, color='tomato', legend='theory')
p.legend.click_policy='hide'
bokeh.io.show(p)




#%%[markdown]
# Let's try a more proper approach factoring in all of the error in the data. 
# This is a more proper Bayesian model in which I make only one critical
# assumption. I have a bunch of measurements $I_1$ and $I_2$ of daughter cells.
# I can make an approximation that any measurement of a given $I_1$ or $I_2$ is
# Gaussian with a mean $\mu$ and some homoscedastic error $\sigma$. This mean is 
# dictated by the relationship $I_1 = \alpha N_\text{1}$ and $I_2 = \alpha
# N_\text{2}$. The likelihoods in this case are given by 
# $$ I_\text{1} \sim \mathcal{N}(\alpha N_\text{1}, \sigma);\,\,I_\text{2}\sim \mathcal{N}(\alpha(N_\text{tot}-N_\text{1}),\sigma).$$
#  
# I have to therefore assign some prior to $N_1$, and $N_\text{tot}$. The crux
# of this model hands on the assumption that partitioning is binomial. As I
# can't really discretely sample in Stan,  I will have to approximate it as a
# Gaussian. The Gaussian approximation of a binomial is one with a mean $np$ and
# standard deviation $np(1 - p)$. Since I am assuming $p = 1/2$ here, this comes
# out to $\mu = N_\text{tot} / 2$ and $\sigma = N_\text{tot} / 4$.
#
# Finally, I just have to assign a prior on $\alpha$, which is still super
# tricky. I suppose that I can just be super uninformative and take uniform over
# some huge range.
#
# This isn't the kind of thing that I can just minimize, so I will have to code
# this up in `stan`, which I have done in another file. 
# 
# Below, we will load the model and sample the replicates of the glucose 37°C replicates

#%%
# Load the stan model
model = mwc.bayes.StanModel('../stan/calibration_factor.stan', force_compile=True)
#%%
# Choose a single date to benchmark it and make sure things are at least
chosen_date = glucose_37['date'].unique()[2]
glucose_sel = glucose_37[(glucose_37['date']==chosen_date) & (glucose_37['run_number']==1)]
# Assemble the data dictionary. 
data_dict = {'N':len(glucose_sel), 
             'I1':glucose_sel['I_1_sub'], 
             'I2':glucose_sel['I_2_sub']}
# Keyword for whether sampling should be executed or not.             
SAMPLE = True
if SAMPLE:
    fit, samples = model.sample(data_dict, iter=2000)

#%%
p = bokeh.plotting.figure(x_axis_type='log', y_axis_type='log')
I_tot_range = np.logspace(np.log10(glucose_sel['summed'].min()) - 0.5,
                   np.log10(glucose_sel['summed'].max()) + 0.5)
bins = np.logspace(np.log10(glucose_sel['summed'].min() - 1), 
                   np.log10(glucose_sel['summed'].max() + 1),
                   15)
binned = bin_by_value(glucose_sel, bins)
p.circle(glucose_sel['summed'], glucose_sel['fluct'], color='black', size=0.5)
p.circle(binned['summed_mean'], binned['fluct_mean'])
p.line(bins, bins * np.mean(samples['alpha']))
bokeh.io.show(p)
#%%[markdown]
# This doesn't seem too bad! And it samples relatively quickly. Let's try again
# with all of the dates. 
#%%
for g, d in tqdm.tqdm(lin_final.groupby(['date', 'carbon', 'temp', 'run_number'])):
    # Set up the data dict and sample
    data_dict = {'N': len(d), 'I1':d['I_1_sub'], 'I2':d['I_2_sub']}
    _, samples = model.sample(data_dict, iter=2000)

    # Compute the important stats of alpha. 
    mean_alpha = np.median(samples['alpha'])
    alpha_min,alpha_max = mwc.stats.compute_hpd(samples['alpha'], 0.95)

    lin_final.loc[(lin_final['carbon']==g[1]) & 
                  (lin_final['date']==g[0]) &
                  (lin_final['temp']==g[2]) & 
                  (lin_final['run_number']==g[-1]), 'alpha_mean'] = mean_alpha
    lin_final.loc[(lin_final['carbon']==g[1]) & 
                  (lin_final['date']==g[0]) &
                  (lin_final['temp']==g[2]) & 
                  (lin_final['run_number']==g[-1]), 'alpha_min'] = alpha_min
    lin_final.loc[(lin_final['carbon']==g[1]) & 
                  (lin_final['date']==g[0]) &
                  (lin_final['temp']==g[2]) & 
                  (lin_final['run_number']==g[-1]), 'alpha_max'] = alpha_max

#%%
glucose_37 = lin_final[(lin_final['temp']==32) & 
                       (lin_final['carbon']=='glucose')].copy()

# Compute the squared differences and the sum total. 
glucose_37['fluct'] = (glucose_37['I_1_sub'] - glucose_37['I_2_sub'])**2
glucose_37['summed'] = glucose_37['I_1_sub'] + glucose_37['I_2_sub']


p = bokeh.plotting.figure(width=500, height=300, x_axis_type='log',
                        y_axis_type='log', x_axis_label='summed intensity',
                        y_axis_label='fluctuations')

# Plot all of the single cell division data. 
p.circle(x='summed', y='fluct', size=1, alpha=0.5, color=colors['black'],
        source=glucose_37, legend='division')

global_min, global_max = glucose_37['summed'].min(), glucose_37['summed'].max()
I_tot_range = np.logspace(np.log10(global_min)-0.5, np.log10(global_max) + 0.5)
# Iterate through each date, bin the data, and plot the means. 
pal = bokeh.palettes.viridis(20)
iter = 0
for g, d in glucose_37.groupby(['date', 'run_number']):
    min_val, max_val = np.min(d['summed']) , np.max(d['summed'])
    bins = np.logspace(np.log10(min_val), np.log10(max_val), 8)
    binned = bin_by_value(d, bins)
    print(d['alpha_mean'].unique())
    # Plot the  errors
    p.segment(x0='summed_mean', x1='summed_mean', y0='fluct_min', y1='fluct_max',
            line_width=1, color=pal[iter], source=binned)
    p.segment(x0='summed_min', x1='summed_max', y0='fluct_mean', y1='fluct_mean',
            line_width=1, color=pal[iter], source=binned)

    # Plot the means
    p.circle(x='summed_mean', y='fluct_mean', size=6, fill_color='white', line_color=pal[iter],
            source=bokeh.models.ColumnDataSource(binned), line_width=2, fill_alpha=0.5)
    # Plot the line of best fit. 
    p.line(I_tot_range, I_tot_range * d['alpha_mean'].unique(), color=pal[iter]) 
    iter += 1
p.legend.location = 'top_left'
bokeh.io.show(p)

#%%[markdown]
# This seems like it works pretty well, although I should look more at the
# actual protein distributions. For now, though, we can use these calibration
# factors to look at the protein expression and how it scales with the repressor
# growth rate.
#
# First, let's just save the lineages so we don't have to do everything over
# again all of the time. 
#
#%%
# lin_final.to_csv('../../data/analyzed_lineages_proper.csv', index=False)

lin_final = pd.read_csv('../../data/analyzed_lineages_proper.csv')
#%%[markdown] To look at the protein expression, we'll make a LUT for the
#calibration factor based on the condition. 
#%%
# Insert the alpha and credible regions into the approved snaps df. 
for g, d in approved_snaps.groupby(['carbon', 'temp', 'date', 'run_number']):
    # Get the calibration factor. 
    samp_lineages = lin_final[(lin_final['date']==g[2]) & (lin_final['carbon']==g[0]) &
                    (lin_final['temp']==g[1]) & (lin_final['run_number']==g[3])].copy()
    
    # Insert the cal factors. 
    approved_snaps.loc[(approved_snaps['carbon']==g[0]) & (approved_snaps['date']==g[2]) & 
                        (approved_snaps['temp']==g[1]) & (approved_snaps['run_number']==g[-1]), 'alpha_mean'] = samp_lineages['alpha_mean'].values[0]
    approved_snaps.loc[(approved_snaps['carbon']==g[0]) & (approved_snaps['date']==g[2]) & 
                        (approved_snaps['temp']==g[1])  & (approved_snaps['run_number']==g[3]), 'alpha_max'] = samp_lineages['alpha_max'].values[0]
    approved_snaps.loc[(approved_snaps['carbon']==g[0]) & (approved_snaps['date']==g[2]) & 
                        (approved_snaps['temp']==g[1]) & (approved_snaps['run_number']==g[3]), 'alpha_min'] = samp_lineages['alpha_min'].values[0]

#%%[markdown]
# Now that the calibration factors have been assigned, we can move forward and
# do the proper background subtraction, like we did with the lineages. 
# Now, compute the mean, min, and max repressor count. 

#%%
# Iterate through, perform the background subtraction, and compute the
# fold-change
fc_dfs = []
for g, d in approved_snaps.groupby(['carbon', 'temp', 'date', 'run_number']):
    d = d.copy()
    # Isolate the autofluorescence samples. 
    auto = d[d['strain']=='auto']
    median_auto_mch = d[d['strain']=='delta']['fluor2_mean_death'].median()
    median_auto_yfp = auto['fluor1_mean_death'].median()

    # Compute the integrated intensities for each. 
    d['mcherry_sub']= d['area_death'] * (d['fluor2_mean_death'] - median_auto_mch)
    d['yfp_sub']= d['area_death'] * (d['fluor1_mean_death'] - median_auto_yfp)

    # compute the mean, min, and max number of repressors. 
    d['rep_mean'] = d['mcherry_sub'] / d['alpha_mean']
    d['rep_min'] = d['mcherry_sub'] / d['alpha_max']
    d['rep_max'] = d['mcherry_sub'] / d['alpha_min']

    # Isolate delta and compute the mean yfp
    delta = d[d['strain']=='delta']
    delta_yfp = delta['yfp_sub'].median()

    # Compute the fold-change
    d['fold_change'] = d['yfp_sub'] / delta_yfp

    # Reduce the dataframe to the informative columns and append to the storage
    # list. 
    d = d[['carbon', 'temp', 'date', 'atc_ngml', 'alpha_mean', 'rep_mean', 'rep_min', 'rep_max', 'fold_change', 'strain']]
    fc_dfs.append(d)

# Concatenate the fold-change dataframe
fc_df = pd.concat(fc_dfs)
#%%
fc_df.to_csv('../../data/analyzed_foldchange_proper.csv', index=False)
#%%
carb_var = fc_df[(fc_df['temp']==37) & (fc_df['strain']=='dilution')]

iter = 0
p = bokeh.plotting.figure(x_axis_type='log', y_axis_type='log')
for g, d in carb_var.groupby(['carbon']):

    # round by the repressor copy number and compute the mean
    d['rep'] = 2 * np.round(d['rep_mean'])
    d = d[(d['rep'] > 10) & (d['rep'] < 1000)]
    grouped = d.groupby('rep').agg(('mean', 'sem')).reset_index()
    grouped['low'] = (grouped['fold_change']['mean'] - grouped['fold_change']['sem'])
    grouped['high'] = (grouped['fold_change']['mean'] + grouped['fold_change']['sem'])
    grouped = grouped[grouped['rep'] <= 500]
    # binned = bin_by_value() 
    p.circle(grouped['rep'], grouped['fold_change']['mean'], size=5, color=color_list[iter+2], 
    legend=g)
    p.segment(x0=grouped['rep'], x1=grouped['rep'], y0=grouped['low'], y1=grouped['high'], line_width=1, color=color_list[iter + 2],
    legend=g)
    iter += 1

rep_range = np.logspace(0, 3, 200)
fc = (1 + (rep_range/4.6E6) * np.exp(13.9))**-1
p.line(rep_range, fc, color='black', legend='theory')

p.legend.click_policy='hide'
bokeh.io.show(p)

#%%
_df = carb_var[carb_var['carbon']=='glucose']
p = bokeh.plotting.figure(x_axis_type='log', y_axis_type='log') 
iter = 0
for g, d in _df.groupby(['date']):
    d['rep'] = np.round(d['rep_mean'], decimals=-1)
    grouped = d.groupby('rep').agg(('mean', 'sem')).reset_index()
    p.circle(grouped['rep'], grouped['fold_change']['mean'], color=color_list[iter], 
            legend=str(g))
    iter += 1

p.line(rep_range, 1/ fc, color='tomato', legend='theory')
p.legend.click_policy='hide'
bokeh.io.show(p)


#%%