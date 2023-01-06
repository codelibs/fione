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

public class GridSchemaV99 extends SchemaV3 {

    /**
     * Grid id
     */
    @SerializedName("grid_id")
    public GridKeyV3 gridId;

    /**
     * Model performance metric to sort by. Examples: logloss, residual_deviance, mse, rmse, mae,rmsle, auc, r2, f1,
     * recall, precision, accuracy, mcc, err, err_count, lift_top_group, max_per_class_error
     */
    @SerializedName("sort_by")
    public String sortBy;

    /**
     * Specify whether sort order should be decreasing.
     */
    public boolean decreasing;

    /**
     * Model IDs built by a grid search
     */
    @SerializedName("model_ids")
    public ModelKeyV3[] modelIds;

    /**
     * Used hyper parameters.
     */
    @SerializedName("hyper_names")
    public String[] hyperNames;

    /**
     * List of failed parameters
     */
    @SerializedName("failed_params")
    public ModelParametersSchemaV3[] failedParams;

    /**
     * List of detailed warning messages
     */
    @SerializedName("warning_details")
    public String[] warningDetails;

    /**
     * List of detailed failure messages
     */
    @SerializedName("failure_details")
    public String[] failureDetails;

    /**
     * List of detailed failure stack traces
     */
    @SerializedName("failure_stack_traces")
    public String[] failureStackTraces;

    /**
     * List of raw parameters causing model building failure
     */
    @SerializedName("failed_raw_params")
    public String[][] failedRawParams;

    /**
     * Training model metrics for the returned models; only returned if sort_by is set
     */
    @SerializedName("training_metrics")
    public ModelMetricsBaseV3[] trainingMetrics;

    /**
     * Validation model metrics for the returned models; only returned if sort_by is set
     */
    @SerializedName("validation_metrics")
    public ModelMetricsBaseV3[] validationMetrics;

    /**
     * Cross validation model metrics for the returned models; only returned if sort_by is set
     */
    @SerializedName("cross_validation_metrics")
    public ModelMetricsBaseV3[] crossValidationMetrics;

    /**
     * Cross validation model metrics summary for the returned models; only returned if sort_by is set
     */
    @SerializedName("cross_validation_metrics_summary")
    public TwoDimTableV3[] crossValidationMetricsSummary;

    /**
     * Directory for Grid automatic checkpointing
     */
    @SerializedName("export_checkpoints_dir")
    public String exportCheckpointsDir;

    /**
     * Summary
     */
    @SerializedName("summary_table")
    public TwoDimTableV3 summaryTable;

    /**
     * Scoring history
     */
    @SerializedName("scoring_history")
    public TwoDimTableV3 scoringHistory;

    /**
     * Public constructor
     */
    public GridSchemaV99() {
        sortBy = "";
        decreasing = false;
        exportCheckpointsDir = "";
    }

    /**
     * Return the contents of this object as a JSON String.
     */
    @Override
    public String toString() {
        return new GsonBuilder().serializeSpecialFloatingPointValues().create().toJson(this);
    }

}
