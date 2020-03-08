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

public class DeepWaterParametersV3 extends ModelParametersSchemaV3 {

    /**
     * Problem type, auto-detected by default. If set to image, the H2OFrame must contain a string column containing the
     * path (URI or URL) to the images in the first column. If set to text, the H2OFrame must contain a string column
     * containing the text in the first column. If set to dataset, Deep Water behaves just like any other H2O Model and
     * builds a model on the provided H2OFrame (non-String columns).
     */
    @SerializedName("problem_type")
    public DeepWaterParametersProblemType problemType;

    /**
     * Activation function. Only used if no user-defined network architecture file is provided, and only for
     * problem_type=dataset.
     */
    public DeepWaterParametersActivation activation;

    /**
     * Hidden layer sizes (e.g. [200, 200]). Only used if no user-defined network architecture file is provided, and
     * only for problem_type=dataset.
     */
    public int[] hidden;

    /**
     * Input layer dropout ratio (can improve generalization, try 0.1 or 0.2).
     */
    @SerializedName("input_dropout_ratio")
    public double inputDropoutRatio;

    /**
     * Hidden layer dropout ratios (can improve generalization), specify one value per hidden layer, defaults to 0.5.
     */
    @SerializedName("hidden_dropout_ratios")
    public double[] hiddenDropoutRatios;

    /**
     * [Deprecated] Maximum size (# classes) for confusion matrices to be printed in the Logs.
     */
    @SerializedName("max_confusion_matrix_size")
    public int maxConfusionMatrixSize;

    /**
     * Sparse data handling (more efficient for data with lots of 0 values).
     */
    public boolean sparse;

    /**
     * Max. number (top K) of predictions to use for hit ratio computation (for multi-class only, 0 to disable).
     */
    @SerializedName("max_hit_ratio_k")
    public int maxHitRatioK;

    /**
     * How many times the dataset should be iterated (streamed), can be fractional.
     */
    public double epochs;

    /**
     * Number of training samples (globally) per MapReduce iteration. Special values are 0: one epoch, -1: all available
     * data (e.g., replicated training data), -2: automatic.
     */
    @SerializedName("train_samples_per_iteration")
    public long trainSamplesPerIteration;

    /**
     * Target ratio of communication overhead to computation. Only for multi-node operation and
     * train_samples_per_iteration = -2 (auto-tuning).
     */
    @SerializedName("target_ratio_comm_to_comp")
    public double targetRatioCommToComp;

    /**
     * Seed for random numbers (affects sampling) - Note: only reproducible when running single threaded.
     */
    public long seed;

    /**
     * Learning rate (higher =&gt; less stable, lower =&gt; slower convergence).
     */
    @SerializedName("learning_rate")
    public double learningRate;

    /**
     * Learning rate annealing: rate / (1 + rate_annealing * samples).
     */
    @SerializedName("learning_rate_annealing")
    public double learningRateAnnealing;

    /**
     * Initial momentum at the beginning of training (try 0.5).
     */
    @SerializedName("momentum_start")
    public double momentumStart;

    /**
     * Number of training samples for which momentum increases.
     */
    @SerializedName("momentum_ramp")
    public double momentumRamp;

    /**
     * Final momentum after the ramp is over (try 0.99).
     */
    @SerializedName("momentum_stable")
    public double momentumStable;

    /**
     * Shortest time interval (in seconds) between model scoring.
     */
    @SerializedName("score_interval")
    public double scoreInterval;

    /**
     * Number of training set samples for scoring (0 for all).
     */
    @SerializedName("score_training_samples")
    public long scoreTrainingSamples;

    /**
     * Number of validation set samples for scoring (0 for all).
     */
    @SerializedName("score_validation_samples")
    public long scoreValidationSamples;

    /**
     * Maximum duty cycle fraction for scoring (lower: more training, higher: more scoring).
     */
    @SerializedName("score_duty_cycle")
    public double scoreDutyCycle;

    /**
     * Stopping criterion for classification error fraction on training data (-1 to disable).
     */
    @SerializedName("classification_stop")
    public double classificationStop;

    /**
     * Stopping criterion for regression error (MSE) on training data (-1 to disable).
     */
    @SerializedName("regression_stop")
    public double regressionStop;

    /**
     * Enable quiet mode for less output to standard output.
     */
    @SerializedName("quiet_mode")
    public boolean quietMode;

