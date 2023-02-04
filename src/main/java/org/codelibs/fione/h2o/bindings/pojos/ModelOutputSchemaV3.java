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

import java.lang.reflect.Field;
import java.util.Arrays;
import java.util.HashMap;
import java.util.Map;

import org.apache.commons.lang3.ArrayUtils;
import org.codelibs.fione.entity.ChartData;

import com.google.gson.GsonBuilder;
import com.google.gson.annotations.SerializedName;

public class ModelOutputSchemaV3 extends SchemaV3 {

    /**
     * Column names
     */
    public String[] names;

    /**
     * Original column names
     */
    @SerializedName("original_names")
    public String[] originalNames;

    /**
     * Column types
     */
    @SerializedName("column_types")
    public String[] columnTypes;

    /**
     * Domains for categorical columns
     */
    public String[][] domains;

    /**
     * Cross-validation models (model ids)
     */
    @SerializedName("cross_validation_models")
    public ModelKeyV3[] crossValidationModels;

    /**
     * Cross-validation predictions, one per cv model (deprecated, use cross_validation_holdout_predictions_frame_id
     * instead)
     */
    @SerializedName("cross_validation_predictions")
    public FrameKeyV3[] crossValidationPredictions;

    /**
     * Cross-validation holdout predictions (full out-of-sample predictions on training data)
     */
    @SerializedName("cross_validation_holdout_predictions_frame_id")
    public FrameKeyV3 crossValidationHoldoutPredictionsFrameId;

    /**
     * Cross-validation fold assignment (each row is assigned to one holdout fold)
     */
    @SerializedName("cross_validation_fold_assignment_frame_id")
    public FrameKeyV3 crossValidationFoldAssignmentFrameId;

    /**
     * Category of the model (e.g., Binomial)
     */
    @SerializedName("model_category")
    public ModelCategory modelCategory;

    /**
     * Model summary
     */
    @SerializedName("model_summary")
    public TwoDimTableV3 modelSummary;

    /**
     * Scoring history
     */
    @SerializedName("scoring_history")
    public TwoDimTableV3 scoringHistory;

    /**
     * Cross-Validation scoring history
     */
    @SerializedName("cv_scoring_history")
    public TwoDimTableV3[] cvScoringHistory;

    /**
     * Model reproducibility information
     */
    @SerializedName("reproducibility_information_table")
    public TwoDimTableV3[] reproducibilityInformationTable;

    /**
     * Training data model metrics
     */
    @SerializedName("training_metrics")
    public ModelMetricsBaseV3 trainingMetrics;

    /**
     * Validation data model metrics
     */
    @SerializedName("validation_metrics")
    public ModelMetricsBaseV3 validationMetrics;

    /**
     * Cross-validation model metrics
     */
    @SerializedName("cross_validation_metrics")
    public ModelMetricsBaseV3 crossValidationMetrics;

    /**
     * Cross-validation model metrics summary
     */
    @SerializedName("cross_validation_metrics_summary")
    public TwoDimTableV3 crossValidationMetricsSummary;

    /**
     * Job status
     */
    public String status;

    /**
     * Start time in milliseconds
     */
    @SerializedName("start_time")
    public long startTime;

    /**
     * End time in milliseconds
     */
    @SerializedName("end_time")
    public long endTime;

    /**
     * Runtime in milliseconds
     */
    @SerializedName("run_time")
    public long runTime;

    /**
     * Default threshold used for predictions
     */
    @SerializedName("default_threshold")
    public double defaultThreshold;

    /**
     * Help information for output fields
     */
    public Map<String, String> help;

    /**
     * Public constructor
     */
    public ModelOutputSchemaV3() {
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

    private boolean isOutputClass(final Class<?> clazz) {
        if (clazz.isPrimitive() || clazz.isEnum() || String.class.isAssignableFrom(clazz) || KeyV3.class.isAssignableFrom(clazz)
                || String[].class.isAssignableFrom(clazz) || String[][].class.isAssignableFrom(clazz)) {
            return true;
        }
        return false;
    }

    @Override
    public String[] getFieldNames() {
        if (fieldNames == null) {
            fieldNames = Arrays.stream(getClass().getFields()).filter(f -> isOutputClass(f.getType())).map(Field::getName)
                    .toArray(n -> new String[n]);
        }
        return fieldNames;
    }

    public ChartData getScoringHistoryChart() {
        final Map<String, Integer> columnIndexMap = new HashMap<>();
        for (var i = 0; i < scoringHistory.columns.length; i++) {
            columnIndexMap.put(scoringHistory.columns[i].name, i);
        }
        final String[] xNames = { "number_of_trees", "epochs", "iteration", "iterations" };
        final String[] yNames =
                { "training_deviance", "training_classification_error", "deviance_train", "within_cluster_sum_of_squares", "objective" };
        for (final String xName : xNames) {
            for (final String yName : yNames) {
                final var chart = getScoringHistoryChart(columnIndexMap, xName, yName);
                if (chart != null) {
                    return chart;
                }
            }
        }
        return null;
    }

    private ChartData getScoringHistoryChart(final Map<String, Integer> columnIndexMap, final String xName, final String yName) {
        if (columnIndexMap.containsKey(xName) && columnIndexMap.containsKey(yName)) {
            final var chartData = new ChartData();
            chartData.addColumn(xName, scoringHistory.data[columnIndexMap.get(xName)]);
            chartData.addColumn(yName, scoringHistory.data[columnIndexMap.get(yName)]);
            chartData.setAxisName(xName);
            chartData.addAxisLabel("x", xName);
            chartData.addAxisLabel("y", yName);
            return chartData;
        }
        return null;
    }

    public ChartData getVariableImportancesChart() {
        return null;
    }

    protected ChartData getVariableImportancesChart(final TwoDimTableV3 dimTable) {
        final Map<String, Integer> columnIndexMap = new HashMap<>();
        for (var i = 0; i < dimTable.columns.length; i++) {
            columnIndexMap.put(dimTable.columns[i].name, i);
        }
        if (columnIndexMap.containsKey("variable") && columnIndexMap.containsKey("scaled_importance")) {
            final var chartData = new ChartData();
            var variables = dimTable.data[columnIndexMap.get("variable")];
            variables = Arrays.copyOf(variables, variables.length);
            ArrayUtils.reverse(variables);
            chartData.addColumn("variable", variables);
            var importances = dimTable.data[columnIndexMap.get("scaled_importance")];
            importances = Arrays.copyOf(importances, importances.length);
            ArrayUtils.reverse(importances);
            chartData.addColumn("scaled_importance", importances, "bar");
            chartData.setAxisName("variable");
            chartData.addAxisLabel("x", "variable");
            chartData.addAxisType("x", "category");
            chartData.addAxisLabel("y", "scaled_importance");
            chartData.setHeight(dimTable.rowcount * 30);
            return chartData;
        }
        return null;
    }
}
