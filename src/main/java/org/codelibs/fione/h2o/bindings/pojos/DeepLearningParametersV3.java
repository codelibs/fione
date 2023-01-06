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

public class DeepLearningParametersV3 extends ModelParametersSchemaV3 {

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
     * [Deprecated] Maximum size (# classes) for confusion matrices to be printed in the Logs.
     */
    @SerializedName("max_confusion_matrix_size")
    public int maxConfusionMatrixSize;

    /**
     * Activation function.
     */
    public DeepLearningActivation activation;

    /**
     * Hidden layer sizes (e.g. [100, 100]).
     */
    public int[] hidden;

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
     * Adaptive learning rate.
     */
    @SerializedName("adaptive_rate")
    public boolean adaptiveRate;

    /**
     * Adaptive learning rate time decay factor (similarity to prior updates).
     */
    public double rho;

    /**
     * Adaptive learning rate smoothing factor (to avoid divisions by zero and allow progress).
     */
    public double epsilon;

    /**
     * Learning rate (higher => less stable, lower => slower convergence).
     */
    public double rate;

    /**
     * Learning rate annealing: rate / (1 + rate_annealing * samples).
     */
    @SerializedName("rate_annealing")
    public double rateAnnealing;

    /**
     * Learning rate decay factor between layers (N-th layer: rate * rate_decay ^ (n - 1).
     */
    @SerializedName("rate_decay")
    public double rateDecay;

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
     * Use Nesterov accelerated gradient (recommended).
     */
    @SerializedName("nesterov_accelerated_gradient")
    public boolean nesterovAcceleratedGradient;

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
     * L1 regularization (can add stability and improve generalization, causes many weights to become 0).
     */
    public double l1;

    /**
     * L2 regularization (can add stability and improve generalization, causes many weights to be small.
     */
    public double l2;

    /**
     * Constraint for squared sum of incoming weights per unit (e.g. for Rectifier).
     */
    @SerializedName("max_w2")
    public float maxW2;

    /**
     * Initial weight distribution.
     */
    @SerializedName("initial_weight_distribution")
    public DeepLearningInitialWeightDistribution initialWeightDistribution;

    /**
     * Uniform: -value...value, Normal: stddev.
     */
    @SerializedName("initial_weight_scale")
    public double initialWeightScale;

    /**
     * A list of H2OFrame ids to initialize the weight matrices of this model with.
     */
    @SerializedName("initial_weights")
    public FrameKeyV3[] initialWeights;

    /**
     * A list of H2OFrame ids to initialize the bias vectors of this model with.
     */
    @SerializedName("initial_biases")
    public FrameKeyV3[] initialBiases;

    /**
     * Loss function.
     */
    public DeepLearningLoss loss;

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
     * Method used to sample validation dataset for scoring.
     */
    @SerializedName("score_validation_sampling")
    public DeepLearningClassSamplingMethod scoreValidationSampling;

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
     * Use all factor levels of categorical variables. Otherwise, the first factor level is omitted (without loss of
     * accuracy). Useful for variable importances and auto-enabled for autoencoder.
     */
    @SerializedName("use_all_factor_levels")
    public boolean useAllFactorLevels;

    /**
     * If enabled, automatically standardize the data. If disabled, the user must provide properly scaled input data.
     */
    public boolean standardize;

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
     * Enable fast mode (minor approximation in back-propagation).
     */
    @SerializedName("fast_mode")
    public boolean fastMode;

    /**
     * Force extra load balancing to increase training speed for small datasets (to keep all cores busy).
     */
    @SerializedName("force_load_balance")
    public boolean forceLoadBalance;

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
     * Enable shuffling of training data (recommended if training data is replicated and train_samples_per_iteration is
     * close to #nodes x #rows, of if using balance_classes).
     */
    @SerializedName("shuffle_training_data")
    public boolean shuffleTrainingData;

    /**
     * Handling of missing values. Either MeanImputation or Skip.
     */
    @SerializedName("missing_values_handling")
    public DeepLearningMissingValuesHandling missingValuesHandling;

    /**
     * Sparse data handling (more efficient for data with lots of 0 values).
     */
    public boolean sparse;

    /**
     * #DEPRECATED Use a column major weight matrix for input layer. Can speed up forward propagation, but might slow
     * down backpropagation.
     */
    @SerializedName("col_major")
    public boolean colMajor;

    /**
     * Average activation for sparse auto-encoder. #Experimental
     */
    @SerializedName("average_activation")
    public double averageActivation;

    /**
     * Sparsity regularization. #Experimental
     */
    @SerializedName("sparsity_beta")
    public double sparsityBeta;

    /**
     * Max. number of categorical features, enforced via hashing. #Experimental
     */
    @SerializedName("max_categorical_features")
    public int maxCategoricalFeatures;

    /**
     * Force reproducibility on small data (will be slow - only uses 1 thread).
     */
    public boolean reproducible;

    /**
     * Whether to export Neural Network weights and biases to H2O Frames.
     */
    @SerializedName("export_weights_and_biases")
    public boolean exportWeightsAndBiases;

    /**
     * Mini-batch size (smaller leads to better fit, larger can speed up and generalize better).
     */
    @SerializedName("mini_batch_size")
    public int miniBatchSize;

    /**
     * Elastic averaging between compute nodes can improve distributed model convergence. #Experimental
     */
    @SerializedName("elastic_averaging")
    public boolean elasticAveraging;

    /**
     * Elastic averaging moving rate (only if elastic averaging is enabled).
     */
    @SerializedName("elastic_averaging_moving_rate")
    public double elasticAveragingMovingRate;

    /**
     * Elastic averaging regularization strength (only if elastic averaging is enabled).
     */
    @SerializedName("elastic_averaging_regularization")
    public double elasticAveragingRegularization;

    /**
     * Pretrained autoencoder model to initialize this model with.
     */
    @SerializedName("pretrained_autoencoder")
    public ModelKeyV3 pretrainedAutoencoder;

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
    public DeepLearningParametersV3() {
        balanceClasses = false;
        maxAfterBalanceSize = 5.0f;
        maxConfusionMatrixSize = 20;
        activation = DeepLearningActivation.Rectifier;
        hidden = new int[] { 200, 200 };
        epochs = 10.0;
        trainSamplesPerIteration = -2L;
        targetRatioCommToComp = 0.05;
        seed = -1L;
        adaptiveRate = true;
        rho = 0.99;
        epsilon = 1e-08;
        rate = 0.005;
        rateAnnealing = 1e-06;
        rateDecay = 1.0;
        momentumStart = 0.0;
        momentumRamp = 1000000.0;
        momentumStable = 0.0;
        nesterovAcceleratedGradient = true;
        inputDropoutRatio = 0.0;
        l1 = 0.0;
        l2 = 0.0;
        maxW2 = 3.4028235e+38f;
        initialWeightDistribution = DeepLearningInitialWeightDistribution.UniformAdaptive;
        initialWeightScale = 1.0;
        loss = DeepLearningLoss.Automatic;
        scoreInterval = 5.0;
        scoreTrainingSamples = 10000L;
        scoreValidationSamples = 0L;
        scoreDutyCycle = 0.1;
        classificationStop = 0.0;
        regressionStop = 1e-06;
        quietMode = false;
        scoreValidationSampling = DeepLearningClassSamplingMethod.Uniform;
        overwriteWithBestModel = true;
        autoencoder = false;
        useAllFactorLevels = true;
        standardize = true;
        diagnostics = true;
        variableImportances = true;
        fastMode = true;
        forceLoadBalance = true;
        replicateTrainingData = true;
        singleNodeMode = false;
        shuffleTrainingData = false;
        missingValuesHandling = DeepLearningMissingValuesHandling.MeanImputation;
        sparse = false;
        colMajor = false;
        averageActivation = 0.0;
        sparsityBeta = 0.0;
        maxCategoricalFeatures = 2147483647;
        reproducible = false;
        exportWeightsAndBiases = false;
        miniBatchSize = 1;
        elasticAveraging = false;
        elasticAveragingMovingRate = 0.9;
        elasticAveragingRegularization = 0.001;
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
        return new GsonBuilder().serializeSpecialFloatingPointValues().create().toJson(this);
    }

}