    /**
     * If enabled, override the final model with the best model found during training.
     */
    @SerializedName("overwrite_with_best_model")
    public boolean overwriteWithBestModel;

    /**
     * Auto-Encoder.
     */
    public boolean autoencoder;

    /**
     * Enable diagnostics for hidden layers.
     */
    public boolean diagnostics;

    /**
     * Compute variable importances for input features (Gedeon method) - can be slow for large networks.
     */
    @SerializedName("variable_importances")
    public boolean variableImportances;

    /**
     * Replicate the entire training dataset onto every node for faster training on small datasets.
     */
    @SerializedName("replicate_training_data")
    public boolean replicateTrainingData;

    /**
     * Run on a single node for fine-tuning of model parameters.
     */
    @SerializedName("single_node_mode")
    public boolean singleNodeMode;

    /**
     * Enable global shuffling of training data.
     */
    @SerializedName("shuffle_training_data")
    public boolean shuffleTrainingData;

    /**
     * Mini-batch size (smaller leads to better fit, larger can speed up and generalize better).
     */
    @SerializedName("mini_batch_size")
    public int miniBatchSize;

    /**
     * Clip gradients once their absolute value is larger than this value.
     */
    @SerializedName("clip_gradient")
    public double clipGradient;

    /**
     * Network architecture.
     */
    public DeepWaterParametersNetwork network;

    /**
     * Deep Learning Backend.
     */
    public DeepWaterParametersBackend backend;

    /**
     * Width and height of image.
     */
    @SerializedName("image_shape")
    public int[] imageShape;

    /**
     * Number of (color) channels.
     */
    public int channels;

    /**
     * Whether to use a GPU (if available).
     */
    public boolean gpu;

    /**
     * Device IDs (which GPUs to use).
     */
    @SerializedName("device_id")
    public int[] deviceId;

    /**
     * Whether to cache the data in memory (automatically disabled if data size is too large).
     */
    @SerializedName("cache_data")
    public boolean cacheData;

    /**
     * Path of file containing network definition (graph, architecture).
     */
    @SerializedName("network_definition_file")
    public String networkDefinitionFile;

    /**
     * Path of file containing network (initial) parameters (weights, biases).
     */
    @SerializedName("network_parameters_file")
    public String networkParametersFile;

    /**
     * Path of file containing the mean image data for data normalization.
     */
    @SerializedName("mean_image_file")
    public String meanImageFile;

    /**
     * Path (prefix) where to export the native model parameters after every iteration.
     */
    @SerializedName("export_native_parameters_prefix")
    public String exportNativeParametersPrefix;

    /**
     * If enabled, automatically standardize the data. If disabled, the user must provide properly scaled input data.
     */
    public boolean standardize;

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
    public DeepWaterParametersV3() {
        problemType = DeepWaterParametersProblemType.auto;
        inputDropoutRatio = 0.0;
        maxConfusionMatrixSize = 20;
        sparse = false;
        maxHitRatioK = 0;
        epochs = 10.0;
        trainSamplesPerIteration = -2L;
        targetRatioCommToComp = 0.05;
        seed = -1L;
        learningRate = 0.001;
        learningRateAnnealing = 1e-06;
        momentumStart = 0.9;
        momentumRamp = 10000.0;
        momentumStable = 0.9;
        scoreInterval = 5.0;
        scoreTrainingSamples = 10000L;
        scoreValidationSamples = 0L;
        scoreDutyCycle = 0.1;
        classificationStop = 0.0;
        regressionStop = 0.0;
        quietMode = false;
        overwriteWithBestModel = true;
        autoencoder = false;
        diagnostics = false;
        variableImportances = false;
        replicateTrainingData = true;
        singleNodeMode = false;
        shuffleTrainingData = true;
        miniBatchSize = 32;
        clipGradient = 10.0;
        network = DeepWaterParametersNetwork.auto;
        backend = DeepWaterParametersBackend.mxnet;
        imageShape = new int[] { 0, 0 };
        channels = 3;
        gpu = true;
        deviceId = new int[] { 0 };
        cacheData = true;
        networkDefinitionFile = "";
        networkParametersFile = "";
        meanImageFile = "";
        exportNativeParametersPrefix = "";
        standardize = true;
        balanceClasses = false;
        maxAfterBalanceSize = 5.0f;
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
        stoppingRounds = 5;
        maxRuntimeSecs = 0.0;
        stoppingMetric = ScoreKeeperStoppingMetric.AUTO;
        stoppingTolerance = 0.0;
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
