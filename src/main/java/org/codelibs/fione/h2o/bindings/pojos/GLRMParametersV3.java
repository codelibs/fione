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

public class GLRMParametersV3 extends ModelParametersSchemaV3 {

    /**
     * Transformation of training data
     */
    public DataInfoTransformType transform;

    /**
     * Rank of matrix approximation
     */
    public int k;

    /**
     * Numeric loss function
     */
    public GenmodelalgosglrmGlrmLoss loss;

    /**
     * Categorical loss function
     */
    @SerializedName("multi_loss")
    public GenmodelalgosglrmGlrmLoss multiLoss;

    /**
     * Loss function by column (override)
     */
    @SerializedName("loss_by_col")
    public GenmodelalgosglrmGlrmLoss[] lossByCol;

    /**
     * Loss function by column index (override)
     */
    @SerializedName("loss_by_col_idx")
    public int[] lossByColIdx;

    /**
     * Length of period (only used with periodic loss function)
     */
    public int period;

    /**
     * Regularization function for X matrix
     */
    @SerializedName("regularization_x")
    public GenmodelalgosglrmGlrmRegularizer regularizationX;

    /**
     * Regularization function for Y matrix
     */
    @SerializedName("regularization_y")
    public GenmodelalgosglrmGlrmRegularizer regularizationY;

    /**
     * Regularization weight on X matrix
     */
    @SerializedName("gamma_x")
    public double gammaX;

    /**
     * Regularization weight on Y matrix
     */
    @SerializedName("gamma_y")
    public double gammaY;

    /**
     * Maximum number of iterations
     */
    @SerializedName("max_iterations")
    public int maxIterations;

    /**
     * Maximum number of updates, defaults to 2*max_iterations
     */
    @SerializedName("max_updates")
    public int maxUpdates;

    /**
     * Initial step size
     */
    @SerializedName("init_step_size")
    public double initStepSize;

    /**
     * Minimum step size
     */
    @SerializedName("min_step_size")
    public double minStepSize;

    /**
     * RNG seed for initialization
     */
    public long seed;

    /**
     * Initialization mode
     */
    public GenmodelalgosglrmGlrmInitialization init;

    /**
     * Method for computing SVD during initialization (Caution: Randomized is currently experimental and unstable)
     */
    @SerializedName("svd_method")
    public SVDMethod svdMethod;

    /**
     * User-specified initial Y
     */
    @SerializedName("user_y")
    public FrameKeyV3 userY;

    /**
     * User-specified initial X
     */
    @SerializedName("user_x")
    public FrameKeyV3 userX;

    /**
     * [Deprecated] Use representation_name instead.  Frame key to save resulting X.
     */
    @SerializedName("loading_name")
    public String loadingName;

    /**
     * Frame key to save resulting X
     */
    @SerializedName("representation_name")
    public String representationName;

    /**
     * Expand categorical columns in user-specified initial Y
     */
    @SerializedName("expand_user_y")
    public boolean expandUserY;

    /**
     * Reconstruct original training data by reversing transform
     */
    @SerializedName("impute_original")
    public boolean imputeOriginal;

    /**
     * Recover singular values and eigenvectors of XY
     */
    @SerializedName("recover_svd")
    public boolean recoverSvd;

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
    public GLRMParametersV3() {
        transform = DataInfoTransformType.NONE;
        k = 1;
        loss = GenmodelalgosglrmGlrmLoss.Quadratic;
        multiLoss = GenmodelalgosglrmGlrmLoss.Categorical;
        period = 1;
        regularizationX = GenmodelalgosglrmGlrmRegularizer.None;
        regularizationY = GenmodelalgosglrmGlrmRegularizer.None;
        gammaX = 0.0;
        gammaY = 0.0;
        maxIterations = 1000;
        maxUpdates = 2000;
        initStepSize = 1.0;
        minStepSize = 0.0001;
        seed = -1L;
        init = GenmodelalgosglrmGlrmInitialization.PlusPlus;
        svdMethod = SVDMethod.Randomized;
        loadingName = "";
        representationName = "";
        expandUserY = true;
        imputeOriginal = false;
        recoverSvd = false;
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
