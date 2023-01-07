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

import com.google.gson.GsonBuilder;
import com.google.gson.annotations.SerializedName;

public class ModelParametersSchemaV3 extends SchemaV3 {

    /**
     * Destination id for this model; auto-generated if not specified.
     */
    @SerializedName("model_id")
    public ModelKeyV3 modelId;

    /**
     * Id of the training data frame.
     */
    @SerializedName("training_frame")
    public FrameKeyV3 trainingFrame;

    /**
     * Id of the validation data frame.
     */
    @SerializedName("validation_frame")
    public FrameKeyV3 validationFrame;

    /**
     * Number of folds for K-fold cross-validation (0 to disable or >= 2).
     */
    public int nfolds;

    /**
     * Whether to keep the cross-validation models.
     */
    @SerializedName("keep_cross_validation_models")
    public boolean keepCrossValidationModels;

    /**
     * Whether to keep the predictions of the cross-validation models.
     */
    @SerializedName("keep_cross_validation_predictions")
    public boolean keepCrossValidationPredictions;

    /**
     * Whether to keep the cross-validation fold assignment.
     */
    @SerializedName("keep_cross_validation_fold_assignment")
    public boolean keepCrossValidationFoldAssignment;

    /**
     * Allow parallel training of cross-validation models
     */
    @SerializedName("parallelize_cross_validation")
    public boolean parallelizeCrossValidation;

    /**
     * Distribution function
     */
    public GenmodelutilsDistributionFamily distribution;

    /**
     * Tweedie power for Tweedie regression, must be between 1 and 2.
     */
    @SerializedName("tweedie_power")
    public double tweediePower;

    /**
     * Desired quantile for Quantile regression, must be between 0 and 1.
     */
    @SerializedName("quantile_alpha")
    public double quantileAlpha;

    /**
     * Desired quantile for Huber/M-regression (threshold between quadratic and linear loss, must be between 0 and 1).
     */
    @SerializedName("huber_alpha")
    public double huberAlpha;

    /**
     * Response variable column.
     */
    @SerializedName("response_column")
    public ColSpecifierV3 responseColumn;

    /**
     * Column with observation weights. Giving some observation a weight of zero is equivalent to excluding it from the
     * dataset; giving an observation a relative weight of 2 is equivalent to repeating that row twice. Negative weights
     * are not allowed. Note: Weights are per-row observation weights and do not increase the size of the data frame.
     * This is typically the number of times a row is repeated, but non-integer values are supported as well. During
     * training, rows with higher weights matter more, due to the larger loss function pre-factor. If you set weight = 0
     * for a row, the returned prediction frame at that row is zero and this is incorrect. To get an accurate
     * prediction, remove all rows with weight == 0.
     */
    @SerializedName("weights_column")
    public ColSpecifierV3 weightsColumn;

    /**
     * Offset column. This will be added to the combination of columns before applying the link function.
     */
    @SerializedName("offset_column")
    public ColSpecifierV3 offsetColumn;

    /**
     * Column with cross-validation fold index assignment per observation.
     */
    @SerializedName("fold_column")
    public ColSpecifierV3 foldColumn;

    /**
     * Cross-validation fold assignment scheme, if fold_column is not specified. The 'Stratified' option will stratify
     * the folds based on the response variable, for classification problems.
     */
    @SerializedName("fold_assignment")
    public ModelParametersFoldAssignmentScheme foldAssignment;

    /**
     * Encoding scheme for categorical features
     */
    @SerializedName("categorical_encoding")
    public ModelParametersCategoricalEncodingScheme categoricalEncoding;

    /**
     * For every categorical feature, only use this many most frequent categorical levels for model training. Only used
     * for categorical_encoding == EnumLimited.
     */
    @SerializedName("max_categorical_levels")
    public int maxCategoricalLevels;

    /**
     * Names of columns to ignore for training.
     */
    @SerializedName("ignored_columns")
    public String[] ignoredColumns;

    /**
     * Ignore constant columns.
     */
    @SerializedName("ignore_const_cols")
    public boolean ignoreConstCols;

    /**
     * Whether to score during each iteration of model training.
     */
    @SerializedName("score_each_iteration")
    public boolean scoreEachIteration;

    /**
     * Model checkpoint to resume training with.
     */
    public ModelKeyV3 checkpoint;

    /**
     * Early stopping based on convergence of stopping_metric. Stop if simple moving average of length k of the
     * stopping_metric does not improve for k:=stopping_rounds scoring events (0 to disable)
     */
    @SerializedName("stopping_rounds")
    public int stoppingRounds;

    /**
     * Maximum allowed runtime in seconds for model training. Use 0 to disable.
     */
    @SerializedName("max_runtime_secs")
    public double maxRuntimeSecs;

    /**
     * Metric to use for early stopping (AUTO: logloss for classification, deviance for regression and anonomaly_score
     * for Isolation Forest). Note that custom and custom_increasing can only be used in GBM and DRF with the Python
     * client.
     */
    @SerializedName("stopping_metric")
    public ScoreKeeperStoppingMetric stoppingMetric;

    /**
     * Relative tolerance for metric-based stopping criterion (stop if relative improvement is not at least this much)
     */
    @SerializedName("stopping_tolerance")
    public double stoppingTolerance;

    /**
     * Gains/Lift table number of bins. 0 means disabled.. Default value -1 means automatic binning.
     */
    @SerializedName("gainslift_bins")
    public int gainsliftBins;

    /**
     * Reference to custom evaluation function, format: `language:keyName=funcName`
     */
    @SerializedName("custom_metric_func")
    public String customMetricFunc;

    /**
     * Reference to custom distribution, format: `language:keyName=funcName`
     */
    @SerializedName("custom_distribution_func")
    public String customDistributionFunc;

    /**
     * Automatically export generated models to this directory.
     */
    @SerializedName("export_checkpoints_dir")
    public String exportCheckpointsDir;

    /**
     * Set default multinomial AUC type.
     */
    @SerializedName("auc_type")
    public MultinomialAucType aucType;

    /**
     * Public constructor
     */
    public ModelParametersSchemaV3() {
        nfolds = 0;
        keepCrossValidationModels = false;
        keepCrossValidationPredictions = false;
        keepCrossValidationFoldAssignment = false;
        parallelizeCrossValidation = false;
        tweediePower = 0.0;
        quantileAlpha = 0.0;
        huberAlpha = 0.0;
        maxCategoricalLevels = 0;
        ignoreConstCols = false;
        scoreEachIteration = false;
        stoppingRounds = 0;
        maxRuntimeSecs = 0.0;
        stoppingTolerance = 0.0;
        gainsliftBins = 0;
        customMetricFunc = "";
        customDistributionFunc = "";
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
