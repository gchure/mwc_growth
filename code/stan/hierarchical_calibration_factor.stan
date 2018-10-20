/* 
* Hierarchical Model for Calibration Factor Inference
* ---------------------------------------------------
* Author: Griffin Chure
* License: MIT
* 
*/
functions{
    /** 
    * Approximate the Binomial distirubution for continuous variables 
    * as a ratio of Gamma functions 
    * 
    * @param I1: Observed fluorescence of daughter cell 1. 
    * @param I2: Observed fluorescence of daughter cell 2.
    * @param alpha: Fluorescenc calibration factor in units of a.u. / molecule
    * @param N: Total number of measurements 
    **/
    real GammaApproxBinom_lpdf(real I1, real I2, real alpha) { 
            return -log(alpha) + lgamma(((I1 + I2) / alpha) + 1) - lgamma((I1 / alpha) + 1)
                        - lgamma((I2 / alpha) + 1) - ((I1 + I2) / alpha) * log(2);
        }
    }

data {
    //Dimensional parameters
    int<lower=1> J1; // Number of unique growth media
    int<lower=1> J2; // Number of unique experimental across entire data set
    int<lower=1> N; // total number of measurements for fluctuations
    int<lower=1, upper=J1> idx_1[J2];
    int<lower=1, upper=J2> idx_2[N];
    
    // Experimental parameters
    real<lower=0> I_1[N]; // Observed mean pixel intensity of daughter cell 1
    real<lower=0> I_2[N]; // Observed mean pixel intensity of daughter cell 2 
}
   
parameters {
    // Hyper parameters
    vector<lower=0, upper=2^12>[J1]  alpha_mu; // Hyperparameter for alpha

    // Low-level parameters
    vector<lower=0>[J2] alpha_raw; // Low-level parameter for experimental alpha 
    real<lower=0> tau;
}

transformed parameters {
    vector[J2] alpha = alpha_mu[idx_1] + tau * alpha_raw[idx_1];
}

model {
    // Define the hyperpriors. 
    alpha_mu ~ lognormal(3, 3);
    tau ~ normal(0, 1);

    // Iterate through each measurement and compute the likelihood
    for (i in 1:N) {
        I_1[i] ~ GammaApproxBinom(I_2[i],alpha[idx_2[i]]);
    } 
}
