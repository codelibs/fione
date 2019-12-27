/*
 * Copyright 2012-2019 CodeLibs Project and the Others.
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

public class GLMParametersV3 extends ModelParametersSchemaV3 {

    /**
     * Seed for pseudo random number generator (if applicable)
     */
    public long seed;

    /**
     * Family. Use binomial for classification with logistic regression, others are for regression problems.
     */
    public GLMFamily family;

    /**
     * Random Component Family array.  One for each random component. Only support gaussian for now.
     */
    @SerializedName("rand_family")
    public GLMFamily[] randFamily;

    /**
     * Tweedie variance power
     */
    @SerializedName("tweedie_variance_power")
    public double tweedieVariancePower;

    /**
     * Tweedie link power
     */
    @SerializedName("tweedie_link_power")
    public double tweedieLinkPower;

    /**
     * Theta
     */
    public double theta;

    /**
     * AUTO will set the solver based on given data and the other parameters. IRLSM is fast on on problems with small
     * number of predictors and for lambda-search with L1 penalty, L_BFGS scales better for datasets with many columns.
     */
    public GLMSolver solver;

    /**
     * Distribution of regularization between the L1 (Lasso) and L2 (Ridge) penalties. A value of 1 for alpha represents
     * Lasso regression, a value of 0 produces Ridge regression, and anything in between specifies the amount of mixing
     * between the two. Default value of alpha is 0 when SOLVER = 'L-BFGS'; 0.5 otherwise.
     */
    public double[] alpha;

    /**
     * Regularization strength
     */
    public double[] lambda;

    /**
     * Use lambda search starting at lambda max, given lambda is then interpreted as lambda min
     */
    @SerializedName("lambda_search")
    public boolean lambdaSearch;

    /**
     * Stop early when there is no more relative improvement on train or validation (if provided)
     */
    @SerializedName("early_stopping")
    public boolean earlyStopping;

    /**
     * Number of lambdas to be used in a search. Default indicates: If alpha is zero, with lambda search set to True,
     * the value of nlamdas is set to 30 (fewer lambdas are needed for ridge regression) otherwise it is set to 100.
     */
    public int nlambdas;

    /**
     * Standardize numeric columns to have zero mean and unit variance
     */
    public boolean standardize;

    /**
     * Handling of missing values. Either MeanImputation, Skip or PlugValues.
     */
    @SerializedName("missing_values_handling")
    public GLMMissingValuesHandling missingValuesHandling;

    /**
     * Plug Values (a single row frame containing values that will be used to impute missing values of the
     * training/validation frame, use with conjunction missing_values_handling = PlugValues)
     */
    @SerializedName("plug_values")
    public FrameKeyV3 plugValues;

    /**
     * Restrict coefficients (not intercept) to be non-negative
     */
    @SerializedName("non_negative")
    public boolean nonNegative;

    /**
     * Maximum number of iterations
     */
    @SerializedName("max_iterations")
    public int maxIterations;

    /**
     * Converge if  beta changes less (using L-infinity norm) than beta esilon, ONLY applies to IRLSM solver
     */
    @SerializedName("beta_epsilon")
    public double betaEpsilon;

    /**
     * Converge if  objective value changes less than this. Default indicates: If lambda_search is set to True the value
     * of objective_epsilon is set to .0001. If the lambda_search is set to False and lambda is equal to zero, the value
     * of objective_epsilon is set to .000001, for any other value of lambda the default value of objective_epsilon is
     * set to .0001.
     */
    @SerializedName("objective_epsilon")
    public double objectiveEpsilon;

    /**
     * Converge if  objective changes less (using L-infinity norm) than this, ONLY applies to L-BFGS solver. Default
     * indicates: If lambda_search is set to False and lambda is equal to zero, the default value of gradient_epsilon is
     * equal to .000001, otherwise the default value is .0001. If lambda_search is set to True, the conditional values
     * above are 1E-8 and 1E-6 respectively.
     */
    @SerializedName("gradient_epsilon")
    public double gradientEpsilon;

    /**
     * Likelihood divider in objective value computation, default is 1/nobs
     */
    @SerializedName("obj_reg")
    public double objReg;

    /**
     * Link function.
     */
    public GLMLink link;

    /**
     * Link function array for random component in HGLM.
     */
    @SerializedName("rand_link")
    public GLMLink[] randLink;

    /**
     * double array to initialize fixed and random coefficients for HGLM.
     */
    public double[] startval;

    /**
     * random columns indices for HGLM.
     */
    @SerializedName("random_columns")
    public int[] randomColumns;

    /**
     * if true, will return likelihood function value for HGLM.
     */
    @SerializedName("calc_like")
    public boolean calcLike;

    /**
     * Include constant term in the model
     */
    public boolean intercept;

    /**
     * If set to true, will return HGLM model.  Otherwise, normal GLM model will be returned
     */
    @SerializedName("HGLM")
    public boolean hglm;

    /**
     * Prior probability for y==1. To be used only for logistic regression iff the data has been sampled and the mean of
     * response does not reflect reality.
     */
    public double prior;

    /**
     * Minimum lambda used in lambda search, specified as a ratio of lambda_max (the smallest lambda that drives all
     * coefficients to zero). Default indicates: if the number of observations is greater than the number of variables,
     * then lambda_min_ratio is set to 0.0001; if the number of observations is less than the number of variables, then
     * lambda_min_ratio is set to 0.01.
     */
    @SerializedName("lambda_min_ratio")
    public double lambdaMinRatio;

    /**
     * Beta constraints
     */
    @SerializedName("beta_constraints")
    public FrameKeyV3 betaConstraints;

    /**
     * Maximum number of active predictors during computation. Use as a stopping criterion to prevent expensive model
     * building with many predictors. Default indicates: If the IRLSM solver is used, the value of max_active_predictors
     * is set to 5000 otherwise it is set to 100000000.
     */
    @SerializedName("max_active_predictors")
    public int maxActivePredictors;

    /**
     * A list of predictor column indices to interact. All pairwise combinations will be computed for the list.
     */
    public String[] interactions;

    /**
     * A list of pairwise (first order) column interactions.
     */
    @SerializedName("interaction_pairs")
    public StringPairV3[] interactionPairs;

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
     * [Deprecated] Maximum size (# classes) for confusion matrices to be printed in the Logs
     */
    @SerializedName("max_confusion_matrix_size")
    public int maxConfusionMatrixSize;

    /**
     * Maximum number (top K) of predictions to use for hit ratio computation (for multi-class only, 0 to disable)
     */
    @SerializedName("max_hit_ratio_k")
    public int maxHitRatioK;

    /**
     * Request p-values computation, p-values work only with IRLSM solver and no regularization
     */
    @SerializedName("compute_p_values")
    public boolean computePValues;

    /**
     * In case of linearly dependent columns, remove some of the dependent columns
     */
    @SerializedName("remove_collinear_columns")
    public boolean removeCollinearColumns;

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
    public GLMParametersV3() {
        seed = -1L;
        family = GLMFamily.gaussian;
        tweedieVariancePower = 0.0;
        tweedieLinkPower = 1.0;
        theta = 1e-10;
        solver = GLMSolver.AUTO;
        lambdaSearch = false;
        earlyStopping = true;
        nlambdas = -1;
        standardize = true;
        missingValuesHandling = GLMMissingValuesHandling.MeanImputation;
        nonNegative = false;
        maxIterations = -1;
        betaEpsilon = 0.0001;
        objectiveEpsilon = -1.0;
        gradientEpsilon = -1.0;
        objReg = -1.0;
        link = GLMLink.family_default;
        calcLike = false;
        intercept = true;
        hglm = false;
        prior = -1.0;
        lambdaMinRatio = -1.0;
        maxActivePredictors = -1;
        balanceClasses = false;
        maxAfterBalanceSize = 5.0f;
        maxConfusionMatrixSize = 20;
        maxHitRatioK = 0;
        computePValues = false;
        removeCollinearColumns = false;
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
        stoppingRounds = 3;
        maxRuntimeSecs = 0.0;
        stoppingMetric = ScoreKeeperStoppingMetric.deviance;
        stoppingTolerance = 0.0001;
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
