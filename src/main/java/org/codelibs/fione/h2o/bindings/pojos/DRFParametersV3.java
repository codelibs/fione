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

public class DRFParametersV3 extends SharedTreeParametersV3 {

    /**
     * Number of variables randomly sampled as candidates at each split. If set to -1, defaults to sqrt{p} for
     * classification and p/3 for regression (where p is the # of predictors
     */
    public int mtries;

    /**
     * For binary classification: Build 2x as many trees (one per class) - can lead to higher accuracy.
     */
    @SerializedName("binomial_double_trees")
    public boolean binomialDoubleTrees;

    /**
     * Row sample rate per tree (from 0.0 to 1.0)
     */
    @SerializedName("sample_rate")
    public double sampleRate;

    /*------------------------------------------------------------------------------------------------------------------
    //                                                  INHERITED
    //------------------------------------------------------------------------------------------------------------------

    // Balance training data class counts via over/under-sampling (for imbalanced data).
    public boolean balanceClasses;

    // Desired over/under-sampling ratios per class (in lexicographic order). If not specified, sampling factors will be
    // automatically computed to obtain class balance during training. Requires balance_classes.
    public float[] classSamplingFactors;

    // Maximum relative size of the training data after balancing class counts (can be less than 1.0). Requires
    // balance_classes.
    public float maxAfterBalanceSize;

    // [Deprecated] Maximum size (# classes) for confusion matrices to be printed in the Logs
    public int maxConfusionMatrixSize;

    // Number of trees.
    public int ntrees;

    // Maximum tree depth (0 for unlimited).
    public int maxDepth;

    // Fewest allowed (weighted) observations in a leaf.
    public double minRows;

    // For numerical columns (real/int), build a histogram of (at least) this many bins, then split at the best point
    public int nbins;

    // For numerical columns (real/int), build a histogram of (at most) this many bins at the root level, then decrease
    // by factor of two per level
    public int nbinsTopLevel;

    // For categorical columns (factors), build a histogram of this many bins, then split at the best point. Higher
    // values can lead to more overfitting.
    public int nbinsCats;

    // r2_stopping is no longer supported and will be ignored if set - please use stopping_rounds, stopping_metric and
    // stopping_tolerance instead. Previous version of H2O would stop making trees when the R^2 metric equals or exceeds
    // this
    public double r2Stopping;

    // Seed for pseudo random number generator (if applicable)
    public long seed;

    // Run on one node only; no network overhead but fewer cpus used. Suitable for small datasets.
    public boolean buildTreeOneNode;

    // A list of row sample rates per class (relative fraction for each class, from 0.0 to 1.0), for each tree
    public double[] sampleRatePerClass;

    // Column sample rate per tree (from 0.0 to 1.0)
    public double colSampleRatePerTree;

    // Relative change of the column sampling rate for every level (must be > 0.0 and <= 2.0)
    public double colSampleRateChangePerLevel;

    // Score the model after every so many trees. Disabled if set to 0.
    public int scoreTreeInterval;

    // Minimum relative improvement in squared error reduction for a split to happen
    public double minSplitImprovement;

    // What type of histogram to use for finding optimal split points
    public TreeSharedTreeModelSharedTreeParametersHistogramType histogramType;

    // Use Platt Scaling to calculate calibrated class probabilities. Calibration can provide more accurate estimates of
    // class probabilities.
    public boolean calibrateModel;

    // Calibration frame for Platt Scaling
    public FrameKeyV3 calibrationFrame;

    // Check if response column is constant. If enabled, then an exception is thrown if the response column is a
    // constant value.If disabled, then model will train regardless of the response column being a constant value or
    // not.
    public boolean checkConstantResponse;

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
    public DRFParametersV3() {
        mtries = -1;
        binomialDoubleTrees = false;
        sampleRate = 0.632;
        balanceClasses = false;
        maxAfterBalanceSize = 5.0f;
        maxConfusionMatrixSize = 20;
        ntrees = 50;
        maxDepth = 20;
        minRows = 1.0;
        nbins = 20;
        nbinsTopLevel = 1024;
        nbinsCats = 1024;
        r2Stopping = 1.7976931348623157e+308;
        seed = -1L;
        buildTreeOneNode = false;
        colSampleRatePerTree = 1.0;
        colSampleRateChangePerLevel = 1.0;
        scoreTreeInterval = 0;
        minSplitImprovement = 1e-05;
        histogramType = TreeSharedTreeModelSharedTreeParametersHistogramType.AUTO;
        calibrateModel = false;
        checkConstantResponse = true;
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
