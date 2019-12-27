/*
 * Copyright 2012-2019 CodeLibs Project and the Others.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
 * either express or implied. See the License for the specific language
 * governing permissions and limitations under the License.
 */
package org.codelibs.fione.h2o.bindings.pojos;

import com.google.gson.GsonBuilder;

public class ModelMetricsHGLMGaussianGaussianGenericV3 extends ModelMetricsHGLMGenericV3 {

    /*------------------------------------------------------------------------------------------------------------------
    //                                                  INHERITED
    //------------------------------------------------------------------------------------------------------------------

    // standard error of fixed predictors/effects
    public double[] sefe;

    // standard error of random effects
    public double[] sere;

    // dispersion parameter of the mean model (residual variance for LMM)
    public double varfix;

    // dispersion parameter of the random effects (variance of random effects for GLMM
    public double[] varranef;

    // fixed coefficient)
    public double[] fixef;

    // random coefficients
    public double[] ranef;

    // true if model has converged
    public boolean converge;

    // number of random columns
    public int[] randc;

    // deviance degrees of freedom for mean part of the model
    public double dfrefe;

    // estimates, standard errors of the linear predictor in the dispersion model
    public double[] summvc1;

    // estimates, standard errors of the linear predictor for dispersion parameter of random effects
    public double[][] summvc2;

    // log h-likelihood
    public double hlik;

    // adjusted profile log-likelihood profiled over random effects
    public double pvh;

    // adjusted profile log-likelihood profiled over fixed and random effects
    public double pbvh;

    // conditional AIC
    public double caic;

    // index of the most influential observation
    public long bad;

    // sum(etai-eta0)^2 where etai is current eta and eta0 is the previous one
    public double sumetadiffsquare;

    // sum(etai-eta0)^2/sum(etai)^2
    public double convergence;

    // The model used for this scoring run.
    public ModelKeyV3 model;

    // The checksum for the model used for this scoring run.
    public long modelChecksum;

    // The frame used for this scoring run.
    public FrameKeyV3 frame;

    // The checksum for the frame used for this scoring run.
    public long frameChecksum;

    // Optional description for this scoring run (to note out-of-bag, sampled data, etc.)
    public String description;

    // The category (e.g., Clustering) for the model used for this scoring run.
    public ModelCategory modelCategory;

    // The time in mS since the epoch for the start of this scoring run.
    public long scoringTime;

    // Predictions Frame.
    public FrameV3 predictions;

    // The Mean Squared Error of the prediction for this scoring run.
    public double mse;

    // The Root Mean Squared Error of the prediction for this scoring run.
    public double rmse;

    // Number of observations.
    public long nobs;

    // Name of custom metric
    public String customMetricName;

    // Value of custom metric
    public double customMetricValue;

    */

    /**
     * Public constructor
     */
    public ModelMetricsHGLMGaussianGaussianGenericV3() {
        varfix = 0.0;
        converge = false;
        dfrefe = 0.0;
        hlik = 0.0;
        pvh = 0.0;
        pbvh = 0.0;
        caic = 0.0;
        bad = 0L;
        sumetadiffsquare = 0.0;
        convergence = 0.0;
        modelChecksum = 0L;
        frameChecksum = 0L;
        description = "";
        scoringTime = 0L;
        mse = 0.0;
        rmse = 0.0;
        nobs = 0L;
        customMetricName = "";
        customMetricValue = 0.0;
    }

    /**
     * Return the contents of this object as a JSON String.
     */
    @Override
    public String toString() {
        return new GsonBuilder().serializeSpecialFloatingPointValues().create().toJson(this);
    }

}
