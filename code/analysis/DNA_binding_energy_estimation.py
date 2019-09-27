# %%
import numpy as np
import pandas as pd
import mwc.bayes

#  Load the data.
data = pd.read_csv('../../data/analyzed_foldchange.csv')
data = data[(data['strain']=='dilution') & (data['repressors'] >= 10)]

# Group the data by each date, run number, replicate, and ATC to compute the means. 
grouped = data.groupby(['carbon', 'temp', 'date', 
                        'run_number', 'atc_ngml']).mean().reset_index()

# Assign an identifier to each  unique set of measurements. 
grouped['idx'] = grouped.groupby(['carbon', 'temp']).ngroup() + 1
#
# Load the stan model 
model = mwc.bayes.StanModel('../stan/DNA_binding_energy.stan')

#%%
# Assign the data dictionary and sample the model. 
data_dict = {'J':grouped['idx'].max(),
             'N':len(grouped),
             'idx':grouped['idx'],
             'repressors':grouped['repressors'],
             'Nns':4.6E6,
             'foldchange':grouped['fold_change']}

fit, samples = model.sample(data_dict)
params = model.summarize_parameters()
#%%
# Update the dimensions and parameter entries. 
rename_params = ['epRA', 'sigma']
sample_dfs = []
for g, d in grouped.groupby(['idx']):
    params.loc[params['dimension']==g, 'carbon'] = d['carbon'].unique()[0]
    params.loc[params['dimension']==g, 'temp'] = d['temp'].unique()[0]
    for r in rename_params:
        df = pd.DataFrame([])
        df['value'] = samples[f'{p}[{g}]']
        df['parameter'] = p
        df['carbon'] = d['carbon'].unique()[0]
        df['temp'] = d['temp'].unique()[0]
        sample_dfs.append(df)
samples = pd.concat(sample_dfs)

# Save the dataframes to disk. 
params.to_csv('../../data/DNA_binding_energy_summary.csv', index=False)
samples.to_csv('../../data/DNA_binding_energy_samples.csv', index=False)