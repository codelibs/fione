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

public class InfogramParametersV3 extends ModelParametersSchemaV3 {

    /**
     * Seed for pseudo random number generator (if applicable).
     */
    public long seed;

    /**
     * Standardize numeric columns to have zero mean and unit variance.
     */
    public boolean standardize;

    /**
     * Plug Values (a single row frame containing values that will be used to impute missing values of the
     * training/validation frame, use with conjunction missing_values_handling = PlugValues).
     */
    @SerializedName("plug_values")
    public FrameKeyV3 plugValues;

    /**
     * Maximum number of iterations.
     */
    @SerializedName("max_iterations")
    public int maxIterations;

    /**
     * Prior probability for y==1. To be used only for logistic regression iff the data has been sampled and the mean of
     * response does not reflect reality.
     */
    public double prior;

    /**
     * Balance training data class counts via over/under-sampling (for imbalanced data).
     */
    @SerializedName("balance_classes")
    public boolean balanceClasses;

    /**
     * Desired over/under-sampling ratios per class (in lexicographic order). If not specified, sampling factors will be
     * automatically computed to obtain class balance during training. Requires balance_classes.
     */
    @SerializedName("class_sampling_factors")
    public float[] classSamplingFactors;

    /**
     * Maximum relative size of the training data after balancing class counts (can be less than 1.0). Requires
     * balance_classes.
     */
    @SerializedName("max_after_balance_size")
    public float maxAfterBalanceSize;

    /**
     * Type of machine learning algorithm used to build the infogram. Options include 'AUTO' (gbm), 'deeplearning' (Deep
     * Learning with default parameters), 'drf' (Random Forest with default parameters), 'gbm' (GBM with default
     * parameters), 'glm' (GLM with default parameters), or 'xgboost' (if available, XGBoost with default parameters).
     */
    public InfogramAlgorithm algorithm;

    /**
     * Customized parameters for the machine learning algorithm specified in the algorithm parameter.
     */
    @SerializedName("algorithm_params")
    public String algorithmParams;

    /**
     * Columns that contain features that are sensitive and need to be protected (legally, or otherwise), if applicable.
     * These features (e.g. race, gender, etc) should not drive the prediction of the response.
     */
    @SerializedName("protected_columns")
    public String[] protectedColumns;

    /**
     * A number between 0 and 1 representing a threshold for total information, defaulting to 0.1. For a specific
     * feature, if the total information is higher than this threshold, and the corresponding net information is also
     * higher than the threshold ``net_information_threshold``, that feature will be considered admissible. The total
     * information is the x-axis of the Core Infogram. Default is -1 which gets set to 0.1.
     */
    @SerializedName("total_information_threshold")
    public double totalInformationThreshold;

    /**
     * A number between 0 and 1 representing a threshold for net information, defaulting to 0.1.  For a specific
     * feature, if the net information is higher than this threshold, and the corresponding total information is also
     * higher than the total_information_threshold, that feature will be considered admissible. The net information is
     * the y-axis of the Core Infogram. Default is -1 which gets set to 0.1.
     */
    @SerializedName("net_information_threshold")
    public double netInformationThreshold;

    /**
     * A number between 0 and 1 representing a threshold for the relevance index, defaulting to 0.1.  This is only used
     * when ``protected_columns`` is set by the user.  For a specific feature, if the relevance index value is higher
     * than this threshold, and the corresponding safety index is also higher than the safety_index_threshold``, that
     * feature will be considered admissible.  The relevance index is the x-axis of the Fair Infogram. Default is -1
     * which gets set to 0.1.
     */
    @SerializedName("relevance_index_threshold")
    public double relevanceIndexThreshold;

    /**
     * A number between 0 and 1 representing a threshold for the safety index, defaulting to 0.1.  This is only used
     * when protected_columns is set by the user.  For a specific feature, if the safety index value is higher than this
     * threshold, and the corresponding relevance index is also higher than the relevance_index_threshold, that feature
     * will be considered admissible.  The safety index is the y-axis of the Fair Infogram. Default is -1 which gets set
     * to 0.1.
     */
    @SerializedName("safety_index_threshold")
    public double safetyIndexThreshold;

    /**
     * The fraction of training frame to use to build the infogram model. Defaults to 1.0, and any value greater than 0
     * and less than or equal to 1.0 is acceptable.
     */
    @SerializedName("data_fraction")
    public double dataFraction;

    /**
     * An integer specifying the number of columns to evaluate in the infogram.  The columns are ranked by variable
     * importance, and the top N are evaluated.  Defaults to 50.
     */
    @SerializedName("top_n_features")
    public int topNFeatures;

    /*------------------------------------------------------------------------------------------------------------------
    //                                                  INHERITED
    //------------------------------------------------------------------------------------------------------------------

    // Destination id for this model; auto-generated if not specified.
    public ModelKeyV3 modelId;

    // Id of the training data frame.
    public FrameKeyV3 trainingFrame;

    // Id of the validation data frame.
    public FrameKeyV3 validationFrame;

    // Number of folds for K-fold cross-validation (0 to disable or >= 2).
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
    // training, rows with higher weights matter more, due to the larger loss function pre-factor. If you set weight = 0
    // for a row, the returned prediction frame at that row is zero and this is incorrect. To get an accurate
    // prediction, remove all rows with weight == 0.
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

    // Gains/Lift table number of bins. 0 means disabled.. Default value -1 means automatic binning.
    public int gainsliftBins;

    // Reference to custom evaluation function, format: `language:keyName=funcName`
    public String customMetricFunc;

    // Reference to custom distribution, format: `language:keyName=funcName`
    public String customDistributionFunc;

    // Automatically export generated models to this directory.
    public String exportCheckpointsDir;

    // Set default multinomial AUC type.
    public MultinomialAucType aucType;

    */

    /**
     * Public constructor
     */
    public InfogramParametersV3() {
        seed = -1L;
        standardize = false;
        maxIterations = 0;
        prior = 0.0;
        balanceClasses = false;
        maxAfterBalanceSize = 5.0f;
        algorithm = InfogramAlgorithm.AUTO;
        algorithmParams = "";
        totalInformationThreshold = -1.0;
        netInformationThreshold = -1.0;
        relevanceIndexThreshold = -1.0;
        safetyIndexThreshold = -1.0;
        dataFraction = 1.0;
        topNFeatures = 50;
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
        gainsliftBins = -1;
        customMetricFunc = "";
        customDistributionFunc = "";
        exportCheckpointsDir = "";
        aucType = MultinomialAucType.AUTO;
    }

    /**
     * Return the contents of this object as a JSON String.
     */
    @Override
    public String toString() {
        return new Gson().toJson(this);
    }

}
