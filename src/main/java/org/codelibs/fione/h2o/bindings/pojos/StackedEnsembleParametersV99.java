/*
 * Copyright 2012-2020 CodeLibs Project and the Others.
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

public class StackedEnsembleParametersV99 extends ModelParametersSchemaV3 {

    /**
     * List of models (or model ids) to ensemble/stack together. If not using blending frame, then models must have been
     * cross-validated using nfolds &gt; 1, and folds must be identical across models.
     */
    @SerializedName("base_models")
    public ModelKeyV3[] baseModels;

    /**
     * Type of algorithm to use as the metalearner. Options include 'AUTO' (GLM with non negative weights; if
     * validation_frame is present, a lambda search is performed), 'glm' (GLM with default parameters), 'gbm' (GBM with
     * default parameters), 'drf' (Random Forest with default parameters), or 'deeplearning' (Deep Learning with default
     * parameters).
     */
    @SerializedName("metalearner_algorithm")
    public EnsembleMetalearnerAlgorithm metalearnerAlgorithm;

    /**
     * Number of folds for K-fold cross-validation of the metalearner algorithm (0 to disable or &gt;= 2).
     */
    @SerializedName("metalearner_nfolds")
    public int metalearnerNfolds;

    /**
     * Cross-validation fold assignment scheme for metalearner cross-validation.  Defaults to AUTO (which is currently
     * set to Random). The 'Stratified' option will stratify the folds based on the response variable, for
     * classification problems.
     */
    @SerializedName("metalearner_fold_assignment")
    public ModelParametersFoldAssignmentScheme metalearnerFoldAssignment;

    /**
     * Column with cross-validation fold index assignment per observation for cross-validation of the metalearner.
     */
    @SerializedName("metalearner_fold_column")
    public ColSpecifierV3 metalearnerFoldColumn;

    /**
     * Keep level one frame used for metalearner training.
     */
    @SerializedName("keep_levelone_frame")
    public boolean keepLeveloneFrame;

    /**
     * Parameters for metalearner algorithm
     */
    @SerializedName("metalearner_params")
    public String metalearnerParams;

    /**
     * Frame used to compute the predictions that serve as the training frame for the metalearner (triggers blending
     * mode if provided)
     */
    @SerializedName("blending_frame")
    public FrameKeyV3 blendingFrame;

    /**
     * Seed for random numbers; passed through to the metalearner algorithm. Defaults to -1 (time-based random number)
     */
    public long seed;

    /*------------------------------------------------------------------------------------------------------------------
    //                                                  INHERITED
    //------------------------------------------------------------------------------------------------------------------

    // Destination id for this model; auto-generated if not specified.
    public ModelKeyV3 modelId;

    // Id of the training data frame.
    public FrameKeyV3 trainingFrame;

    // Id of the validation data frame.
    public FrameKeyV3 validationFrame;

    // Number of folds for K-fold cross-validation (0 to disable or &gt;= 2).
    public int nfolds;

    // Whether to keep the cross-validation models.
    public boolean keepCrossValidationModels;

    // Whether to keep the predictions of the cross-validation models.
    public boolean keepCrossValidationPredictions;

    // Whether to keep the cross-validation fold assignment.
    public boolean keepCrossValidationFoldAssignment;

    // Allow parallel training of cross-validation models
    public boolean parallelizeCrossValidation;

    // Distribution function
    public GenmodelutilsDistributionFamily distribution;

    // Tweedie power for Tweedie regression, must be between 1 and 2.
    public double tweediePower;

    // Desired quantile for Quantile regression, must be between 0 and 1.
    public double quantileAlpha;

    // Desired quantile for Huber/M-regression (threshold between quadratic and linear loss, must be between 0 and 1).
    public double huberAlpha;

    // Response variable column.
    public ColSpecifierV3 responseColumn;

    // Column with observation weights. Giving some observation a weight of zero is equivalent to excluding it from the
    // dataset; giving an observation a relative weight of 2 is equivalent to repeating that row twice. Negative weights
    // are not allowed. Note: Weights are per-row observation weights and do not increase the size of the data frame.
    // This is typically the number of times a row is repeated, but non-integer values are supported as well. During
    // training, rows with higher weights matter more, due to the larger loss function pre-factor.
    public ColSpecifierV3 weightsColumn;

    // Offset column. This will be added to the combination of columns before applying the link function.
    public ColSpecifierV3 offsetColumn;

    // Column with cross-validation fold index assignment per observation.
    public ColSpecifierV3 foldColumn;

    // Cross-validation fold assignment scheme, if fold_column is not specified. The 'Stratified' option will stratify
    // the folds based on the response variable, for classification problems.
    public ModelParametersFoldAssignmentScheme foldAssignment;

    // Encoding scheme for categorical features
    public ModelParametersCategoricalEncodingScheme categoricalEncoding;

    // For every categorical feature, only use this many most frequent categorical levels for model training. Only used
    // for categorical_encoding == EnumLimited.
    public int maxCategoricalLevels;

    // Names of columns to ignore for training.
    public String[] ignoredColumns;

    // Ignore constant columns.
    public boolean ignoreConstCols;

    // Whether to score during each iteration of model training.
    public boolean scoreEachIteration;

    // Model checkpoint to resume training with.
    public ModelKeyV3 checkpoint;

    // Early stopping based on convergence of stopping_metric. Stop if simple moving average of length k of the
    // stopping_metric does not improve for k:=stopping_rounds scoring events (0 to disable)
    public int stoppingRounds;

    // Maximum allowed runtime in seconds for model training. Use 0 to disable.
    public double maxRuntimeSecs;

    // Metric to use for early stopping (AUTO: logloss for classification, deviance for regression and anonomaly_score
    // for Isolation Forest). Note that custom and custom_increasing can only be used in GBM and DRF with the Python
    // client.
    public ScoreKeeperStoppingMetric stoppingMetric;

    // Relative tolerance for metric-based stopping criterion (stop if relative improvement is not at least this much)
    public double stoppingTolerance;

    // Reference to custom evaluation function, format: `language:keyName=funcName`
    public String customMetricFunc;

    // Reference to custom distribution, format: `language:keyName=funcName`
    public String customDistributionFunc;

    // Automatically export generated models to this directory.
    public String exportCheckpointsDir;

    */

    /**
     * Public constructor
     */
    public StackedEnsembleParametersV99() {
        baseModels = new ModelKeyV3[] {};
        metalearnerAlgorithm = EnsembleMetalearnerAlgorithm.AUTO;
        metalearnerNfolds = 0;
        keepLeveloneFrame = false;
        metalearnerParams = "";
        seed = -1L;
        nfolds = 0;
        keepCrossValidationModels = true;
        keepCrossValidationPredictions = false;
        keepCrossValidationFoldAssignment = false;
        parallelizeCrossValidation = true;
        distribution = GenmodelutilsDistributionFamily.AUTO;
        tweediePower = 1.5;
        quantileAlpha = 0.5;
        huberAlpha = 0.9;
        foldAssignment = ModelParametersFoldAssignmentScheme.AUTO;
        categoricalEncoding = ModelParametersCategoricalEncodingScheme.AUTO;
        maxCategoricalLevels = 10;
        ignoreConstCols = true;
        scoreEachIteration = false;
        stoppingRounds = 0;
        maxRuntimeSecs = 0.0;
        stoppingMetric = ScoreKeeperStoppingMetric.AUTO;
        stoppingTolerance = 0.001;
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
