data {
    int<lower=1> J; // Number of unique temperatures
    int<lower=1> N; // Total number of measurements
    vector[J] temps; // Temperture (in C)
    int<lower=1, upper=J> temp_idx[N]; // Temp look up vector
    int<lower=1> Nns; // Number of nonspecific sites
    vector<lower=0>[N] R; // Number of repressors per cell
    vector[N] foldchange; // Observed fold-change in gene expression
}

transformed data { 
    // Convert fold-change to log fold change
    vector[N] log_fc = log(foldchange);
    vector[J] temp_K = temps + 273.15;
}

parameters { 
    real<lower=0> fc_sigma; // Homoscedastic error of fold-change
    vector epsilon_37;
    real delS; // Intercept of line on Van't off plot, proportional to del S
}

transformed parameters {
    vector[J] epsilon;

    for (i in 1:J) {
        epsilon[i] = -(delH / temp_K[i]) + delS;
     } 
 }

model {
    vector[N] mu;
    epsilon_37 ~ normal(-12, 6);
    fc_sigma ~ normal(0, 0.1);
    delH ~ lognormal(0, 10);
    delS ~ lognormal(0, 1);
    mu = -1 * log(1 + (R ./ Nns) .* exp(-epsilon[temp_idx]));
    log_fc ~ normal(mu, fc_sigma);
}