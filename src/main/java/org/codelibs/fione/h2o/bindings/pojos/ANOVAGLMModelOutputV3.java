/*
 * Copyright 2012-2022 CodeLibs Project and the Others.
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

import com.google.gson.Gson;
import com.google.gson.annotations.SerializedName;

public class ANOVAGLMModelOutputV3 extends ModelOutputSchemaV3 {

    /**
     * Table of Coefficients
     */
    @SerializedName("coefficients_table")
    public TwoDimTableV3[] coefficientsTable;

    /**
     * AnovaGLM transformed predictor frame key.  For debugging purposes only
     */
    @SerializedName("transformed_columns_key")
    public FrameKeyV3 transformedColumnsKey;

    /**
     * ANOVA table frame key containing Type III SS calculation, degree of freedom, F-statistics and p-values.  This
     * frame content is repeated in the model summary.
     */
    @SerializedName("result_frame_key")
    public FrameKeyV3 resultFrameKey;

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
    public ANOVAGLMModelOutputV3() {
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
        return new Gson().toJson(this);
    }

}
