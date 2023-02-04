/*
 * Copyright 2012-2023 CodeLibs Project and the Others.
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
import com.google.gson.annotations.SerializedName;

public class CoxPHModelOutputV3 extends ModelOutputSchemaV3 {

    /**
     * Table of Coefficients
     */
    @SerializedName("coefficients_table")
    public TwoDimTableV3 coefficientsTable;

    /**
     * var(coefficients)
     */
    @SerializedName("var_coef")
    public double[][] varCoef;

    /**
     * null log-likelihood
     */
    @SerializedName("null_loglik")
    public double nullLoglik;

    /**
     * log-likelihood
     */
    public double loglik;

    /**
     * log-likelihood test stat
     */
    @SerializedName("loglik_test")
    public double loglikTest;

    /**
     * Wald test stat
     */
    @SerializedName("wald_test")
    public double waldTest;

    /**
     * Score test stat
     */
    @SerializedName("score_test")
    public double scoreTest;

    /**
     * R-square
     */
    public double rsq;

    /**
     * Maximum R-square
     */
    public double maxrsq;

    /**
     * log relative error
     */
    public double lre;

    /**
     * number of iterations
     */
    public int iter;

    /**
     * x weighted mean vector for categorical variables
     */
    @SerializedName("x_mean_cat")
    public double[][] xMeanCat;

    /**
     * x weighted mean vector for numeric variables
     */
    @SerializedName("x_mean_num")
    public double[][] xMeanNum;

    /**
     * unweighted mean vector for numeric offsets
     */
    @SerializedName("mean_offset")
    public double[] meanOffset;

    /**
     * names of offsets
     */
    @SerializedName("offset_names")
    public String[] offsetNames;

    /**
     * n
     */
    public long n;

    /**
     * number of rows with missing values
     */
    @SerializedName("n_missing")
    public long nMissing;

    /**
     * total events
     */
    @SerializedName("total_event")
    public long totalEvent;

    /**
     * time
     */
    public double[] time;

    /**
     * number at risk
     */
    @SerializedName("n_risk")
    public double[] nRisk;

    /**
     * number of events
     */
    @SerializedName("n_event")
    public double[] nEvent;

    /**
     * number of censored obs
     */
    @SerializedName("n_censor")
    public double[] nCensor;

    /**
     * baseline cumulative hazard
     */
    @SerializedName("cumhaz_0")
    public double[] cumhaz0;

    /**
     * component of var(cumhaz)
     */
    @SerializedName("var_cumhaz_1")
    public double[] varCumhaz1;

    /**
     * component of var(cumhaz)
     */
    @SerializedName("var_cumhaz_2")
    public FrameKeyV3 varCumhaz2;

    /**
     * Baseline Hazard
     */
    @SerializedName("baseline_hazard")
    public FrameKeyV3 baselineHazard;

    /**
     * Baseline Survival
     */
    @SerializedName("baseline_survival")
    public FrameKeyV3 baselineSurvival;

    /**
     * formula
     */
    public String formula;

    /**
     * ties
     */
    public CoxPHTies ties;

    /**
     * concordance
     */
    public double concordance;

    /*------------------------------------------------------------------------------------------------------------------
    //                                                  INHERITED
    //------------------------------------------------------------------------------------------------------------------

    // Column names
    public String[] names;

    // Original column names
    public String[] originalNames;

    // Column types
    public String[] columnTypes;

    // Domains for categorical columns
    public String[][] domains;

    // Cross-validation models (model ids)
    public ModelKeyV3[] crossValidationModels;

    // Cross-validation predictions, one per cv model (deprecated, use cross_validation_holdout_predictions_frame_id
    // instead)
    public FrameKeyV3[] crossValidationPredictions;

    // Cross-validation holdout predictions (full out-of-sample predictions on training data)
    public FrameKeyV3 crossValidationHoldoutPredictionsFrameId;

    // Cross-validation fold assignment (each row is assigned to one holdout fold)
    public FrameKeyV3 crossValidationFoldAssignmentFrameId;

    // Category of the model (e.g., Binomial)
    public ModelCategory modelCategory;

    // Model summary
    public TwoDimTableV3 modelSummary;

    // Scoring history
    public TwoDimTableV3 scoringHistory;

    // Cross-Validation scoring history
    public TwoDimTableV3[] cvScoringHistory;

    // Model reproducibility information
    public TwoDimTableV3[] reproducibilityInformationTable;

    // Training data model metrics
    public ModelMetricsBaseV3 trainingMetrics;

    // Validation data model metrics
    public ModelMetricsBaseV3 validationMetrics;

    // Cross-validation model metrics
    public ModelMetricsBaseV3 crossValidationMetrics;

    // Cross-validation model metrics summary
    public TwoDimTableV3 crossValidationMetricsSummary;

    // Job status
    public String status;

    // Start time in milliseconds
    public long startTime;

    // End time in milliseconds
    public long endTime;

    // Runtime in milliseconds
    public long runTime;

    // Default threshold used for predictions
    public double defaultThreshold;

    // Help information for output fields
    public Map<String,String> help;

    */

    /**
     * Public constructor
     */
    public CoxPHModelOutputV3() {
        nullLoglik = 0.0;
        loglik = 0.0;
        loglikTest = 0.0;
        waldTest = 0.0;
        scoreTest = 0.0;
        rsq = 0.0;
        maxrsq = 0.0;
        lre = 0.0;
        iter = 0;
        n = 0L;
        nMissing = 0L;
        totalEvent = 0L;
        formula = "";
        concordance = 0.0;
        status = "";
        startTime = 0L;
        endTime = 0L;
        runTime = 0L;
        defaultThreshold = 0.0;
    }

    /**
     * Return the contents of this object as a JSON String.
     */
    @Override
    public String toString() {
        return new GsonBuilder().serializeSpecialFloatingPointValues().create().toJson(this);
    }

}
