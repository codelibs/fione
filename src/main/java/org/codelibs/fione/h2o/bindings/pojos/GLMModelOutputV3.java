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

public class GLMModelOutputV3 extends ModelOutputSchemaV3 {

    /**
     * Table of Coefficients
     */
    @SerializedName("coefficients_table")
    public TwoDimTableV3 coefficientsTable;

    /**
     * Table of Random Coefficients for HGLM
     */
    @SerializedName("random_coefficients_table")
    public TwoDimTableV3 randomCoefficientsTable;

    /**
     * Table of Coefficients with coefficients denoted with class names for GLM multinonimals only.
     */
    @SerializedName("coefficients_table_multinomials_with_class_names")
    public TwoDimTableV3 coefficientsTableMultinomialsWithClassNames;

    /**
     * Standardized Coefficient Magnitudes
     */
    @SerializedName("standardized_coefficient_magnitudes")
    public TwoDimTableV3 standardizedCoefficientMagnitudes;

    /**
     * Variable Importances
     */
    @SerializedName("variable_importances")
    public TwoDimTableV3 variableImportances;

    /**
     * Lambda minimizing the objective value, only applicable with lambda search or when arrays of alpha and lambdas are
     * provided
     */
    @SerializedName("lambda_best")
    public double lambdaBest;

    /**
     * Alpha minimizing the objective value, only applicable when arrays of alphas are given
     */
    @SerializedName("alpha_best")
    public double alphaBest;

    /**
     * submodel index minimizing the objective value, only applicable for arrays of alphas/lambda
     */
    @SerializedName("best_submodel_index")
    public int bestSubmodelIndex;

    /**
     * Lambda best + 1 standard error. Only applicable with lambda search and cross-validation
     */
    @SerializedName("lambda_1se")
    public double lambda1se;

    /**
     * Minimum lambda value calculated that may be used for lambda search.  Early-stop may happen and the minimum lambda
     * value will not be used in this case.
     */
    @SerializedName("lambda_min")
    public double lambdaMin;

    /**
     * Starting lambda value used when lambda search is enabled.
     */
    @SerializedName("lambda_max")
    public double lambdaMax;

    /**
     * Dispersion parameter, only applicable to Tweedie family (input/output) and fractional Binomial (output only)
     */
    public double dispersion;

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
    public GLMModelOutputV3() {
        lambdaBest = -1.0;
        alphaBest = -1.0;
        bestSubmodelIndex = 0;
        lambda1se = -1.0;
        lambdaMin = -1.0;
        lambdaMax = -1.0;
        dispersion = 0.0;
        modelCategory = ModelCategory.Regression;
        status = "";
        startTime = 0L;
        endTime = 0L;
        runTime = 0L;
        defaultThreshold = 0.5;
    }

    /**
     * Return the contents of this object as a JSON String.
     */
    @Override
    public String toString() {
        return new GsonBuilder().serializeSpecialFloatingPointValues().create().toJson(this);
    }

}
