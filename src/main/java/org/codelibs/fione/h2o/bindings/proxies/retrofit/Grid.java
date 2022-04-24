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
package org.codelibs.fione.h2o.bindings.proxies.retrofit;

import org.codelibs.fione.h2o.bindings.pojos.AggregatorParametersV99;
import org.codelibs.fione.h2o.bindings.pojos.AggregatorV99;
import org.codelibs.fione.h2o.bindings.pojos.CoxPHParametersV3;
import org.codelibs.fione.h2o.bindings.pojos.CoxPHTies;
import org.codelibs.fione.h2o.bindings.pojos.CoxPHV3;
import org.codelibs.fione.h2o.bindings.pojos.DRFParametersV3;
import org.codelibs.fione.h2o.bindings.pojos.DRFV3;
import org.codelibs.fione.h2o.bindings.pojos.DataInfoTransformType;
import org.codelibs.fione.h2o.bindings.pojos.DeepLearningActivation;
import org.codelibs.fione.h2o.bindings.pojos.DeepLearningClassSamplingMethod;
import org.codelibs.fione.h2o.bindings.pojos.DeepLearningInitialWeightDistribution;
import org.codelibs.fione.h2o.bindings.pojos.DeepLearningLoss;
import org.codelibs.fione.h2o.bindings.pojos.DeepLearningMissingValuesHandling;
import org.codelibs.fione.h2o.bindings.pojos.DeepLearningParametersV3;
import org.codelibs.fione.h2o.bindings.pojos.DeepLearningV3;
import org.codelibs.fione.h2o.bindings.pojos.DeepWaterParametersActivation;
import org.codelibs.fione.h2o.bindings.pojos.DeepWaterParametersBackend;
import org.codelibs.fione.h2o.bindings.pojos.DeepWaterParametersNetwork;
import org.codelibs.fione.h2o.bindings.pojos.DeepWaterParametersProblemType;
import org.codelibs.fione.h2o.bindings.pojos.DeepWaterParametersV3;
import org.codelibs.fione.h2o.bindings.pojos.DeepWaterV3;
import org.codelibs.fione.h2o.bindings.pojos.EnsembleMetalearnerAlgorithm;
import org.codelibs.fione.h2o.bindings.pojos.GBMParametersV3;
import org.codelibs.fione.h2o.bindings.pojos.GBMV3;
import org.codelibs.fione.h2o.bindings.pojos.GLMFamily;
import org.codelibs.fione.h2o.bindings.pojos.GLMLink;
import org.codelibs.fione.h2o.bindings.pojos.GLMMissingValuesHandling;
import org.codelibs.fione.h2o.bindings.pojos.GLMParametersV3;
import org.codelibs.fione.h2o.bindings.pojos.GLMSolver;
import org.codelibs.fione.h2o.bindings.pojos.GLMV3;
import org.codelibs.fione.h2o.bindings.pojos.GLRMParametersV3;
import org.codelibs.fione.h2o.bindings.pojos.GLRMV3;
import org.codelibs.fione.h2o.bindings.pojos.GenericParametersV3;
import org.codelibs.fione.h2o.bindings.pojos.GenericV3;
import org.codelibs.fione.h2o.bindings.pojos.GenmodelalgosglrmGlrmInitialization;
import org.codelibs.fione.h2o.bindings.pojos.GenmodelalgosglrmGlrmLoss;
import org.codelibs.fione.h2o.bindings.pojos.GenmodelalgosglrmGlrmRegularizer;
import org.codelibs.fione.h2o.bindings.pojos.GenmodelalgospsvmKernelType;
import org.codelibs.fione.h2o.bindings.pojos.GenmodelutilsDistributionFamily;
import org.codelibs.fione.h2o.bindings.pojos.GridKeyV3;
import org.codelibs.fione.h2o.bindings.pojos.H2otargetencodingTargetEncoderDataLeakageHandlingStrategy;
import org.codelibs.fione.h2o.bindings.pojos.IsolationForestParametersV3;
import org.codelibs.fione.h2o.bindings.pojos.IsolationForestV3;
import org.codelibs.fione.h2o.bindings.pojos.KMeansInitialization;
import org.codelibs.fione.h2o.bindings.pojos.KMeansParametersV3;
import org.codelibs.fione.h2o.bindings.pojos.KMeansV3;
import org.codelibs.fione.h2o.bindings.pojos.KeyV3;
import org.codelibs.fione.h2o.bindings.pojos.KeyValueV3;
import org.codelibs.fione.h2o.bindings.pojos.ModelParametersCategoricalEncodingScheme;
import org.codelibs.fione.h2o.bindings.pojos.ModelParametersFoldAssignmentScheme;
import org.codelibs.fione.h2o.bindings.pojos.NaiveBayesParametersV3;
import org.codelibs.fione.h2o.bindings.pojos.NaiveBayesV3;
import org.codelibs.fione.h2o.bindings.pojos.PCAImplementation;
import org.codelibs.fione.h2o.bindings.pojos.PCAMethod;
import org.codelibs.fione.h2o.bindings.pojos.PCAParametersV3;
import org.codelibs.fione.h2o.bindings.pojos.PCAV3;
import org.codelibs.fione.h2o.bindings.pojos.PSVMParametersV3;
import org.codelibs.fione.h2o.bindings.pojos.PSVMV3;
import org.codelibs.fione.h2o.bindings.pojos.SVDMethod;
import org.codelibs.fione.h2o.bindings.pojos.SVDParametersV99;
import org.codelibs.fione.h2o.bindings.pojos.SVDV99;
import org.codelibs.fione.h2o.bindings.pojos.ScoreKeeperStoppingMetric;
import org.codelibs.fione.h2o.bindings.pojos.StackedEnsembleParametersV99;
import org.codelibs.fione.h2o.bindings.pojos.StackedEnsembleV99;
import org.codelibs.fione.h2o.bindings.pojos.StringPairV3;
import org.codelibs.fione.h2o.bindings.pojos.TargetEncoderParametersV3;
import org.codelibs.fione.h2o.bindings.pojos.TargetEncoderV3;
import org.codelibs.fione.h2o.bindings.pojos.TreeSharedTreeModelSharedTreeParametersHistogramType;
import org.codelibs.fione.h2o.bindings.pojos.TreexgboostXGBoostModelXGBoostParametersBackend;
import org.codelibs.fione.h2o.bindings.pojos.TreexgboostXGBoostModelXGBoostParametersBooster;
import org.codelibs.fione.h2o.bindings.pojos.TreexgboostXGBoostModelXGBoostParametersDMatrixType;
import org.codelibs.fione.h2o.bindings.pojos.TreexgboostXGBoostModelXGBoostParametersDartNormalizeType;
import org.codelibs.fione.h2o.bindings.pojos.TreexgboostXGBoostModelXGBoostParametersDartSampleType;
import org.codelibs.fione.h2o.bindings.pojos.TreexgboostXGBoostModelXGBoostParametersGrowPolicy;
import org.codelibs.fione.h2o.bindings.pojos.TreexgboostXGBoostModelXGBoostParametersTreeMethod;
import org.codelibs.fione.h2o.bindings.pojos.Word2VecNormModel;
import org.codelibs.fione.h2o.bindings.pojos.Word2VecParametersV3;
import org.codelibs.fione.h2o.bindings.pojos.Word2VecV3;
import org.codelibs.fione.h2o.bindings.pojos.Word2VecWordModel;
import org.codelibs.fione.h2o.bindings.pojos.XGBoostParametersV3;
import org.codelibs.fione.h2o.bindings.pojos.XGBoostV3;

import retrofit2.Call;
import retrofit2.http.Field;
import retrofit2.http.FormUrlEncoded;
import retrofit2.http.POST;
import retrofit2.http.Path;

public interface Grid {

    /**
     * Run grid search for XGBoost model.
     *   @param ntrees (same as n_estimators) Number of trees.
     *   @param n_estimators (same as ntrees) Number of trees.
     *   @param max_depth Maximum tree depth.
     *   @param min_rows (same as min_child_weight) Fewest allowed (weighted) observations in a leaf.
     *   @param min_child_weight (same as min_rows) Fewest allowed (weighted) observations in a leaf.
     *   @param learn_rate (same as eta) Learning rate (from 0.0 to 1.0)
     *   @param eta (same as learn_rate) Learning rate (from 0.0 to 1.0)
     *   @param sample_rate (same as subsample) Row sample rate per tree (from 0.0 to 1.0)
     *   @param subsample (same as sample_rate) Row sample rate per tree (from 0.0 to 1.0)
     *   @param col_sample_rate (same as colsample_bylevel) Column sample rate (from 0.0 to 1.0)
     *   @param colsample_bylevel (same as col_sample_rate) Column sample rate (from 0.0 to 1.0)
     *   @param col_sample_rate_per_tree (same as colsample_bytree) Column sample rate per tree (from 0.0 to 1.0)
     *   @param colsample_bytree (same as col_sample_rate_per_tree) Column sample rate per tree (from 0.0 to 1.0)
     *   @param monotone_constraints A mapping representing monotonic constraints. Use +1 to enforce an increasing
     *                               constraint and -1 to specify a decreasing constraint.
     *   @param max_abs_leafnode_pred (same as max_delta_step) Maximum absolute value of a leaf node prediction
     *   @param max_delta_step (same as max_abs_leafnode_pred) Maximum absolute value of a leaf node prediction
     *   @param score_tree_interval Score the model after every so many trees. Disabled if set to 0.
     *   @param seed Seed for pseudo random number generator (if applicable)
     *   @param min_split_improvement (same as gamma) Minimum relative improvement in squared error reduction for a split
     *                                to happen
     *   @param gamma (same as min_split_improvement) Minimum relative improvement in squared error reduction for a split
     *                to happen
     *   @param nthread Number of parallel threads that can be used to run XGBoost. Cannot exceed H2O cluster limits
     *                  (-nthreads parameter). Defaults to maximum available
     *   @param save_matrix_directory Directory where to save matrices passed to XGBoost library. Useful for debugging.
     *   @param calibrate_model Use Platt Scaling to calculate calibrated class probabilities. Calibration can provide
     *                          more accurate estimates of class probabilities.
     *   @param calibration_frame Calibration frame for Platt Scaling
     *   @param max_bins For tree_method=hist only: maximum number of bins
     *   @param max_leaves For tree_method=hist only: maximum number of leaves
     *   @param min_sum_hessian_in_leaf For tree_method=hist only: the mininum sum of hessian in a leaf to keep splitting
     *   @param min_data_in_leaf For tree_method=hist only: the mininum data in a leaf to keep splitting
     *   @param tree_method Tree method
     *   @param grow_policy Grow policy - depthwise is standard GBM, lossguide is LightGBM
     *   @param booster Booster type
     *   @param reg_lambda L2 regularization
     *   @param reg_alpha L1 regularization
     *   @param quiet_mode Enable quiet mode
     *   @param sample_type For booster=dart only: sample_type
     *   @param normalize_type For booster=dart only: normalize_type
     *   @param rate_drop For booster=dart only: rate_drop (0..1)
     *   @param one_drop For booster=dart only: one_drop
     *   @param skip_drop For booster=dart only: skip_drop (0..1)
     *   @param dmatrix_type Type of DMatrix. For sparse, NAs and 0 are treated equally.
     *   @param backend Backend. By default (auto), a GPU is used if available.
     *   @param gpu_id Which GPU to use.
     *   @param model_id Destination id for this model; auto-generated if not specified.
     *   @param training_frame Id of the training data frame.
     *   @param validation_frame Id of the validation data frame.
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or &gt;= 2).
     *   @param keep_cross_validation_models Whether to keep the cross-validation models.
     *   @param keep_cross_validation_predictions Whether to keep the predictions of the cross-validation models.
     *   @param keep_cross_validation_fold_assignment Whether to keep the cross-validation fold assignment.
     *   @param parallelize_cross_validation Allow parallel training of cross-validation models
     *   @param distribution Distribution function
     *   @param tweedie_power Tweedie power for Tweedie regression, must be between 1 and 2.
     *   @param quantile_alpha Desired quantile for Quantile regression, must be between 0 and 1.
     *   @param huber_alpha Desired quantile for Huber/M-regression (threshold between quadratic and linear loss, must be
     *                      between 0 and 1).
     *   @param response_column Response variable column.
     *   @param weights_column Column with observation weights. Giving some observation a weight of zero is equivalent to
     *                         excluding it from the dataset; giving an observation a relative weight of 2 is equivalent
     *                         to repeating that row twice. Negative weights are not allowed. Note: Weights are per-row
     *                         observation weights and do not increase the size of the data frame. This is typically the
     *                         number of times a row is repeated, but non-integer values are supported as well. During
     *                         training, rows with higher weights matter more, due to the larger loss function pre-factor.
     *   @param offset_column Offset column. This will be added to the combination of columns before applying the link
     *                        function.
     *   @param fold_column Column with cross-validation fold index assignment per observation.
     *   @param fold_assignment Cross-validation fold assignment scheme, if fold_column is not specified. The 'Stratified'
     *                          option will stratify the folds based on the response variable, for classification
     *                          problems.
     *   @param categorical_encoding Encoding scheme for categorical features
     *   @param max_categorical_levels For every categorical feature, only use this many most frequent categorical levels
     *                                 for model training. Only used for categorical_encoding == EnumLimited.
     *   @param ignored_columns Names of columns to ignore for training.
     *   @param ignore_const_cols Ignore constant columns.
     *   @param score_each_iteration Whether to score during each iteration of model training.
     *   @param checkpoint Model checkpoint to resume training with.
     *   @param stopping_rounds Early stopping based on convergence of stopping_metric. Stop if simple moving average of
     *                          length k of the stopping_metric does not improve for k:=stopping_rounds scoring events (0
     *                          to disable)
     *   @param max_runtime_secs Maximum allowed runtime in seconds for model training. Use 0 to disable.
     *   @param stopping_metric Metric to use for early stopping (AUTO: logloss for classification, deviance for
     *                          regression and anonomaly_score for Isolation Forest). Note that custom and
     *                          custom_increasing can only be used in GBM and DRF with the Python client.
     *   @param stopping_tolerance Relative tolerance for metric-based stopping criterion (stop if relative improvement is
     *                             not at least this much)
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     */
    @FormUrlEncoded
    @POST("/99/Grid/xgboost")
    Call<XGBoostV3> trainXgboost(@Field("ntrees") int ntrees, @Field("n_estimators") int n_estimators, @Field("max_depth") int max_depth,
            @Field("min_rows") double min_rows, @Field("min_child_weight") double min_child_weight, @Field("learn_rate") double learn_rate,
            @Field("eta") double eta, @Field("sample_rate") double sample_rate, @Field("subsample") double subsample,
            @Field("col_sample_rate") double col_sample_rate, @Field("colsample_bylevel") double colsample_bylevel,
            @Field("col_sample_rate_per_tree") double col_sample_rate_per_tree, @Field("colsample_bytree") double colsample_bytree,
            @Field("monotone_constraints") KeyValueV3[] monotone_constraints, @Field("max_abs_leafnode_pred") float max_abs_leafnode_pred,
            @Field("max_delta_step") float max_delta_step, @Field("score_tree_interval") int score_tree_interval, @Field("seed") long seed,
            @Field("min_split_improvement") float min_split_improvement, @Field("gamma") float gamma, @Field("nthread") int nthread,
            @Field("save_matrix_directory") String save_matrix_directory, @Field("calibrate_model") boolean calibrate_model,
            @Field("calibration_frame") String calibration_frame, @Field("max_bins") int max_bins, @Field("max_leaves") int max_leaves,
            @Field("min_sum_hessian_in_leaf") float min_sum_hessian_in_leaf, @Field("min_data_in_leaf") float min_data_in_leaf,
            @Field("tree_method") TreexgboostXGBoostModelXGBoostParametersTreeMethod tree_method,
            @Field("grow_policy") TreexgboostXGBoostModelXGBoostParametersGrowPolicy grow_policy,
            @Field("booster") TreexgboostXGBoostModelXGBoostParametersBooster booster, @Field("reg_lambda") float reg_lambda,
            @Field("reg_alpha") float reg_alpha, @Field("quiet_mode") boolean quiet_mode,
            @Field("sample_type") TreexgboostXGBoostModelXGBoostParametersDartSampleType sample_type,
            @Field("normalize_type") TreexgboostXGBoostModelXGBoostParametersDartNormalizeType normalize_type,
            @Field("rate_drop") float rate_drop, @Field("one_drop") boolean one_drop, @Field("skip_drop") float skip_drop,
            @Field("dmatrix_type") TreexgboostXGBoostModelXGBoostParametersDMatrixType dmatrix_type,
            @Field("backend") TreexgboostXGBoostModelXGBoostParametersBackend backend, @Field("gpu_id") int gpu_id,
            @Field("model_id") String model_id, @Field("training_frame") String training_frame,
            @Field("validation_frame") String validation_frame, @Field("nfolds") int nfolds,
            @Field("keep_cross_validation_models") boolean keep_cross_validation_models,
            @Field("keep_cross_validation_predictions") boolean keep_cross_validation_predictions,
            @Field("keep_cross_validation_fold_assignment") boolean keep_cross_validation_fold_assignment,
            @Field("parallelize_cross_validation") boolean parallelize_cross_validation,
            @Field("distribution") GenmodelutilsDistributionFamily distribution, @Field("tweedie_power") double tweedie_power,
            @Field("quantile_alpha") double quantile_alpha, @Field("huber_alpha") double huber_alpha,
            @Field("response_column") String response_column, @Field("weights_column") String weights_column,
            @Field("offset_column") String offset_column, @Field("fold_column") String fold_column,
            @Field("fold_assignment") ModelParametersFoldAssignmentScheme fold_assignment,
            @Field("categorical_encoding") ModelParametersCategoricalEncodingScheme categorical_encoding,
            @Field("max_categorical_levels") int max_categorical_levels, @Field("ignored_columns") String[] ignored_columns,
            @Field("ignore_const_cols") boolean ignore_const_cols, @Field("score_each_iteration") boolean score_each_iteration,
            @Field("checkpoint") String checkpoint, @Field("stopping_rounds") int stopping_rounds,
            @Field("max_runtime_secs") double max_runtime_secs, @Field("stopping_metric") ScoreKeeperStoppingMetric stopping_metric,
            @Field("stopping_tolerance") double stopping_tolerance, @Field("custom_metric_func") String custom_metric_func,
            @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir);

    @FormUrlEncoded
    @POST("/99/Grid/xgboost")
    Call<XGBoostV3> trainXgboost();

    /**
     * Run grid search for TargetEncoderBuilder model.
     *   @param blending Blending enabled/disabled
     *   @param k Inflection point. Used for blending (if enabled). Blending is to be enabled separately using the
     *            'blending' parameter.
     *   @param f Smoothing. Used for blending (if enabled). Blending is to be enabled separately using the 'blending'
     *            parameter.
     *   @param data_leakage_handling Data leakage handling strategy.
     *   @param noise_level Noise level
     *   @param seed Seed for the specified noise level
     *   @param model_id Destination id for this model; auto-generated if not specified.
     *   @param training_frame Id of the training data frame.
     *   @param validation_frame Id of the validation data frame.
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or &gt;= 2).
     *   @param keep_cross_validation_models Whether to keep the cross-validation models.
     *   @param keep_cross_validation_predictions Whether to keep the predictions of the cross-validation models.
     *   @param keep_cross_validation_fold_assignment Whether to keep the cross-validation fold assignment.
     *   @param parallelize_cross_validation Allow parallel training of cross-validation models
     *   @param distribution Distribution function
     *   @param tweedie_power Tweedie power for Tweedie regression, must be between 1 and 2.
     *   @param quantile_alpha Desired quantile for Quantile regression, must be between 0 and 1.
     *   @param huber_alpha Desired quantile for Huber/M-regression (threshold between quadratic and linear loss, must be
     *                      between 0 and 1).
     *   @param response_column Response variable column.
     *   @param weights_column Column with observation weights. Giving some observation a weight of zero is equivalent to
     *                         excluding it from the dataset; giving an observation a relative weight of 2 is equivalent
     *                         to repeating that row twice. Negative weights are not allowed. Note: Weights are per-row
     *                         observation weights and do not increase the size of the data frame. This is typically the
     *                         number of times a row is repeated, but non-integer values are supported as well. During
     *                         training, rows with higher weights matter more, due to the larger loss function pre-factor.
     *   @param offset_column Offset column. This will be added to the combination of columns before applying the link
     *                        function.
     *   @param fold_column Column with cross-validation fold index assignment per observation.
     *   @param fold_assignment Cross-validation fold assignment scheme, if fold_column is not specified. The 'Stratified'
     *                          option will stratify the folds based on the response variable, for classification
     *                          problems.
     *   @param categorical_encoding Encoding scheme for categorical features
     *   @param max_categorical_levels For every categorical feature, only use this many most frequent categorical levels
     *                                 for model training. Only used for categorical_encoding == EnumLimited.
     *   @param ignored_columns Names of columns to ignore for training.
     *   @param ignore_const_cols Ignore constant columns.
     *   @param score_each_iteration Whether to score during each iteration of model training.
     *   @param checkpoint Model checkpoint to resume training with.
     *   @param stopping_rounds Early stopping based on convergence of stopping_metric. Stop if simple moving average of
     *                          length k of the stopping_metric does not improve for k:=stopping_rounds scoring events (0
     *                          to disable)
     *   @param max_runtime_secs Maximum allowed runtime in seconds for model training. Use 0 to disable.
     *   @param stopping_metric Metric to use for early stopping (AUTO: logloss for classification, deviance for
     *                          regression and anonomaly_score for Isolation Forest). Note that custom and
     *                          custom_increasing can only be used in GBM and DRF with the Python client.
     *   @param stopping_tolerance Relative tolerance for metric-based stopping criterion (stop if relative improvement is
     *                             not at least this much)
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     */
    @FormUrlEncoded
    @POST("/99/Grid/targetencoder")
    Call<TargetEncoderV3> trainTargetencoder(@Field("blending") boolean blending, @Field("k") double k, @Field("f") double f,
            @Field("data_leakage_handling") H2otargetencodingTargetEncoderDataLeakageHandlingStrategy data_leakage_handling,
            @Field("noise_level") double noise_level, @Field("seed") long seed, @Field("model_id") String model_id,
            @Field("training_frame") String training_frame, @Field("validation_frame") String validation_frame, @Field("nfolds") int nfolds,
            @Field("keep_cross_validation_models") boolean keep_cross_validation_models,
            @Field("keep_cross_validation_predictions") boolean keep_cross_validation_predictions,
            @Field("keep_cross_validation_fold_assignment") boolean keep_cross_validation_fold_assignment,
            @Field("parallelize_cross_validation") boolean parallelize_cross_validation,
            @Field("distribution") GenmodelutilsDistributionFamily distribution, @Field("tweedie_power") double tweedie_power,
            @Field("quantile_alpha") double quantile_alpha, @Field("huber_alpha") double huber_alpha,
            @Field("response_column") String response_column, @Field("weights_column") String weights_column,
            @Field("offset_column") String offset_column, @Field("fold_column") String fold_column,
            @Field("fold_assignment") ModelParametersFoldAssignmentScheme fold_assignment,
            @Field("categorical_encoding") ModelParametersCategoricalEncodingScheme categorical_encoding,
            @Field("max_categorical_levels") int max_categorical_levels, @Field("ignored_columns") String[] ignored_columns,
            @Field("ignore_const_cols") boolean ignore_const_cols, @Field("score_each_iteration") boolean score_each_iteration,
            @Field("checkpoint") String checkpoint, @Field("stopping_rounds") int stopping_rounds,
            @Field("max_runtime_secs") double max_runtime_secs, @Field("stopping_metric") ScoreKeeperStoppingMetric stopping_metric,
            @Field("stopping_tolerance") double stopping_tolerance, @Field("custom_metric_func") String custom_metric_func,
            @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir);

    @FormUrlEncoded
    @POST("/99/Grid/targetencoder")
    Call<TargetEncoderV3> trainTargetencoder();

    /**
     * Run grid search for DeepLearning model.
     *   @param balance_classes Balance training data class counts via over/under-sampling (for imbalanced data).
     *   @param class_sampling_factors Desired over/under-sampling ratios per class (in lexicographic order). If not
     *                                 specified, sampling factors will be automatically computed to obtain class balance
     *                                 during training. Requires balance_classes.
     *   @param max_after_balance_size Maximum relative size of the training data after balancing class counts (can be
     *                                 less than 1.0). Requires balance_classes.
     *   @param max_confusion_matrix_size [Deprecated] Maximum size (# classes) for confusion matrices to be printed in
     *                                    the Logs.
     *   @param max_hit_ratio_k Max. number (top K) of predictions to use for hit ratio computation (for multi-class only,
     *                          0 to disable).
     *   @param activation Activation function.
     *   @param hidden Hidden layer sizes (e.g. [100, 100]).
     *   @param epochs How many times the dataset should be iterated (streamed), can be fractional.
     *   @param train_samples_per_iteration Number of training samples (globally) per MapReduce iteration. Special values
     *                                      are 0: one epoch, -1: all available data (e.g., replicated training data), -2:
     *                                      automatic.
     *   @param target_ratio_comm_to_comp Target ratio of communication overhead to computation. Only for multi-node
     *                                    operation and train_samples_per_iteration = -2 (auto-tuning).
     *   @param seed Seed for random numbers (affects sampling) - Note: only reproducible when running single threaded.
     *   @param adaptive_rate Adaptive learning rate.
     *   @param rho Adaptive learning rate time decay factor (similarity to prior updates).
     *   @param epsilon Adaptive learning rate smoothing factor (to avoid divisions by zero and allow progress).
     *   @param rate Learning rate (higher =&gt; less stable, lower =&gt; slower convergence).
     *   @param rate_annealing Learning rate annealing: rate / (1 + rate_annealing * samples).
     *   @param rate_decay Learning rate decay factor between layers (N-th layer: rate * rate_decay ^ (n - 1).
     *   @param momentum_start Initial momentum at the beginning of training (try 0.5).
     *   @param momentum_ramp Number of training samples for which momentum increases.
     *   @param momentum_stable Final momentum after the ramp is over (try 0.99).
     *   @param nesterov_accelerated_gradient Use Nesterov accelerated gradient (recommended).
     *   @param input_dropout_ratio Input layer dropout ratio (can improve generalization, try 0.1 or 0.2).
     *   @param hidden_dropout_ratios Hidden layer dropout ratios (can improve generalization), specify one value per
     *                                hidden layer, defaults to 0.5.
     *   @param l1 L1 regularization (can add stability and improve generalization, causes many weights to become 0).
     *   @param l2 L2 regularization (can add stability and improve generalization, causes many weights to be small.
     *   @param max_w2 Constraint for squared sum of incoming weights per unit (e.g. for Rectifier).
     *   @param initial_weight_distribution Initial weight distribution.
     *   @param initial_weight_scale Uniform: -value...value, Normal: stddev.
     *   @param initial_weights A list of H2OFrame ids to initialize the weight matrices of this model with.
     *   @param initial_biases A list of H2OFrame ids to initialize the bias vectors of this model with.
     *   @param loss Loss function.
     *   @param score_interval Shortest time interval (in seconds) between model scoring.
     *   @param score_training_samples Number of training set samples for scoring (0 for all).
     *   @param score_validation_samples Number of validation set samples for scoring (0 for all).
     *   @param score_duty_cycle Maximum duty cycle fraction for scoring (lower: more training, higher: more scoring).
     *   @param classification_stop Stopping criterion for classification error fraction on training data (-1 to disable).
     *   @param regression_stop Stopping criterion for regression error (MSE) on training data (-1 to disable).
     *   @param quiet_mode Enable quiet mode for less output to standard output.
     *   @param score_validation_sampling Method used to sample validation dataset for scoring.
     *   @param overwrite_with_best_model If enabled, override the final model with the best model found during training.
     *   @param autoencoder Auto-Encoder.
     *   @param use_all_factor_levels Use all factor levels of categorical variables. Otherwise, the first factor level is
     *                                omitted (without loss of accuracy). Useful for variable importances and auto-enabled
     *                                for autoencoder.
     *   @param standardize If enabled, automatically standardize the data. If disabled, the user must provide properly
     *                      scaled input data.
     *   @param diagnostics Enable diagnostics for hidden layers.
     *   @param variable_importances Compute variable importances for input features (Gedeon method) - can be slow for
     *                               large networks.
     *   @param fast_mode Enable fast mode (minor approximation in back-propagation).
     *   @param force_load_balance Force extra load balancing to increase training speed for small datasets (to keep all
     *                             cores busy).
     *   @param replicate_training_data Replicate the entire training dataset onto every node for faster training on small
     *                                  datasets.
     *   @param single_node_mode Run on a single node for fine-tuning of model parameters.
     *   @param shuffle_training_data Enable shuffling of training data (recommended if training data is replicated and
     *                                train_samples_per_iteration is close to #nodes x #rows, of if using
     *                                balance_classes).
     *   @param missing_values_handling Handling of missing values. Either MeanImputation or Skip.
     *   @param sparse Sparse data handling (more efficient for data with lots of 0 values).
     *   @param col_major #DEPRECATED Use a column major weight matrix for input layer. Can speed up forward propagation,
     *                    but might slow down backpropagation.
     *   @param average_activation Average activation for sparse auto-encoder. #Experimental
     *   @param sparsity_beta Sparsity regularization. #Experimental
     *   @param max_categorical_features Max. number of categorical features, enforced via hashing. #Experimental
     *   @param reproducible Force reproducibility on small data (will be slow - only uses 1 thread).
     *   @param export_weights_and_biases Whether to export Neural Network weights and biases to H2O Frames.
     *   @param mini_batch_size Mini-batch size (smaller leads to better fit, larger can speed up and generalize better).
     *   @param elastic_averaging Elastic averaging between compute nodes can improve distributed model convergence.
     *                            #Experimental
     *   @param elastic_averaging_moving_rate Elastic averaging moving rate (only if elastic averaging is enabled).
     *   @param elastic_averaging_regularization Elastic averaging regularization strength (only if elastic averaging is
     *                                           enabled).
     *   @param pretrained_autoencoder Pretrained autoencoder model to initialize this model with.
     *   @param model_id Destination id for this model; auto-generated if not specified.
     *   @param training_frame Id of the training data frame.
     *   @param validation_frame Id of the validation data frame.
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or &gt;= 2).
     *   @param keep_cross_validation_models Whether to keep the cross-validation models.
     *   @param keep_cross_validation_predictions Whether to keep the predictions of the cross-validation models.
     *   @param keep_cross_validation_fold_assignment Whether to keep the cross-validation fold assignment.
     *   @param parallelize_cross_validation Allow parallel training of cross-validation models
     *   @param distribution Distribution function
     *   @param tweedie_power Tweedie power for Tweedie regression, must be between 1 and 2.
     *   @param quantile_alpha Desired quantile for Quantile regression, must be between 0 and 1.
     *   @param huber_alpha Desired quantile for Huber/M-regression (threshold between quadratic and linear loss, must be
     *                      between 0 and 1).
     *   @param response_column Response variable column.
     *   @param weights_column Column with observation weights. Giving some observation a weight of zero is equivalent to
     *                         excluding it from the dataset; giving an observation a relative weight of 2 is equivalent
     *                         to repeating that row twice. Negative weights are not allowed. Note: Weights are per-row
     *                         observation weights and do not increase the size of the data frame. This is typically the
     *                         number of times a row is repeated, but non-integer values are supported as well. During
     *                         training, rows with higher weights matter more, due to the larger loss function pre-factor.
     *   @param offset_column Offset column. This will be added to the combination of columns before applying the link
     *                        function.
     *   @param fold_column Column with cross-validation fold index assignment per observation.
     *   @param fold_assignment Cross-validation fold assignment scheme, if fold_column is not specified. The 'Stratified'
     *                          option will stratify the folds based on the response variable, for classification
     *                          problems.
     *   @param categorical_encoding Encoding scheme for categorical features
     *   @param max_categorical_levels For every categorical feature, only use this many most frequent categorical levels
     *                                 for model training. Only used for categorical_encoding == EnumLimited.
     *   @param ignored_columns Names of columns to ignore for training.
     *   @param ignore_const_cols Ignore constant columns.
     *   @param score_each_iteration Whether to score during each iteration of model training.
     *   @param checkpoint Model checkpoint to resume training with.
     *   @param stopping_rounds Early stopping based on convergence of stopping_metric. Stop if simple moving average of
     *                          length k of the stopping_metric does not improve for k:=stopping_rounds scoring events (0
     *                          to disable)
     *   @param max_runtime_secs Maximum allowed runtime in seconds for model training. Use 0 to disable.
     *   @param stopping_metric Metric to use for early stopping (AUTO: logloss for classification, deviance for
     *                          regression and anonomaly_score for Isolation Forest). Note that custom and
     *                          custom_increasing can only be used in GBM and DRF with the Python client.
     *   @param stopping_tolerance Relative tolerance for metric-based stopping criterion (stop if relative improvement is
     *                             not at least this much)
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     */
    @FormUrlEncoded
    @POST("/99/Grid/deeplearning")
    Call<DeepLearningV3> trainDeeplearning(@Field("balance_classes") boolean balance_classes,
            @Field("class_sampling_factors") float[] class_sampling_factors, @Field("max_after_balance_size") float max_after_balance_size,
            @Field("max_confusion_matrix_size") int max_confusion_matrix_size, @Field("max_hit_ratio_k") int max_hit_ratio_k,
            @Field("activation") DeepLearningActivation activation, @Field("hidden") int[] hidden, @Field("epochs") double epochs,
            @Field("train_samples_per_iteration") long train_samples_per_iteration,
            @Field("target_ratio_comm_to_comp") double target_ratio_comm_to_comp, @Field("seed") long seed,
            @Field("adaptive_rate") boolean adaptive_rate, @Field("rho") double rho, @Field("epsilon") double epsilon,
            @Field("rate") double rate, @Field("rate_annealing") double rate_annealing, @Field("rate_decay") double rate_decay,
            @Field("momentum_start") double momentum_start, @Field("momentum_ramp") double momentum_ramp,
            @Field("momentum_stable") double momentum_stable, @Field("nesterov_accelerated_gradient") boolean nesterov_accelerated_gradient,
            @Field("input_dropout_ratio") double input_dropout_ratio, @Field("hidden_dropout_ratios") double[] hidden_dropout_ratios,
            @Field("l1") double l1, @Field("l2") double l2, @Field("max_w2") float max_w2,
            @Field("initial_weight_distribution") DeepLearningInitialWeightDistribution initial_weight_distribution,
            @Field("initial_weight_scale") double initial_weight_scale, @Field("initial_weights") String[] initial_weights,
            @Field("initial_biases") String[] initial_biases, @Field("loss") DeepLearningLoss loss,
            @Field("score_interval") double score_interval, @Field("score_training_samples") long score_training_samples,
            @Field("score_validation_samples") long score_validation_samples, @Field("score_duty_cycle") double score_duty_cycle,
            @Field("classification_stop") double classification_stop, @Field("regression_stop") double regression_stop,
            @Field("quiet_mode") boolean quiet_mode,
            @Field("score_validation_sampling") DeepLearningClassSamplingMethod score_validation_sampling,
            @Field("overwrite_with_best_model") boolean overwrite_with_best_model, @Field("autoencoder") boolean autoencoder,
            @Field("use_all_factor_levels") boolean use_all_factor_levels, @Field("standardize") boolean standardize,
            @Field("diagnostics") boolean diagnostics, @Field("variable_importances") boolean variable_importances,
            @Field("fast_mode") boolean fast_mode, @Field("force_load_balance") boolean force_load_balance,
            @Field("replicate_training_data") boolean replicate_training_data, @Field("single_node_mode") boolean single_node_mode,
            @Field("shuffle_training_data") boolean shuffle_training_data,
            @Field("missing_values_handling") DeepLearningMissingValuesHandling missing_values_handling, @Field("sparse") boolean sparse,
            @Field("col_major") boolean col_major, @Field("average_activation") double average_activation,
            @Field("sparsity_beta") double sparsity_beta, @Field("max_categorical_features") int max_categorical_features,
            @Field("reproducible") boolean reproducible, @Field("export_weights_and_biases") boolean export_weights_and_biases,
            @Field("mini_batch_size") int mini_batch_size, @Field("elastic_averaging") boolean elastic_averaging,
            @Field("elastic_averaging_moving_rate") double elastic_averaging_moving_rate,
            @Field("elastic_averaging_regularization") double elastic_averaging_regularization,
            @Field("pretrained_autoencoder") String pretrained_autoencoder, @Field("model_id") String model_id,
            @Field("training_frame") String training_frame, @Field("validation_frame") String validation_frame, @Field("nfolds") int nfolds,
            @Field("keep_cross_validation_models") boolean keep_cross_validation_models,
            @Field("keep_cross_validation_predictions") boolean keep_cross_validation_predictions,
            @Field("keep_cross_validation_fold_assignment") boolean keep_cross_validation_fold_assignment,
            @Field("parallelize_cross_validation") boolean parallelize_cross_validation,
            @Field("distribution") GenmodelutilsDistributionFamily distribution, @Field("tweedie_power") double tweedie_power,
            @Field("quantile_alpha") double quantile_alpha, @Field("huber_alpha") double huber_alpha,
            @Field("response_column") String response_column, @Field("weights_column") String weights_column,
            @Field("offset_column") String offset_column, @Field("fold_column") String fold_column,
            @Field("fold_assignment") ModelParametersFoldAssignmentScheme fold_assignment,
            @Field("categorical_encoding") ModelParametersCategoricalEncodingScheme categorical_encoding,
            @Field("max_categorical_levels") int max_categorical_levels, @Field("ignored_columns") String[] ignored_columns,
            @Field("ignore_const_cols") boolean ignore_const_cols, @Field("score_each_iteration") boolean score_each_iteration,
            @Field("checkpoint") String checkpoint, @Field("stopping_rounds") int stopping_rounds,
            @Field("max_runtime_secs") double max_runtime_secs, @Field("stopping_metric") ScoreKeeperStoppingMetric stopping_metric,
            @Field("stopping_tolerance") double stopping_tolerance, @Field("custom_metric_func") String custom_metric_func,
            @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir);

    @FormUrlEncoded
    @POST("/99/Grid/deeplearning")
    Call<DeepLearningV3> trainDeeplearning();

    /**
     * Run grid search for GLM model.
     *   @param seed Seed for pseudo random number generator (if applicable)
     *   @param family Family. Use binomial for classification with logistic regression, others are for regression
     *                 problems.
     *   @param rand_family Random Component Family array.  One for each random component. Only support gaussian for now.
     *   @param tweedie_variance_power Tweedie variance power
     *   @param tweedie_link_power Tweedie link power
     *   @param theta Theta
     *   @param solver AUTO will set the solver based on given data and the other parameters. IRLSM is fast on on problems
     *                 with small number of predictors and for lambda-search with L1 penalty, L_BFGS scales better for
     *                 datasets with many columns.
     *   @param alpha Distribution of regularization between the L1 (Lasso) and L2 (Ridge) penalties. A value of 1 for
     *                alpha represents Lasso regression, a value of 0 produces Ridge regression, and anything in between
     *                specifies the amount of mixing between the two. Default value of alpha is 0 when SOLVER = 'L-BFGS';
     *                0.5 otherwise.
     *   @param lambda Regularization strength
     *   @param lambda_search Use lambda search starting at lambda max, given lambda is then interpreted as lambda min
     *   @param early_stopping Stop early when there is no more relative improvement on train or validation (if provided)
     *   @param nlambdas Number of lambdas to be used in a search. Default indicates: If alpha is zero, with lambda search
     *                   set to True, the value of nlamdas is set to 30 (fewer lambdas are needed for ridge regression)
     *                   otherwise it is set to 100.
     *   @param standardize Standardize numeric columns to have zero mean and unit variance
     *   @param missing_values_handling Handling of missing values. Either MeanImputation, Skip or PlugValues.
     *   @param plug_values Plug Values (a single row frame containing values that will be used to impute missing values
     *                      of the training/validation frame, use with conjunction missing_values_handling = PlugValues)
     *   @param non_negative Restrict coefficients (not intercept) to be non-negative
     *   @param max_iterations Maximum number of iterations
     *   @param beta_epsilon Converge if  beta changes less (using L-infinity norm) than beta esilon, ONLY applies to
     *                       IRLSM solver
     *   @param objective_epsilon Converge if  objective value changes less than this. Default indicates: If lambda_search
     *                            is set to True the value of objective_epsilon is set to .0001. If the lambda_search is
     *                            set to False and lambda is equal to zero, the value of objective_epsilon is set to
     *                            .000001, for any other value of lambda the default value of objective_epsilon is set to
     *                            .0001.
     *   @param gradient_epsilon Converge if  objective changes less (using L-infinity norm) than this, ONLY applies to
     *                           L-BFGS solver. Default indicates: If lambda_search is set to False and lambda is equal to
     *                           zero, the default value of gradient_epsilon is equal to .000001, otherwise the default
     *                           value is .0001. If lambda_search is set to True, the conditional values above are 1E-8
     *                           and 1E-6 respectively.
     *   @param obj_reg Likelihood divider in objective value computation, default is 1/nobs
     *   @param link Link function.
     *   @param rand_link Link function array for random component in HGLM.
     *   @param startval double array to initialize fixed and random coefficients for HGLM.
     *   @param random_columns random columns indices for HGLM.
     *   @param calc_like if true, will return likelihood function value for HGLM.
     *   @param intercept Include constant term in the model
     *   @param HGLM If set to true, will return HGLM model.  Otherwise, normal GLM model will be returned
     *   @param prior Prior probability for y==1. To be used only for logistic regression iff the data has been sampled
     *                and the mean of response does not reflect reality.
     *   @param lambda_min_ratio Minimum lambda used in lambda search, specified as a ratio of lambda_max (the smallest
     *                           lambda that drives all coefficients to zero). Default indicates: if the number of
     *                           observations is greater than the number of variables, then lambda_min_ratio is set to
     *                           0.0001; if the number of observations is less than the number of variables, then
     *                           lambda_min_ratio is set to 0.01.
     *   @param beta_constraints Beta constraints
     *   @param max_active_predictors Maximum number of active predictors during computation. Use as a stopping criterion
     *                                to prevent expensive model building with many predictors. Default indicates: If the
     *                                IRLSM solver is used, the value of max_active_predictors is set to 5000 otherwise it
     *                                is set to 100000000.
     *   @param interactions A list of predictor column indices to interact. All pairwise combinations will be computed
     *                       for the list.
     *   @param interaction_pairs A list of pairwise (first order) column interactions.
     *   @param balance_classes Balance training data class counts via over/under-sampling (for imbalanced data).
     *   @param class_sampling_factors Desired over/under-sampling ratios per class (in lexicographic order). If not
     *                                 specified, sampling factors will be automatically computed to obtain class balance
     *                                 during training. Requires balance_classes.
     *   @param max_after_balance_size Maximum relative size of the training data after balancing class counts (can be
     *                                 less than 1.0). Requires balance_classes.
     *   @param max_confusion_matrix_size [Deprecated] Maximum size (# classes) for confusion matrices to be printed in
     *                                    the Logs
     *   @param max_hit_ratio_k Maximum number (top K) of predictions to use for hit ratio computation (for multi-class
     *                          only, 0 to disable)
     *   @param compute_p_values Request p-values computation, p-values work only with IRLSM solver and no regularization
     *   @param remove_collinear_columns In case of linearly dependent columns, remove some of the dependent columns
     *   @param model_id Destination id for this model; auto-generated if not specified.
     *   @param training_frame Id of the training data frame.
     *   @param validation_frame Id of the validation data frame.
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or &gt;= 2).
     *   @param keep_cross_validation_models Whether to keep the cross-validation models.
     *   @param keep_cross_validation_predictions Whether to keep the predictions of the cross-validation models.
     *   @param keep_cross_validation_fold_assignment Whether to keep the cross-validation fold assignment.
     *   @param parallelize_cross_validation Allow parallel training of cross-validation models
     *   @param distribution Distribution function
     *   @param tweedie_power Tweedie power for Tweedie regression, must be between 1 and 2.
     *   @param quantile_alpha Desired quantile for Quantile regression, must be between 0 and 1.
     *   @param huber_alpha Desired quantile for Huber/M-regression (threshold between quadratic and linear loss, must be
     *                      between 0 and 1).
     *   @param response_column Response variable column.
     *   @param weights_column Column with observation weights. Giving some observation a weight of zero is equivalent to
     *                         excluding it from the dataset; giving an observation a relative weight of 2 is equivalent
     *                         to repeating that row twice. Negative weights are not allowed. Note: Weights are per-row
     *                         observation weights and do not increase the size of the data frame. This is typically the
     *                         number of times a row is repeated, but non-integer values are supported as well. During
     *                         training, rows with higher weights matter more, due to the larger loss function pre-factor.
     *   @param offset_column Offset column. This will be added to the combination of columns before applying the link
     *                        function.
     *   @param fold_column Column with cross-validation fold index assignment per observation.
     *   @param fold_assignment Cross-validation fold assignment scheme, if fold_column is not specified. The 'Stratified'
     *                          option will stratify the folds based on the response variable, for classification
     *                          problems.
     *   @param categorical_encoding Encoding scheme for categorical features
     *   @param max_categorical_levels For every categorical feature, only use this many most frequent categorical levels
     *                                 for model training. Only used for categorical_encoding == EnumLimited.
     *   @param ignored_columns Names of columns to ignore for training.
     *   @param ignore_const_cols Ignore constant columns.
     *   @param score_each_iteration Whether to score during each iteration of model training.
     *   @param checkpoint Model checkpoint to resume training with.
     *   @param stopping_rounds Early stopping based on convergence of stopping_metric. Stop if simple moving average of
     *                          length k of the stopping_metric does not improve for k:=stopping_rounds scoring events (0
     *                          to disable)
     *   @param max_runtime_secs Maximum allowed runtime in seconds for model training. Use 0 to disable.
     *   @param stopping_metric Metric to use for early stopping (AUTO: logloss for classification, deviance for
     *                          regression and anonomaly_score for Isolation Forest). Note that custom and
     *                          custom_increasing can only be used in GBM and DRF with the Python client.
     *   @param stopping_tolerance Relative tolerance for metric-based stopping criterion (stop if relative improvement is
     *                             not at least this much)
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     */
    @FormUrlEncoded
    @POST("/99/Grid/glm")
    Call<GLMV3> trainGlm(@Field("seed") long seed, @Field("family") GLMFamily family, @Field("rand_family") GLMFamily[] rand_family,
            @Field("tweedie_variance_power") double tweedie_variance_power, @Field("tweedie_link_power") double tweedie_link_power,
            @Field("theta") double theta, @Field("solver") GLMSolver solver, @Field("alpha") double[] alpha,
            @Field("lambda") double[] lambda, @Field("lambda_search") boolean lambda_search,
            @Field("early_stopping") boolean early_stopping, @Field("nlambdas") int nlambdas, @Field("standardize") boolean standardize,
            @Field("missing_values_handling") GLMMissingValuesHandling missing_values_handling, @Field("plug_values") String plug_values,
            @Field("non_negative") boolean non_negative, @Field("max_iterations") int max_iterations,
            @Field("beta_epsilon") double beta_epsilon, @Field("objective_epsilon") double objective_epsilon,
            @Field("gradient_epsilon") double gradient_epsilon, @Field("obj_reg") double obj_reg, @Field("link") GLMLink link,
            @Field("rand_link") GLMLink[] rand_link, @Field("startval") double[] startval, @Field("random_columns") int[] random_columns,
            @Field("calc_like") boolean calc_like, @Field("intercept") boolean intercept, @Field("HGLM") boolean HGLM,
            @Field("prior") double prior, @Field("lambda_min_ratio") double lambda_min_ratio,
            @Field("beta_constraints") String beta_constraints, @Field("max_active_predictors") int max_active_predictors,
            @Field("interactions") String[] interactions, @Field("interaction_pairs") StringPairV3[] interaction_pairs,
            @Field("balance_classes") boolean balance_classes, @Field("class_sampling_factors") float[] class_sampling_factors,
            @Field("max_after_balance_size") float max_after_balance_size,
            @Field("max_confusion_matrix_size") int max_confusion_matrix_size, @Field("max_hit_ratio_k") int max_hit_ratio_k,
            @Field("compute_p_values") boolean compute_p_values, @Field("remove_collinear_columns") boolean remove_collinear_columns,
            @Field("model_id") String model_id, @Field("training_frame") String training_frame,
            @Field("validation_frame") String validation_frame, @Field("nfolds") int nfolds,
            @Field("keep_cross_validation_models") boolean keep_cross_validation_models,
            @Field("keep_cross_validation_predictions") boolean keep_cross_validation_predictions,
            @Field("keep_cross_validation_fold_assignment") boolean keep_cross_validation_fold_assignment,
            @Field("parallelize_cross_validation") boolean parallelize_cross_validation,
            @Field("distribution") GenmodelutilsDistributionFamily distribution, @Field("tweedie_power") double tweedie_power,
            @Field("quantile_alpha") double quantile_alpha, @Field("huber_alpha") double huber_alpha,
            @Field("response_column") String response_column, @Field("weights_column") String weights_column,
            @Field("offset_column") String offset_column, @Field("fold_column") String fold_column,
            @Field("fold_assignment") ModelParametersFoldAssignmentScheme fold_assignment,
            @Field("categorical_encoding") ModelParametersCategoricalEncodingScheme categorical_encoding,
            @Field("max_categorical_levels") int max_categorical_levels, @Field("ignored_columns") String[] ignored_columns,
            @Field("ignore_const_cols") boolean ignore_const_cols, @Field("score_each_iteration") boolean score_each_iteration,
            @Field("checkpoint") String checkpoint, @Field("stopping_rounds") int stopping_rounds,
            @Field("max_runtime_secs") double max_runtime_secs, @Field("stopping_metric") ScoreKeeperStoppingMetric stopping_metric,
            @Field("stopping_tolerance") double stopping_tolerance, @Field("custom_metric_func") String custom_metric_func,
            @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir);

    @FormUrlEncoded
    @POST("/99/Grid/glm")
    Call<GLMV3> trainGlm();

    /**
     * Run grid search for GLRM model.
     *   @param transform Transformation of training data
     *   @param k Rank of matrix approximation
     *   @param loss Numeric loss function
     *   @param multi_loss Categorical loss function
     *   @param loss_by_col Loss function by column (override)
     *   @param loss_by_col_idx Loss function by column index (override)
     *   @param period Length of period (only used with periodic loss function)
     *   @param regularization_x Regularization function for X matrix
     *   @param regularization_y Regularization function for Y matrix
     *   @param gamma_x Regularization weight on X matrix
     *   @param gamma_y Regularization weight on Y matrix
     *   @param max_iterations Maximum number of iterations
     *   @param max_updates Maximum number of updates, defaults to 2*max_iterations
     *   @param init_step_size Initial step size
     *   @param min_step_size Minimum step size
     *   @param seed RNG seed for initialization
     *   @param init Initialization mode
     *   @param svd_method Method for computing SVD during initialization (Caution: Randomized is currently experimental
     *                     and unstable)
     *   @param user_y User-specified initial Y
     *   @param user_x User-specified initial X
     *   @param loading_name Frame key to save resulting X
     *   @param expand_user_y Expand categorical columns in user-specified initial Y
     *   @param impute_original Reconstruct original training data by reversing transform
     *   @param recover_svd Recover singular values and eigenvectors of XY
     *   @param model_id Destination id for this model; auto-generated if not specified.
     *   @param training_frame Id of the training data frame.
     *   @param validation_frame Id of the validation data frame.
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or &gt;= 2).
     *   @param keep_cross_validation_models Whether to keep the cross-validation models.
     *   @param keep_cross_validation_predictions Whether to keep the predictions of the cross-validation models.
     *   @param keep_cross_validation_fold_assignment Whether to keep the cross-validation fold assignment.
     *   @param parallelize_cross_validation Allow parallel training of cross-validation models
     *   @param distribution Distribution function
     *   @param tweedie_power Tweedie power for Tweedie regression, must be between 1 and 2.
     *   @param quantile_alpha Desired quantile for Quantile regression, must be between 0 and 1.
     *   @param huber_alpha Desired quantile for Huber/M-regression (threshold between quadratic and linear loss, must be
     *                      between 0 and 1).
     *   @param response_column Response variable column.
     *   @param weights_column Column with observation weights. Giving some observation a weight of zero is equivalent to
     *                         excluding it from the dataset; giving an observation a relative weight of 2 is equivalent
     *                         to repeating that row twice. Negative weights are not allowed. Note: Weights are per-row
     *                         observation weights and do not increase the size of the data frame. This is typically the
     *                         number of times a row is repeated, but non-integer values are supported as well. During
     *                         training, rows with higher weights matter more, due to the larger loss function pre-factor.
     *   @param offset_column Offset column. This will be added to the combination of columns before applying the link
     *                        function.
     *   @param fold_column Column with cross-validation fold index assignment per observation.
     *   @param fold_assignment Cross-validation fold assignment scheme, if fold_column is not specified. The 'Stratified'
     *                          option will stratify the folds based on the response variable, for classification
     *                          problems.
     *   @param categorical_encoding Encoding scheme for categorical features
     *   @param max_categorical_levels For every categorical feature, only use this many most frequent categorical levels
     *                                 for model training. Only used for categorical_encoding == EnumLimited.
     *   @param ignored_columns Names of columns to ignore for training.
     *   @param ignore_const_cols Ignore constant columns.
     *   @param score_each_iteration Whether to score during each iteration of model training.
     *   @param checkpoint Model checkpoint to resume training with.
     *   @param stopping_rounds Early stopping based on convergence of stopping_metric. Stop if simple moving average of
     *                          length k of the stopping_metric does not improve for k:=stopping_rounds scoring events (0
     *                          to disable)
     *   @param max_runtime_secs Maximum allowed runtime in seconds for model training. Use 0 to disable.
     *   @param stopping_metric Metric to use for early stopping (AUTO: logloss for classification, deviance for
     *                          regression and anonomaly_score for Isolation Forest). Note that custom and
     *                          custom_increasing can only be used in GBM and DRF with the Python client.
     *   @param stopping_tolerance Relative tolerance for metric-based stopping criterion (stop if relative improvement is
     *                             not at least this much)
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     */
    @FormUrlEncoded
    @POST("/99/Grid/glrm")
    Call<GLRMV3> trainGlrm(@Field("transform") DataInfoTransformType transform, @Field("k") int k,
            @Field("loss") GenmodelalgosglrmGlrmLoss loss, @Field("multi_loss") GenmodelalgosglrmGlrmLoss multi_loss,
            @Field("loss_by_col") GenmodelalgosglrmGlrmLoss[] loss_by_col, @Field("loss_by_col_idx") int[] loss_by_col_idx,
            @Field("period") int period, @Field("regularization_x") GenmodelalgosglrmGlrmRegularizer regularization_x,
            @Field("regularization_y") GenmodelalgosglrmGlrmRegularizer regularization_y, @Field("gamma_x") double gamma_x,
            @Field("gamma_y") double gamma_y, @Field("max_iterations") int max_iterations, @Field("max_updates") int max_updates,
            @Field("init_step_size") double init_step_size, @Field("min_step_size") double min_step_size, @Field("seed") long seed,
            @Field("init") GenmodelalgosglrmGlrmInitialization init, @Field("svd_method") SVDMethod svd_method,
            @Field("user_y") String user_y, @Field("user_x") String user_x, @Field("loading_name") String loading_name,
            @Field("expand_user_y") boolean expand_user_y, @Field("impute_original") boolean impute_original,
            @Field("recover_svd") boolean recover_svd, @Field("model_id") String model_id, @Field("training_frame") String training_frame,
            @Field("validation_frame") String validation_frame, @Field("nfolds") int nfolds,
            @Field("keep_cross_validation_models") boolean keep_cross_validation_models,
            @Field("keep_cross_validation_predictions") boolean keep_cross_validation_predictions,
            @Field("keep_cross_validation_fold_assignment") boolean keep_cross_validation_fold_assignment,
            @Field("parallelize_cross_validation") boolean parallelize_cross_validation,
            @Field("distribution") GenmodelutilsDistributionFamily distribution, @Field("tweedie_power") double tweedie_power,
            @Field("quantile_alpha") double quantile_alpha, @Field("huber_alpha") double huber_alpha,
            @Field("response_column") String response_column, @Field("weights_column") String weights_column,
            @Field("offset_column") String offset_column, @Field("fold_column") String fold_column,
            @Field("fold_assignment") ModelParametersFoldAssignmentScheme fold_assignment,
            @Field("categorical_encoding") ModelParametersCategoricalEncodingScheme categorical_encoding,
            @Field("max_categorical_levels") int max_categorical_levels, @Field("ignored_columns") String[] ignored_columns,
            @Field("ignore_const_cols") boolean ignore_const_cols, @Field("score_each_iteration") boolean score_each_iteration,
            @Field("checkpoint") String checkpoint, @Field("stopping_rounds") int stopping_rounds,
            @Field("max_runtime_secs") double max_runtime_secs, @Field("stopping_metric") ScoreKeeperStoppingMetric stopping_metric,
            @Field("stopping_tolerance") double stopping_tolerance, @Field("custom_metric_func") String custom_metric_func,
            @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir);

    @FormUrlEncoded
    @POST("/99/Grid/glrm")
    Call<GLRMV3> trainGlrm(@Field("k") int k);

    /**
     * Run grid search for KMeans model.
     *   @param user_points This option allows you to specify a dataframe, where each row represents an initial cluster
     *                      center. The user-specified points must have the same number of columns as the training
     *                      observations. The number of rows must equal the number of clusters
     *   @param max_iterations Maximum training iterations (if estimate_k is enabled, then this is for each inner Lloyds
     *                         iteration)
     *   @param standardize Standardize columns before computing distances
     *   @param seed RNG Seed
     *   @param init Initialization mode
     *   @param estimate_k Whether to estimate the number of clusters (&lt;=k) iteratively and deterministically.
     *   @param k The max. number of clusters. If estimate_k is disabled, the model will find k centroids, otherwise it
     *            will find up to k centroids.
     *   @param model_id Destination id for this model; auto-generated if not specified.
     *   @param training_frame Id of the training data frame.
     *   @param validation_frame Id of the validation data frame.
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or &gt;= 2).
     *   @param keep_cross_validation_models Whether to keep the cross-validation models.
     *   @param keep_cross_validation_predictions Whether to keep the predictions of the cross-validation models.
     *   @param keep_cross_validation_fold_assignment Whether to keep the cross-validation fold assignment.
     *   @param parallelize_cross_validation Allow parallel training of cross-validation models
     *   @param distribution Distribution function
     *   @param tweedie_power Tweedie power for Tweedie regression, must be between 1 and 2.
     *   @param quantile_alpha Desired quantile for Quantile regression, must be between 0 and 1.
     *   @param huber_alpha Desired quantile for Huber/M-regression (threshold between quadratic and linear loss, must be
     *                      between 0 and 1).
     *   @param response_column Response variable column.
     *   @param weights_column Column with observation weights. Giving some observation a weight of zero is equivalent to
     *                         excluding it from the dataset; giving an observation a relative weight of 2 is equivalent
     *                         to repeating that row twice. Negative weights are not allowed. Note: Weights are per-row
     *                         observation weights and do not increase the size of the data frame. This is typically the
     *                         number of times a row is repeated, but non-integer values are supported as well. During
     *                         training, rows with higher weights matter more, due to the larger loss function pre-factor.
     *   @param offset_column Offset column. This will be added to the combination of columns before applying the link
     *                        function.
     *   @param fold_column Column with cross-validation fold index assignment per observation.
     *   @param fold_assignment Cross-validation fold assignment scheme, if fold_column is not specified. The 'Stratified'
     *                          option will stratify the folds based on the response variable, for classification
     *                          problems.
     *   @param categorical_encoding Encoding scheme for categorical features
     *   @param max_categorical_levels For every categorical feature, only use this many most frequent categorical levels
     *                                 for model training. Only used for categorical_encoding == EnumLimited.
     *   @param ignored_columns Names of columns to ignore for training.
     *   @param ignore_const_cols Ignore constant columns.
     *   @param score_each_iteration Whether to score during each iteration of model training.
     *   @param checkpoint Model checkpoint to resume training with.
     *   @param stopping_rounds Early stopping based on convergence of stopping_metric. Stop if simple moving average of
     *                          length k of the stopping_metric does not improve for k:=stopping_rounds scoring events (0
     *                          to disable)
     *   @param max_runtime_secs Maximum allowed runtime in seconds for model training. Use 0 to disable.
     *   @param stopping_metric Metric to use for early stopping (AUTO: logloss for classification, deviance for
     *                          regression and anonomaly_score for Isolation Forest). Note that custom and
     *                          custom_increasing can only be used in GBM and DRF with the Python client.
     *   @param stopping_tolerance Relative tolerance for metric-based stopping criterion (stop if relative improvement is
     *                             not at least this much)
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     */
    @FormUrlEncoded
    @POST("/99/Grid/kmeans")
    Call<KMeansV3> trainKmeans(@Field("user_points") String user_points, @Field("max_iterations") int max_iterations,
            @Field("standardize") boolean standardize, @Field("seed") long seed, @Field("init") KMeansInitialization init,
            @Field("estimate_k") boolean estimate_k, @Field("k") int k, @Field("model_id") String model_id,
            @Field("training_frame") String training_frame, @Field("validation_frame") String validation_frame, @Field("nfolds") int nfolds,
            @Field("keep_cross_validation_models") boolean keep_cross_validation_models,
            @Field("keep_cross_validation_predictions") boolean keep_cross_validation_predictions,
            @Field("keep_cross_validation_fold_assignment") boolean keep_cross_validation_fold_assignment,
            @Field("parallelize_cross_validation") boolean parallelize_cross_validation,
            @Field("distribution") GenmodelutilsDistributionFamily distribution, @Field("tweedie_power") double tweedie_power,
            @Field("quantile_alpha") double quantile_alpha, @Field("huber_alpha") double huber_alpha,
            @Field("response_column") String response_column, @Field("weights_column") String weights_column,
            @Field("offset_column") String offset_column, @Field("fold_column") String fold_column,
            @Field("fold_assignment") ModelParametersFoldAssignmentScheme fold_assignment,
            @Field("categorical_encoding") ModelParametersCategoricalEncodingScheme categorical_encoding,
            @Field("max_categorical_levels") int max_categorical_levels, @Field("ignored_columns") String[] ignored_columns,
            @Field("ignore_const_cols") boolean ignore_const_cols, @Field("score_each_iteration") boolean score_each_iteration,
            @Field("checkpoint") String checkpoint, @Field("stopping_rounds") int stopping_rounds,
            @Field("max_runtime_secs") double max_runtime_secs, @Field("stopping_metric") ScoreKeeperStoppingMetric stopping_metric,
            @Field("stopping_tolerance") double stopping_tolerance, @Field("custom_metric_func") String custom_metric_func,
            @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir);

    @FormUrlEncoded
    @POST("/99/Grid/kmeans")
    Call<KMeansV3> trainKmeans();

    /**
     * Run grid search for NaiveBayes model.
     *   @param balance_classes Balance training data class counts via over/under-sampling (for imbalanced data).
     *   @param class_sampling_factors Desired over/under-sampling ratios per class (in lexicographic order). If not
     *                                 specified, sampling factors will be automatically computed to obtain class balance
     *                                 during training. Requires balance_classes.
     *   @param max_after_balance_size Maximum relative size of the training data after balancing class counts (can be
     *                                 less than 1.0). Requires balance_classes.
     *   @param max_confusion_matrix_size [Deprecated] Maximum size (# classes) for confusion matrices to be printed in
     *                                    the Logs
     *   @param max_hit_ratio_k Max. number (top K) of predictions to use for hit ratio computation (for multi-class only,
     *                          0 to disable)
     *   @param laplace Laplace smoothing parameter
     *   @param min_sdev Min. standard deviation to use for observations with not enough data
     *   @param eps_sdev Cutoff below which standard deviation is replaced with min_sdev
     *   @param min_prob Min. probability to use for observations with not enough data
     *   @param eps_prob Cutoff below which probability is replaced with min_prob
     *   @param compute_metrics Compute metrics on training data
     *   @param seed Seed for pseudo random number generator (only used for cross-validation and fold_assignment="Random"
     *               or "AUTO")
     *   @param model_id Destination id for this model; auto-generated if not specified.
     *   @param training_frame Id of the training data frame.
     *   @param validation_frame Id of the validation data frame.
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or &gt;= 2).
     *   @param keep_cross_validation_models Whether to keep the cross-validation models.
     *   @param keep_cross_validation_predictions Whether to keep the predictions of the cross-validation models.
     *   @param keep_cross_validation_fold_assignment Whether to keep the cross-validation fold assignment.
     *   @param parallelize_cross_validation Allow parallel training of cross-validation models
     *   @param distribution Distribution function
     *   @param tweedie_power Tweedie power for Tweedie regression, must be between 1 and 2.
     *   @param quantile_alpha Desired quantile for Quantile regression, must be between 0 and 1.
     *   @param huber_alpha Desired quantile for Huber/M-regression (threshold between quadratic and linear loss, must be
     *                      between 0 and 1).
     *   @param response_column Response variable column.
     *   @param weights_column Column with observation weights. Giving some observation a weight of zero is equivalent to
     *                         excluding it from the dataset; giving an observation a relative weight of 2 is equivalent
     *                         to repeating that row twice. Negative weights are not allowed. Note: Weights are per-row
     *                         observation weights and do not increase the size of the data frame. This is typically the
     *                         number of times a row is repeated, but non-integer values are supported as well. During
     *                         training, rows with higher weights matter more, due to the larger loss function pre-factor.
     *   @param offset_column Offset column. This will be added to the combination of columns before applying the link
     *                        function.
     *   @param fold_column Column with cross-validation fold index assignment per observation.
     *   @param fold_assignment Cross-validation fold assignment scheme, if fold_column is not specified. The 'Stratified'
     *                          option will stratify the folds based on the response variable, for classification
     *                          problems.
     *   @param categorical_encoding Encoding scheme for categorical features
     *   @param max_categorical_levels For every categorical feature, only use this many most frequent categorical levels
     *                                 for model training. Only used for categorical_encoding == EnumLimited.
     *   @param ignored_columns Names of columns to ignore for training.
     *   @param ignore_const_cols Ignore constant columns.
     *   @param score_each_iteration Whether to score during each iteration of model training.
     *   @param checkpoint Model checkpoint to resume training with.
     *   @param stopping_rounds Early stopping based on convergence of stopping_metric. Stop if simple moving average of
     *                          length k of the stopping_metric does not improve for k:=stopping_rounds scoring events (0
     *                          to disable)
     *   @param max_runtime_secs Maximum allowed runtime in seconds for model training. Use 0 to disable.
     *   @param stopping_metric Metric to use for early stopping (AUTO: logloss for classification, deviance for
     *                          regression and anonomaly_score for Isolation Forest). Note that custom and
     *                          custom_increasing can only be used in GBM and DRF with the Python client.
     *   @param stopping_tolerance Relative tolerance for metric-based stopping criterion (stop if relative improvement is
     *                             not at least this much)
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     */
    @FormUrlEncoded
    @POST("/99/Grid/naivebayes")
    Call<NaiveBayesV3> trainNaivebayes(@Field("balance_classes") boolean balance_classes,
            @Field("class_sampling_factors") float[] class_sampling_factors, @Field("max_after_balance_size") float max_after_balance_size,
            @Field("max_confusion_matrix_size") int max_confusion_matrix_size, @Field("max_hit_ratio_k") int max_hit_ratio_k,
            @Field("laplace") double laplace, @Field("min_sdev") double min_sdev, @Field("eps_sdev") double eps_sdev,
            @Field("min_prob") double min_prob, @Field("eps_prob") double eps_prob, @Field("compute_metrics") boolean compute_metrics,
            @Field("seed") long seed, @Field("model_id") String model_id, @Field("training_frame") String training_frame,
            @Field("validation_frame") String validation_frame, @Field("nfolds") int nfolds,
            @Field("keep_cross_validation_models") boolean keep_cross_validation_models,
            @Field("keep_cross_validation_predictions") boolean keep_cross_validation_predictions,
            @Field("keep_cross_validation_fold_assignment") boolean keep_cross_validation_fold_assignment,
            @Field("parallelize_cross_validation") boolean parallelize_cross_validation,
            @Field("distribution") GenmodelutilsDistributionFamily distribution, @Field("tweedie_power") double tweedie_power,
            @Field("quantile_alpha") double quantile_alpha, @Field("huber_alpha") double huber_alpha,
            @Field("response_column") String response_column, @Field("weights_column") String weights_column,
            @Field("offset_column") String offset_column, @Field("fold_column") String fold_column,
            @Field("fold_assignment") ModelParametersFoldAssignmentScheme fold_assignment,
            @Field("categorical_encoding") ModelParametersCategoricalEncodingScheme categorical_encoding,
            @Field("max_categorical_levels") int max_categorical_levels, @Field("ignored_columns") String[] ignored_columns,
            @Field("ignore_const_cols") boolean ignore_const_cols, @Field("score_each_iteration") boolean score_each_iteration,
            @Field("checkpoint") String checkpoint, @Field("stopping_rounds") int stopping_rounds,
            @Field("max_runtime_secs") double max_runtime_secs, @Field("stopping_metric") ScoreKeeperStoppingMetric stopping_metric,
            @Field("stopping_tolerance") double stopping_tolerance, @Field("custom_metric_func") String custom_metric_func,
            @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir);

    @FormUrlEncoded
    @POST("/99/Grid/naivebayes")
    Call<NaiveBayesV3> trainNaivebayes();

    /**
     * Run grid search for PCA model.
     *   @param transform Transformation of training data
     *   @param pca_method Specify the algorithm to use for computing the principal components: GramSVD - uses a
     *                     distributed computation of the Gram matrix, followed by a local SVD; Power - computes the SVD
     *                     using the power iteration method (experimental); Randomized - uses randomized subspace
     *                     iteration method; GLRM - fits a generalized low-rank model with L2 loss function and no
     *                     regularization and solves for the SVD using local matrix algebra (experimental)
     *   @param pca_impl Specify the implementation to use for computing PCA (via SVD or EVD): MTJ_EVD_DENSEMATRIX -
     *                   eigenvalue decompositions for dense matrix using MTJ; MTJ_EVD_SYMMMATRIX - eigenvalue
     *                   decompositions for symmetric matrix using MTJ; MTJ_SVD_DENSEMATRIX - singular-value
     *                   decompositions for dense matrix using MTJ; JAMA - eigenvalue decompositions for dense matrix
     *                   using JAMA. References: JAMA - http://math.nist.gov/javanumerics/jama/; MTJ -
     *                   https://github.com/fommil/matrix-toolkits-java/
     *   @param k Rank of matrix approximation
     *   @param max_iterations Maximum training iterations
     *   @param seed RNG seed for initialization
     *   @param use_all_factor_levels Whether first factor level is included in each categorical expansion
     *   @param compute_metrics Whether to compute metrics on the training data
     *   @param impute_missing Whether to impute missing entries with the column mean
     *   @param model_id Destination id for this model; auto-generated if not specified.
     *   @param training_frame Id of the training data frame.
     *   @param validation_frame Id of the validation data frame.
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or &gt;= 2).
     *   @param keep_cross_validation_models Whether to keep the cross-validation models.
     *   @param keep_cross_validation_predictions Whether to keep the predictions of the cross-validation models.
     *   @param keep_cross_validation_fold_assignment Whether to keep the cross-validation fold assignment.
     *   @param parallelize_cross_validation Allow parallel training of cross-validation models
     *   @param distribution Distribution function
     *   @param tweedie_power Tweedie power for Tweedie regression, must be between 1 and 2.
     *   @param quantile_alpha Desired quantile for Quantile regression, must be between 0 and 1.
     *   @param huber_alpha Desired quantile for Huber/M-regression (threshold between quadratic and linear loss, must be
     *                      between 0 and 1).
     *   @param response_column Response variable column.
     *   @param weights_column Column with observation weights. Giving some observation a weight of zero is equivalent to
     *                         excluding it from the dataset; giving an observation a relative weight of 2 is equivalent
     *                         to repeating that row twice. Negative weights are not allowed. Note: Weights are per-row
     *                         observation weights and do not increase the size of the data frame. This is typically the
     *                         number of times a row is repeated, but non-integer values are supported as well. During
     *                         training, rows with higher weights matter more, due to the larger loss function pre-factor.
     *   @param offset_column Offset column. This will be added to the combination of columns before applying the link
     *                        function.
     *   @param fold_column Column with cross-validation fold index assignment per observation.
     *   @param fold_assignment Cross-validation fold assignment scheme, if fold_column is not specified. The 'Stratified'
     *                          option will stratify the folds based on the response variable, for classification
     *                          problems.
     *   @param categorical_encoding Encoding scheme for categorical features
     *   @param max_categorical_levels For every categorical feature, only use this many most frequent categorical levels
     *                                 for model training. Only used for categorical_encoding == EnumLimited.
     *   @param ignored_columns Names of columns to ignore for training.
     *   @param ignore_const_cols Ignore constant columns.
     *   @param score_each_iteration Whether to score during each iteration of model training.
     *   @param checkpoint Model checkpoint to resume training with.
     *   @param stopping_rounds Early stopping based on convergence of stopping_metric. Stop if simple moving average of
     *                          length k of the stopping_metric does not improve for k:=stopping_rounds scoring events (0
     *                          to disable)
     *   @param max_runtime_secs Maximum allowed runtime in seconds for model training. Use 0 to disable.
     *   @param stopping_metric Metric to use for early stopping (AUTO: logloss for classification, deviance for
     *                          regression and anonomaly_score for Isolation Forest). Note that custom and
     *                          custom_increasing can only be used in GBM and DRF with the Python client.
     *   @param stopping_tolerance Relative tolerance for metric-based stopping criterion (stop if relative improvement is
     *                             not at least this much)
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     */
    @FormUrlEncoded
    @POST("/99/Grid/pca")
    Call<PCAV3> trainPca(@Field("transform") DataInfoTransformType transform, @Field("pca_method") PCAMethod pca_method,
            @Field("pca_impl") PCAImplementation pca_impl, @Field("k") int k, @Field("max_iterations") int max_iterations,
            @Field("seed") long seed, @Field("use_all_factor_levels") boolean use_all_factor_levels,
            @Field("compute_metrics") boolean compute_metrics, @Field("impute_missing") boolean impute_missing,
            @Field("model_id") String model_id, @Field("training_frame") String training_frame,
            @Field("validation_frame") String validation_frame, @Field("nfolds") int nfolds,
            @Field("keep_cross_validation_models") boolean keep_cross_validation_models,
            @Field("keep_cross_validation_predictions") boolean keep_cross_validation_predictions,
            @Field("keep_cross_validation_fold_assignment") boolean keep_cross_validation_fold_assignment,
            @Field("parallelize_cross_validation") boolean parallelize_cross_validation,
            @Field("distribution") GenmodelutilsDistributionFamily distribution, @Field("tweedie_power") double tweedie_power,
            @Field("quantile_alpha") double quantile_alpha, @Field("huber_alpha") double huber_alpha,
            @Field("response_column") String response_column, @Field("weights_column") String weights_column,
            @Field("offset_column") String offset_column, @Field("fold_column") String fold_column,
            @Field("fold_assignment") ModelParametersFoldAssignmentScheme fold_assignment,
            @Field("categorical_encoding") ModelParametersCategoricalEncodingScheme categorical_encoding,
            @Field("max_categorical_levels") int max_categorical_levels, @Field("ignored_columns") String[] ignored_columns,
            @Field("ignore_const_cols") boolean ignore_const_cols, @Field("score_each_iteration") boolean score_each_iteration,
            @Field("checkpoint") String checkpoint, @Field("stopping_rounds") int stopping_rounds,
            @Field("max_runtime_secs") double max_runtime_secs, @Field("stopping_metric") ScoreKeeperStoppingMetric stopping_metric,
            @Field("stopping_tolerance") double stopping_tolerance, @Field("custom_metric_func") String custom_metric_func,
            @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir);

    @FormUrlEncoded
    @POST("/99/Grid/pca")
    Call<PCAV3> trainPca(@Field("k") int k);

    /**
     * Run grid search for SVD model.
     *   @param transform Transformation of training data
     *   @param svd_method Method for computing SVD (Caution: Randomized is currently experimental and unstable)
     *   @param nv Number of right singular vectors
     *   @param max_iterations Maximum iterations
     *   @param seed RNG seed for k-means++ initialization
     *   @param keep_u Save left singular vectors?
     *   @param u_name Frame key to save left singular vectors
     *   @param use_all_factor_levels Whether first factor level is included in each categorical expansion
     *   @param model_id Destination id for this model; auto-generated if not specified.
     *   @param training_frame Id of the training data frame.
     *   @param validation_frame Id of the validation data frame.
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or &gt;= 2).
     *   @param keep_cross_validation_models Whether to keep the cross-validation models.
     *   @param keep_cross_validation_predictions Whether to keep the predictions of the cross-validation models.
     *   @param keep_cross_validation_fold_assignment Whether to keep the cross-validation fold assignment.
     *   @param parallelize_cross_validation Allow parallel training of cross-validation models
     *   @param distribution Distribution function
     *   @param tweedie_power Tweedie power for Tweedie regression, must be between 1 and 2.
     *   @param quantile_alpha Desired quantile for Quantile regression, must be between 0 and 1.
     *   @param huber_alpha Desired quantile for Huber/M-regression (threshold between quadratic and linear loss, must be
     *                      between 0 and 1).
     *   @param response_column Response variable column.
     *   @param weights_column Column with observation weights. Giving some observation a weight of zero is equivalent to
     *                         excluding it from the dataset; giving an observation a relative weight of 2 is equivalent
     *                         to repeating that row twice. Negative weights are not allowed. Note: Weights are per-row
     *                         observation weights and do not increase the size of the data frame. This is typically the
     *                         number of times a row is repeated, but non-integer values are supported as well. During
     *                         training, rows with higher weights matter more, due to the larger loss function pre-factor.
     *   @param offset_column Offset column. This will be added to the combination of columns before applying the link
     *                        function.
     *   @param fold_column Column with cross-validation fold index assignment per observation.
     *   @param fold_assignment Cross-validation fold assignment scheme, if fold_column is not specified. The 'Stratified'
     *                          option will stratify the folds based on the response variable, for classification
     *                          problems.
     *   @param categorical_encoding Encoding scheme for categorical features
     *   @param max_categorical_levels For every categorical feature, only use this many most frequent categorical levels
     *                                 for model training. Only used for categorical_encoding == EnumLimited.
     *   @param ignored_columns Names of columns to ignore for training.
     *   @param ignore_const_cols Ignore constant columns.
     *   @param score_each_iteration Whether to score during each iteration of model training.
     *   @param checkpoint Model checkpoint to resume training with.
     *   @param stopping_rounds Early stopping based on convergence of stopping_metric. Stop if simple moving average of
     *                          length k of the stopping_metric does not improve for k:=stopping_rounds scoring events (0
     *                          to disable)
     *   @param max_runtime_secs Maximum allowed runtime in seconds for model training. Use 0 to disable.
     *   @param stopping_metric Metric to use for early stopping (AUTO: logloss for classification, deviance for
     *                          regression and anonomaly_score for Isolation Forest). Note that custom and
     *                          custom_increasing can only be used in GBM and DRF with the Python client.
     *   @param stopping_tolerance Relative tolerance for metric-based stopping criterion (stop if relative improvement is
     *                             not at least this much)
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     */
    @FormUrlEncoded
    @POST("/99/Grid/svd")
    Call<SVDV99> trainSvd(@Field("transform") DataInfoTransformType transform, @Field("svd_method") SVDMethod svd_method,
            @Field("nv") int nv, @Field("max_iterations") int max_iterations, @Field("seed") long seed, @Field("keep_u") boolean keep_u,
            @Field("u_name") String u_name, @Field("use_all_factor_levels") boolean use_all_factor_levels,
            @Field("model_id") String model_id, @Field("training_frame") String training_frame,
            @Field("validation_frame") String validation_frame, @Field("nfolds") int nfolds,
            @Field("keep_cross_validation_models") boolean keep_cross_validation_models,
            @Field("keep_cross_validation_predictions") boolean keep_cross_validation_predictions,
            @Field("keep_cross_validation_fold_assignment") boolean keep_cross_validation_fold_assignment,
            @Field("parallelize_cross_validation") boolean parallelize_cross_validation,
            @Field("distribution") GenmodelutilsDistributionFamily distribution, @Field("tweedie_power") double tweedie_power,
            @Field("quantile_alpha") double quantile_alpha, @Field("huber_alpha") double huber_alpha,
            @Field("response_column") String response_column, @Field("weights_column") String weights_column,
            @Field("offset_column") String offset_column, @Field("fold_column") String fold_column,
            @Field("fold_assignment") ModelParametersFoldAssignmentScheme fold_assignment,
            @Field("categorical_encoding") ModelParametersCategoricalEncodingScheme categorical_encoding,
            @Field("max_categorical_levels") int max_categorical_levels, @Field("ignored_columns") String[] ignored_columns,
            @Field("ignore_const_cols") boolean ignore_const_cols, @Field("score_each_iteration") boolean score_each_iteration,
            @Field("checkpoint") String checkpoint, @Field("stopping_rounds") int stopping_rounds,
            @Field("max_runtime_secs") double max_runtime_secs, @Field("stopping_metric") ScoreKeeperStoppingMetric stopping_metric,
            @Field("stopping_tolerance") double stopping_tolerance, @Field("custom_metric_func") String custom_metric_func,
            @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir);

    @FormUrlEncoded
    @POST("/99/Grid/svd")
    Call<SVDV99> trainSvd();

    /**
     * Run grid search for DRF model.
     *   @param mtries Number of variables randomly sampled as candidates at each split. If set to -1, defaults to sqrt{p}
     *                 for classification and p/3 for regression (where p is the # of predictors
     *   @param binomial_double_trees For binary classification: Build 2x as many trees (one per class) - can lead to
     *                                higher accuracy.
     *   @param sample_rate Row sample rate per tree (from 0.0 to 1.0)
     *   @param balance_classes Balance training data class counts via over/under-sampling (for imbalanced data).
     *   @param class_sampling_factors Desired over/under-sampling ratios per class (in lexicographic order). If not
     *                                 specified, sampling factors will be automatically computed to obtain class balance
     *                                 during training. Requires balance_classes.
     *   @param max_after_balance_size Maximum relative size of the training data after balancing class counts (can be
     *                                 less than 1.0). Requires balance_classes.
     *   @param max_confusion_matrix_size [Deprecated] Maximum size (# classes) for confusion matrices to be printed in
     *                                    the Logs
     *   @param max_hit_ratio_k Max. number (top K) of predictions to use for hit ratio computation (for multi-class only,
     *                          0 to disable)
     *   @param ntrees Number of trees.
     *   @param max_depth Maximum tree depth.
     *   @param min_rows Fewest allowed (weighted) observations in a leaf.
     *   @param nbins For numerical columns (real/int), build a histogram of (at least) this many bins, then split at the
     *                best point
     *   @param nbins_top_level For numerical columns (real/int), build a histogram of (at most) this many bins at the
     *                          root level, then decrease by factor of two per level
     *   @param nbins_cats For categorical columns (factors), build a histogram of this many bins, then split at the best
     *                     point. Higher values can lead to more overfitting.
     *   @param r2_stopping r2_stopping is no longer supported and will be ignored if set - please use stopping_rounds,
     *                      stopping_metric and stopping_tolerance instead. Previous version of H2O would stop making
     *                      trees when the R^2 metric equals or exceeds this
     *   @param seed Seed for pseudo random number generator (if applicable)
     *   @param build_tree_one_node Run on one node only; no network overhead but fewer cpus used.  Suitable for small
     *                              datasets.
     *   @param sample_rate_per_class A list of row sample rates per class (relative fraction for each class, from 0.0 to
     *                                1.0), for each tree
     *   @param col_sample_rate_per_tree Column sample rate per tree (from 0.0 to 1.0)
     *   @param col_sample_rate_change_per_level Relative change of the column sampling rate for every level (must be &gt;
     *                                           0.0 and &lt;= 2.0)
     *   @param score_tree_interval Score the model after every so many trees. Disabled if set to 0.
     *   @param min_split_improvement Minimum relative improvement in squared error reduction for a split to happen
     *   @param histogram_type What type of histogram to use for finding optimal split points
     *   @param calibrate_model Use Platt Scaling to calculate calibrated class probabilities. Calibration can provide
     *                          more accurate estimates of class probabilities.
     *   @param calibration_frame Calibration frame for Platt Scaling
     *   @param check_constant_response Check if response column is constant. If enabled, then an exception is thrown if
     *                                  the response column is a constant value.If disabled, then model will train
     *                                  regardless of the response column being a constant value or not.
     *   @param model_id Destination id for this model; auto-generated if not specified.
     *   @param training_frame Id of the training data frame.
     *   @param validation_frame Id of the validation data frame.
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or &gt;= 2).
     *   @param keep_cross_validation_models Whether to keep the cross-validation models.
     *   @param keep_cross_validation_predictions Whether to keep the predictions of the cross-validation models.
     *   @param keep_cross_validation_fold_assignment Whether to keep the cross-validation fold assignment.
     *   @param parallelize_cross_validation Allow parallel training of cross-validation models
     *   @param distribution Distribution function
     *   @param tweedie_power Tweedie power for Tweedie regression, must be between 1 and 2.
     *   @param quantile_alpha Desired quantile for Quantile regression, must be between 0 and 1.
     *   @param huber_alpha Desired quantile for Huber/M-regression (threshold between quadratic and linear loss, must be
     *                      between 0 and 1).
     *   @param response_column Response variable column.
     *   @param weights_column Column with observation weights. Giving some observation a weight of zero is equivalent to
     *                         excluding it from the dataset; giving an observation a relative weight of 2 is equivalent
     *                         to repeating that row twice. Negative weights are not allowed. Note: Weights are per-row
     *                         observation weights and do not increase the size of the data frame. This is typically the
     *                         number of times a row is repeated, but non-integer values are supported as well. During
     *                         training, rows with higher weights matter more, due to the larger loss function pre-factor.
     *   @param offset_column Offset column. This will be added to the combination of columns before applying the link
     *                        function.
     *   @param fold_column Column with cross-validation fold index assignment per observation.
     *   @param fold_assignment Cross-validation fold assignment scheme, if fold_column is not specified. The 'Stratified'
     *                          option will stratify the folds based on the response variable, for classification
     *                          problems.
     *   @param categorical_encoding Encoding scheme for categorical features
     *   @param max_categorical_levels For every categorical feature, only use this many most frequent categorical levels
     *                                 for model training. Only used for categorical_encoding == EnumLimited.
     *   @param ignored_columns Names of columns to ignore for training.
     *   @param ignore_const_cols Ignore constant columns.
     *   @param score_each_iteration Whether to score during each iteration of model training.
     *   @param checkpoint Model checkpoint to resume training with.
     *   @param stopping_rounds Early stopping based on convergence of stopping_metric. Stop if simple moving average of
     *                          length k of the stopping_metric does not improve for k:=stopping_rounds scoring events (0
     *                          to disable)
     *   @param max_runtime_secs Maximum allowed runtime in seconds for model training. Use 0 to disable.
     *   @param stopping_metric Metric to use for early stopping (AUTO: logloss for classification, deviance for
     *                          regression and anonomaly_score for Isolation Forest). Note that custom and
     *                          custom_increasing can only be used in GBM and DRF with the Python client.
     *   @param stopping_tolerance Relative tolerance for metric-based stopping criterion (stop if relative improvement is
     *                             not at least this much)
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     */
    @FormUrlEncoded
    @POST("/99/Grid/drf")
    Call<DRFV3> trainDrf(@Field("mtries") int mtries, @Field("binomial_double_trees") boolean binomial_double_trees,
            @Field("sample_rate") double sample_rate, @Field("balance_classes") boolean balance_classes,
            @Field("class_sampling_factors") float[] class_sampling_factors, @Field("max_after_balance_size") float max_after_balance_size,
            @Field("max_confusion_matrix_size") int max_confusion_matrix_size, @Field("max_hit_ratio_k") int max_hit_ratio_k,
            @Field("ntrees") int ntrees, @Field("max_depth") int max_depth, @Field("min_rows") double min_rows, @Field("nbins") int nbins,
            @Field("nbins_top_level") int nbins_top_level, @Field("nbins_cats") int nbins_cats, @Field("r2_stopping") double r2_stopping,
            @Field("seed") long seed, @Field("build_tree_one_node") boolean build_tree_one_node,
            @Field("sample_rate_per_class") double[] sample_rate_per_class,
            @Field("col_sample_rate_per_tree") double col_sample_rate_per_tree,
            @Field("col_sample_rate_change_per_level") double col_sample_rate_change_per_level,
            @Field("score_tree_interval") int score_tree_interval, @Field("min_split_improvement") double min_split_improvement,
            @Field("histogram_type") TreeSharedTreeModelSharedTreeParametersHistogramType histogram_type,
            @Field("calibrate_model") boolean calibrate_model, @Field("calibration_frame") String calibration_frame,
            @Field("check_constant_response") boolean check_constant_response, @Field("model_id") String model_id,
            @Field("training_frame") String training_frame, @Field("validation_frame") String validation_frame, @Field("nfolds") int nfolds,
            @Field("keep_cross_validation_models") boolean keep_cross_validation_models,
            @Field("keep_cross_validation_predictions") boolean keep_cross_validation_predictions,
            @Field("keep_cross_validation_fold_assignment") boolean keep_cross_validation_fold_assignment,
            @Field("parallelize_cross_validation") boolean parallelize_cross_validation,
            @Field("distribution") GenmodelutilsDistributionFamily distribution, @Field("tweedie_power") double tweedie_power,
            @Field("quantile_alpha") double quantile_alpha, @Field("huber_alpha") double huber_alpha,
            @Field("response_column") String response_column, @Field("weights_column") String weights_column,
            @Field("offset_column") String offset_column, @Field("fold_column") String fold_column,
            @Field("fold_assignment") ModelParametersFoldAssignmentScheme fold_assignment,
            @Field("categorical_encoding") ModelParametersCategoricalEncodingScheme categorical_encoding,
            @Field("max_categorical_levels") int max_categorical_levels, @Field("ignored_columns") String[] ignored_columns,
            @Field("ignore_const_cols") boolean ignore_const_cols, @Field("score_each_iteration") boolean score_each_iteration,
            @Field("checkpoint") String checkpoint, @Field("stopping_rounds") int stopping_rounds,
            @Field("max_runtime_secs") double max_runtime_secs, @Field("stopping_metric") ScoreKeeperStoppingMetric stopping_metric,
            @Field("stopping_tolerance") double stopping_tolerance, @Field("custom_metric_func") String custom_metric_func,
            @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir);

    @FormUrlEncoded
    @POST("/99/Grid/drf")
    Call<DRFV3> trainDrf();

    /**
     * Run grid search for GBM model.
     *   @param learn_rate Learning rate (from 0.0 to 1.0)
     *   @param learn_rate_annealing Scale the learning rate by this factor after each tree (e.g., 0.99 or 0.999)
     *   @param sample_rate Row sample rate per tree (from 0.0 to 1.0)
     *   @param col_sample_rate Column sample rate (from 0.0 to 1.0)
     *   @param monotone_constraints A mapping representing monotonic constraints. Use +1 to enforce an increasing
     *                               constraint and -1 to specify a decreasing constraint.
     *   @param max_abs_leafnode_pred Maximum absolute value of a leaf node prediction
     *   @param pred_noise_bandwidth Bandwidth (sigma) of Gaussian multiplicative noise ~N(1,sigma) for tree node
     *                               predictions
     *   @param balance_classes Balance training data class counts via over/under-sampling (for imbalanced data).
     *   @param class_sampling_factors Desired over/under-sampling ratios per class (in lexicographic order). If not
     *                                 specified, sampling factors will be automatically computed to obtain class balance
     *                                 during training. Requires balance_classes.
     *   @param max_after_balance_size Maximum relative size of the training data after balancing class counts (can be
     *                                 less than 1.0). Requires balance_classes.
     *   @param max_confusion_matrix_size [Deprecated] Maximum size (# classes) for confusion matrices to be printed in
     *                                    the Logs
     *   @param max_hit_ratio_k Max. number (top K) of predictions to use for hit ratio computation (for multi-class only,
     *                          0 to disable)
     *   @param ntrees Number of trees.
     *   @param max_depth Maximum tree depth.
     *   @param min_rows Fewest allowed (weighted) observations in a leaf.
     *   @param nbins For numerical columns (real/int), build a histogram of (at least) this many bins, then split at the
     *                best point
     *   @param nbins_top_level For numerical columns (real/int), build a histogram of (at most) this many bins at the
     *                          root level, then decrease by factor of two per level
     *   @param nbins_cats For categorical columns (factors), build a histogram of this many bins, then split at the best
     *                     point. Higher values can lead to more overfitting.
     *   @param r2_stopping r2_stopping is no longer supported and will be ignored if set - please use stopping_rounds,
     *                      stopping_metric and stopping_tolerance instead. Previous version of H2O would stop making
     *                      trees when the R^2 metric equals or exceeds this
     *   @param seed Seed for pseudo random number generator (if applicable)
     *   @param build_tree_one_node Run on one node only; no network overhead but fewer cpus used.  Suitable for small
     *                              datasets.
     *   @param sample_rate_per_class A list of row sample rates per class (relative fraction for each class, from 0.0 to
     *                                1.0), for each tree
     *   @param col_sample_rate_per_tree Column sample rate per tree (from 0.0 to 1.0)
     *   @param col_sample_rate_change_per_level Relative change of the column sampling rate for every level (must be &gt;
     *                                           0.0 and &lt;= 2.0)
     *   @param score_tree_interval Score the model after every so many trees. Disabled if set to 0.
     *   @param min_split_improvement Minimum relative improvement in squared error reduction for a split to happen
     *   @param histogram_type What type of histogram to use for finding optimal split points
     *   @param calibrate_model Use Platt Scaling to calculate calibrated class probabilities. Calibration can provide
     *                          more accurate estimates of class probabilities.
     *   @param calibration_frame Calibration frame for Platt Scaling
     *   @param check_constant_response Check if response column is constant. If enabled, then an exception is thrown if
     *                                  the response column is a constant value.If disabled, then model will train
     *                                  regardless of the response column being a constant value or not.
     *   @param model_id Destination id for this model; auto-generated if not specified.
     *   @param training_frame Id of the training data frame.
     *   @param validation_frame Id of the validation data frame.
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or &gt;= 2).
     *   @param keep_cross_validation_models Whether to keep the cross-validation models.
     *   @param keep_cross_validation_predictions Whether to keep the predictions of the cross-validation models.
     *   @param keep_cross_validation_fold_assignment Whether to keep the cross-validation fold assignment.
     *   @param parallelize_cross_validation Allow parallel training of cross-validation models
     *   @param distribution Distribution function
     *   @param tweedie_power Tweedie power for Tweedie regression, must be between 1 and 2.
     *   @param quantile_alpha Desired quantile for Quantile regression, must be between 0 and 1.
     *   @param huber_alpha Desired quantile for Huber/M-regression (threshold between quadratic and linear loss, must be
     *                      between 0 and 1).
     *   @param response_column Response variable column.
     *   @param weights_column Column with observation weights. Giving some observation a weight of zero is equivalent to
     *                         excluding it from the dataset; giving an observation a relative weight of 2 is equivalent
     *                         to repeating that row twice. Negative weights are not allowed. Note: Weights are per-row
     *                         observation weights and do not increase the size of the data frame. This is typically the
     *                         number of times a row is repeated, but non-integer values are supported as well. During
     *                         training, rows with higher weights matter more, due to the larger loss function pre-factor.
     *   @param offset_column Offset column. This will be added to the combination of columns before applying the link
     *                        function.
     *   @param fold_column Column with cross-validation fold index assignment per observation.
     *   @param fold_assignment Cross-validation fold assignment scheme, if fold_column is not specified. The 'Stratified'
     *                          option will stratify the folds based on the response variable, for classification
     *                          problems.
     *   @param categorical_encoding Encoding scheme for categorical features
     *   @param max_categorical_levels For every categorical feature, only use this many most frequent categorical levels
     *                                 for model training. Only used for categorical_encoding == EnumLimited.
     *   @param ignored_columns Names of columns to ignore for training.
     *   @param ignore_const_cols Ignore constant columns.
     *   @param score_each_iteration Whether to score during each iteration of model training.
     *   @param checkpoint Model checkpoint to resume training with.
     *   @param stopping_rounds Early stopping based on convergence of stopping_metric. Stop if simple moving average of
     *                          length k of the stopping_metric does not improve for k:=stopping_rounds scoring events (0
     *                          to disable)
     *   @param max_runtime_secs Maximum allowed runtime in seconds for model training. Use 0 to disable.
     *   @param stopping_metric Metric to use for early stopping (AUTO: logloss for classification, deviance for
     *                          regression and anonomaly_score for Isolation Forest). Note that custom and
     *                          custom_increasing can only be used in GBM and DRF with the Python client.
     *   @param stopping_tolerance Relative tolerance for metric-based stopping criterion (stop if relative improvement is
     *                             not at least this much)
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     */
    @FormUrlEncoded
    @POST("/99/Grid/gbm")
    Call<GBMV3> trainGbm(@Field("learn_rate") double learn_rate, @Field("learn_rate_annealing") double learn_rate_annealing,
            @Field("sample_rate") double sample_rate, @Field("col_sample_rate") double col_sample_rate,
            @Field("monotone_constraints") KeyValueV3[] monotone_constraints, @Field("max_abs_leafnode_pred") double max_abs_leafnode_pred,
            @Field("pred_noise_bandwidth") double pred_noise_bandwidth, @Field("balance_classes") boolean balance_classes,
            @Field("class_sampling_factors") float[] class_sampling_factors, @Field("max_after_balance_size") float max_after_balance_size,
            @Field("max_confusion_matrix_size") int max_confusion_matrix_size, @Field("max_hit_ratio_k") int max_hit_ratio_k,
            @Field("ntrees") int ntrees, @Field("max_depth") int max_depth, @Field("min_rows") double min_rows, @Field("nbins") int nbins,
            @Field("nbins_top_level") int nbins_top_level, @Field("nbins_cats") int nbins_cats, @Field("r2_stopping") double r2_stopping,
            @Field("seed") long seed, @Field("build_tree_one_node") boolean build_tree_one_node,
            @Field("sample_rate_per_class") double[] sample_rate_per_class,
            @Field("col_sample_rate_per_tree") double col_sample_rate_per_tree,
            @Field("col_sample_rate_change_per_level") double col_sample_rate_change_per_level,
            @Field("score_tree_interval") int score_tree_interval, @Field("min_split_improvement") double min_split_improvement,
            @Field("histogram_type") TreeSharedTreeModelSharedTreeParametersHistogramType histogram_type,
            @Field("calibrate_model") boolean calibrate_model, @Field("calibration_frame") String calibration_frame,
            @Field("check_constant_response") boolean check_constant_response, @Field("model_id") String model_id,
            @Field("training_frame") String training_frame, @Field("validation_frame") String validation_frame, @Field("nfolds") int nfolds,
            @Field("keep_cross_validation_models") boolean keep_cross_validation_models,
            @Field("keep_cross_validation_predictions") boolean keep_cross_validation_predictions,
            @Field("keep_cross_validation_fold_assignment") boolean keep_cross_validation_fold_assignment,
            @Field("parallelize_cross_validation") boolean parallelize_cross_validation,
            @Field("distribution") GenmodelutilsDistributionFamily distribution, @Field("tweedie_power") double tweedie_power,
            @Field("quantile_alpha") double quantile_alpha, @Field("huber_alpha") double huber_alpha,
            @Field("response_column") String response_column, @Field("weights_column") String weights_column,
            @Field("offset_column") String offset_column, @Field("fold_column") String fold_column,
            @Field("fold_assignment") ModelParametersFoldAssignmentScheme fold_assignment,
            @Field("categorical_encoding") ModelParametersCategoricalEncodingScheme categorical_encoding,
            @Field("max_categorical_levels") int max_categorical_levels, @Field("ignored_columns") String[] ignored_columns,
            @Field("ignore_const_cols") boolean ignore_const_cols, @Field("score_each_iteration") boolean score_each_iteration,
            @Field("checkpoint") String checkpoint, @Field("stopping_rounds") int stopping_rounds,
            @Field("max_runtime_secs") double max_runtime_secs, @Field("stopping_metric") ScoreKeeperStoppingMetric stopping_metric,
            @Field("stopping_tolerance") double stopping_tolerance, @Field("custom_metric_func") String custom_metric_func,
            @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir);

    @FormUrlEncoded
    @POST("/99/Grid/gbm")
    Call<GBMV3> trainGbm();

    /**
     * Run grid search for IsolationForest model.
     *   @param sample_size Number of randomly sampled observations used to train each Isolation Forest tree. Only one of
     *                      parameters sample_size and sample_rate should be defined. If sample_rate is defined,
     *                      sample_size will be ignored.
     *   @param sample_rate Rate of randomly sampled observations used to train each Isolation Forest tree. Needs to be in
     *                      range from 0.0 to 1.0. If set to -1, sample_rate is disabled and sample_size will be used
     *                      instead.
     *   @param mtries Number of variables randomly sampled as candidates at each split. If set to -1, defaults (number of
     *                 predictors)/3.
     *   @param balance_classes Balance training data class counts via over/under-sampling (for imbalanced data).
     *   @param class_sampling_factors Desired over/under-sampling ratios per class (in lexicographic order). If not
     *                                 specified, sampling factors will be automatically computed to obtain class balance
     *                                 during training. Requires balance_classes.
     *   @param max_after_balance_size Maximum relative size of the training data after balancing class counts (can be
     *                                 less than 1.0). Requires balance_classes.
     *   @param max_confusion_matrix_size [Deprecated] Maximum size (# classes) for confusion matrices to be printed in
     *                                    the Logs
     *   @param max_hit_ratio_k Max. number (top K) of predictions to use for hit ratio computation (for multi-class only,
     *                          0 to disable)
     *   @param ntrees Number of trees.
     *   @param max_depth Maximum tree depth.
     *   @param min_rows Fewest allowed (weighted) observations in a leaf.
     *   @param nbins For numerical columns (real/int), build a histogram of (at least) this many bins, then split at the
     *                best point
     *   @param nbins_top_level For numerical columns (real/int), build a histogram of (at most) this many bins at the
     *                          root level, then decrease by factor of two per level
     *   @param nbins_cats For categorical columns (factors), build a histogram of this many bins, then split at the best
     *                     point. Higher values can lead to more overfitting.
     *   @param r2_stopping r2_stopping is no longer supported and will be ignored if set - please use stopping_rounds,
     *                      stopping_metric and stopping_tolerance instead. Previous version of H2O would stop making
     *                      trees when the R^2 metric equals or exceeds this
     *   @param seed Seed for pseudo random number generator (if applicable)
     *   @param build_tree_one_node Run on one node only; no network overhead but fewer cpus used.  Suitable for small
     *                              datasets.
     *   @param sample_rate_per_class A list of row sample rates per class (relative fraction for each class, from 0.0 to
     *                                1.0), for each tree
     *   @param col_sample_rate_per_tree Column sample rate per tree (from 0.0 to 1.0)
     *   @param col_sample_rate_change_per_level Relative change of the column sampling rate for every level (must be &gt;
     *                                           0.0 and &lt;= 2.0)
     *   @param score_tree_interval Score the model after every so many trees. Disabled if set to 0.
     *   @param min_split_improvement Minimum relative improvement in squared error reduction for a split to happen
     *   @param histogram_type What type of histogram to use for finding optimal split points
     *   @param calibrate_model Use Platt Scaling to calculate calibrated class probabilities. Calibration can provide
     *                          more accurate estimates of class probabilities.
     *   @param calibration_frame Calibration frame for Platt Scaling
     *   @param check_constant_response Check if response column is constant. If enabled, then an exception is thrown if
     *                                  the response column is a constant value.If disabled, then model will train
     *                                  regardless of the response column being a constant value or not.
     *   @param model_id Destination id for this model; auto-generated if not specified.
     *   @param training_frame Id of the training data frame.
     *   @param validation_frame Id of the validation data frame.
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or &gt;= 2).
     *   @param keep_cross_validation_models Whether to keep the cross-validation models.
     *   @param keep_cross_validation_predictions Whether to keep the predictions of the cross-validation models.
     *   @param keep_cross_validation_fold_assignment Whether to keep the cross-validation fold assignment.
     *   @param parallelize_cross_validation Allow parallel training of cross-validation models
     *   @param distribution Distribution function
     *   @param tweedie_power Tweedie power for Tweedie regression, must be between 1 and 2.
     *   @param quantile_alpha Desired quantile for Quantile regression, must be between 0 and 1.
     *   @param huber_alpha Desired quantile for Huber/M-regression (threshold between quadratic and linear loss, must be
     *                      between 0 and 1).
     *   @param response_column Response variable column.
     *   @param weights_column Column with observation weights. Giving some observation a weight of zero is equivalent to
     *                         excluding it from the dataset; giving an observation a relative weight of 2 is equivalent
     *                         to repeating that row twice. Negative weights are not allowed. Note: Weights are per-row
     *                         observation weights and do not increase the size of the data frame. This is typically the
     *                         number of times a row is repeated, but non-integer values are supported as well. During
     *                         training, rows with higher weights matter more, due to the larger loss function pre-factor.
     *   @param offset_column Offset column. This will be added to the combination of columns before applying the link
     *                        function.
     *   @param fold_column Column with cross-validation fold index assignment per observation.
     *   @param fold_assignment Cross-validation fold assignment scheme, if fold_column is not specified. The 'Stratified'
     *                          option will stratify the folds based on the response variable, for classification
     *                          problems.
     *   @param categorical_encoding Encoding scheme for categorical features
     *   @param max_categorical_levels For every categorical feature, only use this many most frequent categorical levels
     *                                 for model training. Only used for categorical_encoding == EnumLimited.
     *   @param ignored_columns Names of columns to ignore for training.
     *   @param ignore_const_cols Ignore constant columns.
     *   @param score_each_iteration Whether to score during each iteration of model training.
     *   @param checkpoint Model checkpoint to resume training with.
     *   @param stopping_rounds Early stopping based on convergence of stopping_metric. Stop if simple moving average of
     *                          length k of the stopping_metric does not improve for k:=stopping_rounds scoring events (0
     *                          to disable)
     *   @param max_runtime_secs Maximum allowed runtime in seconds for model training. Use 0 to disable.
     *   @param stopping_metric Metric to use for early stopping (AUTO: logloss for classification, deviance for
     *                          regression and anonomaly_score for Isolation Forest). Note that custom and
     *                          custom_increasing can only be used in GBM and DRF with the Python client.
     *   @param stopping_tolerance Relative tolerance for metric-based stopping criterion (stop if relative improvement is
     *                             not at least this much)
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     */
    @FormUrlEncoded
    @POST("/99/Grid/isolationforest")
    Call<IsolationForestV3> trainIsolationforest(@Field("sample_size") long sample_size, @Field("sample_rate") double sample_rate,
            @Field("mtries") int mtries, @Field("balance_classes") boolean balance_classes,
            @Field("class_sampling_factors") float[] class_sampling_factors, @Field("max_after_balance_size") float max_after_balance_size,
            @Field("max_confusion_matrix_size") int max_confusion_matrix_size, @Field("max_hit_ratio_k") int max_hit_ratio_k,
            @Field("ntrees") int ntrees, @Field("max_depth") int max_depth, @Field("min_rows") double min_rows, @Field("nbins") int nbins,
            @Field("nbins_top_level") int nbins_top_level, @Field("nbins_cats") int nbins_cats, @Field("r2_stopping") double r2_stopping,
            @Field("seed") long seed, @Field("build_tree_one_node") boolean build_tree_one_node,
            @Field("sample_rate_per_class") double[] sample_rate_per_class,
            @Field("col_sample_rate_per_tree") double col_sample_rate_per_tree,
            @Field("col_sample_rate_change_per_level") double col_sample_rate_change_per_level,
            @Field("score_tree_interval") int score_tree_interval, @Field("min_split_improvement") double min_split_improvement,
            @Field("histogram_type") TreeSharedTreeModelSharedTreeParametersHistogramType histogram_type,
            @Field("calibrate_model") boolean calibrate_model, @Field("calibration_frame") String calibration_frame,
            @Field("check_constant_response") boolean check_constant_response, @Field("model_id") String model_id,
            @Field("training_frame") String training_frame, @Field("validation_frame") String validation_frame, @Field("nfolds") int nfolds,
            @Field("keep_cross_validation_models") boolean keep_cross_validation_models,
            @Field("keep_cross_validation_predictions") boolean keep_cross_validation_predictions,
            @Field("keep_cross_validation_fold_assignment") boolean keep_cross_validation_fold_assignment,
            @Field("parallelize_cross_validation") boolean parallelize_cross_validation,
            @Field("distribution") GenmodelutilsDistributionFamily distribution, @Field("tweedie_power") double tweedie_power,
            @Field("quantile_alpha") double quantile_alpha, @Field("huber_alpha") double huber_alpha,
            @Field("response_column") String response_column, @Field("weights_column") String weights_column,
            @Field("offset_column") String offset_column, @Field("fold_column") String fold_column,
            @Field("fold_assignment") ModelParametersFoldAssignmentScheme fold_assignment,
            @Field("categorical_encoding") ModelParametersCategoricalEncodingScheme categorical_encoding,
            @Field("max_categorical_levels") int max_categorical_levels, @Field("ignored_columns") String[] ignored_columns,
            @Field("ignore_const_cols") boolean ignore_const_cols, @Field("score_each_iteration") boolean score_each_iteration,
            @Field("checkpoint") String checkpoint, @Field("stopping_rounds") int stopping_rounds,
            @Field("max_runtime_secs") double max_runtime_secs, @Field("stopping_metric") ScoreKeeperStoppingMetric stopping_metric,
            @Field("stopping_tolerance") double stopping_tolerance, @Field("custom_metric_func") String custom_metric_func,
            @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir);

    @FormUrlEncoded
    @POST("/99/Grid/isolationforest")
    Call<IsolationForestV3> trainIsolationforest();

    /**
     * Run grid search for Aggregator model.
     *   @param transform Transformation of training data
     *   @param pca_method Method for computing PCA (Caution: GLRM is currently experimental and unstable)
     *   @param k Rank of matrix approximation
     *   @param max_iterations Maximum number of iterations for PCA
     *   @param target_num_exemplars Targeted number of exemplars
     *   @param rel_tol_num_exemplars Relative tolerance for number of exemplars (e.g, 0.5 is +/- 50 percents)
     *   @param seed RNG seed for initialization
     *   @param use_all_factor_levels Whether first factor level is included in each categorical expansion
     *   @param save_mapping_frame Whether to export the mapping of the aggregated frame
     *   @param num_iteration_without_new_exemplar The number of iterations to run before aggregator exits if the number
     *                                             of exemplars collected didn't change
     *   @param model_id Destination id for this model; auto-generated if not specified.
     *   @param training_frame Id of the training data frame.
     *   @param validation_frame Id of the validation data frame.
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or &gt;= 2).
     *   @param keep_cross_validation_models Whether to keep the cross-validation models.
     *   @param keep_cross_validation_predictions Whether to keep the predictions of the cross-validation models.
     *   @param keep_cross_validation_fold_assignment Whether to keep the cross-validation fold assignment.
     *   @param parallelize_cross_validation Allow parallel training of cross-validation models
     *   @param distribution Distribution function
     *   @param tweedie_power Tweedie power for Tweedie regression, must be between 1 and 2.
     *   @param quantile_alpha Desired quantile for Quantile regression, must be between 0 and 1.
     *   @param huber_alpha Desired quantile for Huber/M-regression (threshold between quadratic and linear loss, must be
     *                      between 0 and 1).
     *   @param response_column Response variable column.
     *   @param weights_column Column with observation weights. Giving some observation a weight of zero is equivalent to
     *                         excluding it from the dataset; giving an observation a relative weight of 2 is equivalent
     *                         to repeating that row twice. Negative weights are not allowed. Note: Weights are per-row
     *                         observation weights and do not increase the size of the data frame. This is typically the
     *                         number of times a row is repeated, but non-integer values are supported as well. During
     *                         training, rows with higher weights matter more, due to the larger loss function pre-factor.
     *   @param offset_column Offset column. This will be added to the combination of columns before applying the link
     *                        function.
     *   @param fold_column Column with cross-validation fold index assignment per observation.
     *   @param fold_assignment Cross-validation fold assignment scheme, if fold_column is not specified. The 'Stratified'
     *                          option will stratify the folds based on the response variable, for classification
     *                          problems.
     *   @param categorical_encoding Encoding scheme for categorical features
     *   @param max_categorical_levels For every categorical feature, only use this many most frequent categorical levels
     *                                 for model training. Only used for categorical_encoding == EnumLimited.
     *   @param ignored_columns Names of columns to ignore for training.
     *   @param ignore_const_cols Ignore constant columns.
     *   @param score_each_iteration Whether to score during each iteration of model training.
     *   @param checkpoint Model checkpoint to resume training with.
     *   @param stopping_rounds Early stopping based on convergence of stopping_metric. Stop if simple moving average of
     *                          length k of the stopping_metric does not improve for k:=stopping_rounds scoring events (0
     *                          to disable)
     *   @param max_runtime_secs Maximum allowed runtime in seconds for model training. Use 0 to disable.
     *   @param stopping_metric Metric to use for early stopping (AUTO: logloss for classification, deviance for
     *                          regression and anonomaly_score for Isolation Forest). Note that custom and
     *                          custom_increasing can only be used in GBM and DRF with the Python client.
     *   @param stopping_tolerance Relative tolerance for metric-based stopping criterion (stop if relative improvement is
     *                             not at least this much)
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     */
    @FormUrlEncoded
    @POST("/99/Grid/aggregator")
    Call<AggregatorV99> trainAggregator(@Field("transform") DataInfoTransformType transform, @Field("pca_method") PCAMethod pca_method,
            @Field("k") int k, @Field("max_iterations") int max_iterations, @Field("target_num_exemplars") int target_num_exemplars,
            @Field("rel_tol_num_exemplars") double rel_tol_num_exemplars, @Field("seed") long seed,
            @Field("use_all_factor_levels") boolean use_all_factor_levels, @Field("save_mapping_frame") boolean save_mapping_frame,
            @Field("num_iteration_without_new_exemplar") int num_iteration_without_new_exemplar, @Field("model_id") String model_id,
            @Field("training_frame") String training_frame, @Field("validation_frame") String validation_frame, @Field("nfolds") int nfolds,
            @Field("keep_cross_validation_models") boolean keep_cross_validation_models,
            @Field("keep_cross_validation_predictions") boolean keep_cross_validation_predictions,
            @Field("keep_cross_validation_fold_assignment") boolean keep_cross_validation_fold_assignment,
            @Field("parallelize_cross_validation") boolean parallelize_cross_validation,
            @Field("distribution") GenmodelutilsDistributionFamily distribution, @Field("tweedie_power") double tweedie_power,
            @Field("quantile_alpha") double quantile_alpha, @Field("huber_alpha") double huber_alpha,
            @Field("response_column") String response_column, @Field("weights_column") String weights_column,
            @Field("offset_column") String offset_column, @Field("fold_column") String fold_column,
            @Field("fold_assignment") ModelParametersFoldAssignmentScheme fold_assignment,
            @Field("categorical_encoding") ModelParametersCategoricalEncodingScheme categorical_encoding,
            @Field("max_categorical_levels") int max_categorical_levels, @Field("ignored_columns") String[] ignored_columns,
            @Field("ignore_const_cols") boolean ignore_const_cols, @Field("score_each_iteration") boolean score_each_iteration,
            @Field("checkpoint") String checkpoint, @Field("stopping_rounds") int stopping_rounds,
            @Field("max_runtime_secs") double max_runtime_secs, @Field("stopping_metric") ScoreKeeperStoppingMetric stopping_metric,
            @Field("stopping_tolerance") double stopping_tolerance, @Field("custom_metric_func") String custom_metric_func,
            @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir);

    @FormUrlEncoded
    @POST("/99/Grid/aggregator")
    Call<AggregatorV99> trainAggregator();

    /**
     * Run grid search for DeepWater model.
     *   @param problem_type Problem type, auto-detected by default. If set to image, the H2OFrame must contain a string
     *                       column containing the path (URI or URL) to the images in the first column. If set to text,
     *                       the H2OFrame must contain a string column containing the text in the first column. If set to
     *                       dataset, Deep Water behaves just like any other H2O Model and builds a model on the provided
     *                       H2OFrame (non-String columns).
     *   @param activation Activation function. Only used if no user-defined network architecture file is provided, and
     *                     only for problem_type=dataset.
     *   @param hidden Hidden layer sizes (e.g. [200, 200]). Only used if no user-defined network architecture file is
     *                 provided, and only for problem_type=dataset.
     *   @param input_dropout_ratio Input layer dropout ratio (can improve generalization, try 0.1 or 0.2).
     *   @param hidden_dropout_ratios Hidden layer dropout ratios (can improve generalization), specify one value per
     *                                hidden layer, defaults to 0.5.
     *   @param max_confusion_matrix_size [Deprecated] Maximum size (# classes) for confusion matrices to be printed in
     *                                    the Logs.
     *   @param sparse Sparse data handling (more efficient for data with lots of 0 values).
     *   @param max_hit_ratio_k Max. number (top K) of predictions to use for hit ratio computation (for multi-class only,
     *                          0 to disable).
     *   @param epochs How many times the dataset should be iterated (streamed), can be fractional.
     *   @param train_samples_per_iteration Number of training samples (globally) per MapReduce iteration. Special values
     *                                      are 0: one epoch, -1: all available data (e.g., replicated training data), -2:
     *                                      automatic.
     *   @param target_ratio_comm_to_comp Target ratio of communication overhead to computation. Only for multi-node
     *                                    operation and train_samples_per_iteration = -2 (auto-tuning).
     *   @param seed Seed for random numbers (affects sampling) - Note: only reproducible when running single threaded.
     *   @param learning_rate Learning rate (higher =&gt; less stable, lower =&gt; slower convergence).
     *   @param learning_rate_annealing Learning rate annealing: rate / (1 + rate_annealing * samples).
     *   @param momentum_start Initial momentum at the beginning of training (try 0.5).
     *   @param momentum_ramp Number of training samples for which momentum increases.
     *   @param momentum_stable Final momentum after the ramp is over (try 0.99).
     *   @param score_interval Shortest time interval (in seconds) between model scoring.
     *   @param score_training_samples Number of training set samples for scoring (0 for all).
     *   @param score_validation_samples Number of validation set samples for scoring (0 for all).
     *   @param score_duty_cycle Maximum duty cycle fraction for scoring (lower: more training, higher: more scoring).
     *   @param classification_stop Stopping criterion for classification error fraction on training data (-1 to disable).
     *   @param regression_stop Stopping criterion for regression error (MSE) on training data (-1 to disable).
     *   @param quiet_mode Enable quiet mode for less output to standard output.
     *   @param overwrite_with_best_model If enabled, override the final model with the best model found during training.
     *   @param autoencoder Auto-Encoder.
     *   @param diagnostics Enable diagnostics for hidden layers.
     *   @param variable_importances Compute variable importances for input features (Gedeon method) - can be slow for
     *                               large networks.
     *   @param replicate_training_data Replicate the entire training dataset onto every node for faster training on small
     *                                  datasets.
     *   @param single_node_mode Run on a single node for fine-tuning of model parameters.
     *   @param shuffle_training_data Enable global shuffling of training data.
     *   @param mini_batch_size Mini-batch size (smaller leads to better fit, larger can speed up and generalize better).
     *   @param clip_gradient Clip gradients once their absolute value is larger than this value.
     *   @param network Network architecture.
     *   @param backend Deep Learning Backend.
     *   @param image_shape Width and height of image.
     *   @param channels Number of (color) channels.
     *   @param gpu Whether to use a GPU (if available).
     *   @param device_id Device IDs (which GPUs to use).
     *   @param cache_data Whether to cache the data in memory (automatically disabled if data size is too large).
     *   @param network_definition_file Path of file containing network definition (graph, architecture).
     *   @param network_parameters_file Path of file containing network (initial) parameters (weights, biases).
     *   @param mean_image_file Path of file containing the mean image data for data normalization.
     *   @param export_native_parameters_prefix Path (prefix) where to export the native model parameters after every
     *                                          iteration.
     *   @param standardize If enabled, automatically standardize the data. If disabled, the user must provide properly
     *                      scaled input data.
     *   @param balance_classes Balance training data class counts via over/under-sampling (for imbalanced data).
     *   @param class_sampling_factors Desired over/under-sampling ratios per class (in lexicographic order). If not
     *                                 specified, sampling factors will be automatically computed to obtain class balance
     *                                 during training. Requires balance_classes.
     *   @param max_after_balance_size Maximum relative size of the training data after balancing class counts (can be
     *                                 less than 1.0). Requires balance_classes.
     *   @param model_id Destination id for this model; auto-generated if not specified.
     *   @param training_frame Id of the training data frame.
     *   @param validation_frame Id of the validation data frame.
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or &gt;= 2).
     *   @param keep_cross_validation_models Whether to keep the cross-validation models.
     *   @param keep_cross_validation_predictions Whether to keep the predictions of the cross-validation models.
     *   @param keep_cross_validation_fold_assignment Whether to keep the cross-validation fold assignment.
     *   @param parallelize_cross_validation Allow parallel training of cross-validation models
     *   @param distribution Distribution function
     *   @param tweedie_power Tweedie power for Tweedie regression, must be between 1 and 2.
     *   @param quantile_alpha Desired quantile for Quantile regression, must be between 0 and 1.
     *   @param huber_alpha Desired quantile for Huber/M-regression (threshold between quadratic and linear loss, must be
     *                      between 0 and 1).
     *   @param response_column Response variable column.
     *   @param weights_column Column with observation weights. Giving some observation a weight of zero is equivalent to
     *                         excluding it from the dataset; giving an observation a relative weight of 2 is equivalent
     *                         to repeating that row twice. Negative weights are not allowed. Note: Weights are per-row
     *                         observation weights and do not increase the size of the data frame. This is typically the
     *                         number of times a row is repeated, but non-integer values are supported as well. During
     *                         training, rows with higher weights matter more, due to the larger loss function pre-factor.
     *   @param offset_column Offset column. This will be added to the combination of columns before applying the link
     *                        function.
     *   @param fold_column Column with cross-validation fold index assignment per observation.
     *   @param fold_assignment Cross-validation fold assignment scheme, if fold_column is not specified. The 'Stratified'
     *                          option will stratify the folds based on the response variable, for classification
     *                          problems.
     *   @param categorical_encoding Encoding scheme for categorical features
     *   @param max_categorical_levels For every categorical feature, only use this many most frequent categorical levels
     *                                 for model training. Only used for categorical_encoding == EnumLimited.
     *   @param ignored_columns Names of columns to ignore for training.
     *   @param ignore_const_cols Ignore constant columns.
     *   @param score_each_iteration Whether to score during each iteration of model training.
     *   @param checkpoint Model checkpoint to resume training with.
     *   @param stopping_rounds Early stopping based on convergence of stopping_metric. Stop if simple moving average of
     *                          length k of the stopping_metric does not improve for k:=stopping_rounds scoring events (0
     *                          to disable)
     *   @param max_runtime_secs Maximum allowed runtime in seconds for model training. Use 0 to disable.
     *   @param stopping_metric Metric to use for early stopping (AUTO: logloss for classification, deviance for
     *                          regression and anonomaly_score for Isolation Forest). Note that custom and
     *                          custom_increasing can only be used in GBM and DRF with the Python client.
     *   @param stopping_tolerance Relative tolerance for metric-based stopping criterion (stop if relative improvement is
     *                             not at least this much)
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     */
    @FormUrlEncoded
    @POST("/99/Grid/deepwater")
    Call<DeepWaterV3> trainDeepwater(@Field("problem_type") DeepWaterParametersProblemType problem_type,
            @Field("activation") DeepWaterParametersActivation activation, @Field("hidden") int[] hidden,
            @Field("input_dropout_ratio") double input_dropout_ratio, @Field("hidden_dropout_ratios") double[] hidden_dropout_ratios,
            @Field("max_confusion_matrix_size") int max_confusion_matrix_size, @Field("sparse") boolean sparse,
            @Field("max_hit_ratio_k") int max_hit_ratio_k, @Field("epochs") double epochs,
            @Field("train_samples_per_iteration") long train_samples_per_iteration,
            @Field("target_ratio_comm_to_comp") double target_ratio_comm_to_comp, @Field("seed") long seed,
            @Field("learning_rate") double learning_rate, @Field("learning_rate_annealing") double learning_rate_annealing,
            @Field("momentum_start") double momentum_start, @Field("momentum_ramp") double momentum_ramp,
            @Field("momentum_stable") double momentum_stable, @Field("score_interval") double score_interval,
            @Field("score_training_samples") long score_training_samples, @Field("score_validation_samples") long score_validation_samples,
            @Field("score_duty_cycle") double score_duty_cycle, @Field("classification_stop") double classification_stop,
            @Field("regression_stop") double regression_stop, @Field("quiet_mode") boolean quiet_mode,
            @Field("overwrite_with_best_model") boolean overwrite_with_best_model, @Field("autoencoder") boolean autoencoder,
            @Field("diagnostics") boolean diagnostics, @Field("variable_importances") boolean variable_importances,
            @Field("replicate_training_data") boolean replicate_training_data, @Field("single_node_mode") boolean single_node_mode,
            @Field("shuffle_training_data") boolean shuffle_training_data, @Field("mini_batch_size") int mini_batch_size,
            @Field("clip_gradient") double clip_gradient, @Field("network") DeepWaterParametersNetwork network,
            @Field("backend") DeepWaterParametersBackend backend, @Field("image_shape") int[] image_shape, @Field("channels") int channels,
            @Field("gpu") boolean gpu, @Field("device_id") int[] device_id, @Field("cache_data") boolean cache_data,
            @Field("network_definition_file") String network_definition_file,
            @Field("network_parameters_file") String network_parameters_file, @Field("mean_image_file") String mean_image_file,
            @Field("export_native_parameters_prefix") String export_native_parameters_prefix, @Field("standardize") boolean standardize,
            @Field("balance_classes") boolean balance_classes, @Field("class_sampling_factors") float[] class_sampling_factors,
            @Field("max_after_balance_size") float max_after_balance_size, @Field("model_id") String model_id,
            @Field("training_frame") String training_frame, @Field("validation_frame") String validation_frame, @Field("nfolds") int nfolds,
            @Field("keep_cross_validation_models") boolean keep_cross_validation_models,
            @Field("keep_cross_validation_predictions") boolean keep_cross_validation_predictions,
            @Field("keep_cross_validation_fold_assignment") boolean keep_cross_validation_fold_assignment,
            @Field("parallelize_cross_validation") boolean parallelize_cross_validation,
            @Field("distribution") GenmodelutilsDistributionFamily distribution, @Field("tweedie_power") double tweedie_power,
            @Field("quantile_alpha") double quantile_alpha, @Field("huber_alpha") double huber_alpha,
            @Field("response_column") String response_column, @Field("weights_column") String weights_column,
            @Field("offset_column") String offset_column, @Field("fold_column") String fold_column,
            @Field("fold_assignment") ModelParametersFoldAssignmentScheme fold_assignment,
            @Field("categorical_encoding") ModelParametersCategoricalEncodingScheme categorical_encoding,
            @Field("max_categorical_levels") int max_categorical_levels, @Field("ignored_columns") String[] ignored_columns,
            @Field("ignore_const_cols") boolean ignore_const_cols, @Field("score_each_iteration") boolean score_each_iteration,
            @Field("checkpoint") String checkpoint, @Field("stopping_rounds") int stopping_rounds,
            @Field("max_runtime_secs") double max_runtime_secs, @Field("stopping_metric") ScoreKeeperStoppingMetric stopping_metric,
            @Field("stopping_tolerance") double stopping_tolerance, @Field("custom_metric_func") String custom_metric_func,
            @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir);

    @FormUrlEncoded
    @POST("/99/Grid/deepwater")
    Call<DeepWaterV3> trainDeepwater();

    /**
     * Run grid search for Word2Vec model.
     *   @param vec_size Set size of word vectors
     *   @param window_size Set max skip length between words
     *   @param sent_sample_rate Set threshold for occurrence of words. Those that appear with higher frequency in the
     *                           training data                 will be randomly down-sampled; useful range is (0, 1e-5)
     *   @param norm_model Use Hierarchical Softmax
     *   @param epochs Number of training iterations to run
     *   @param min_word_freq This will discard words that appear less than &lt;int&gt; times
     *   @param init_learning_rate Set the starting learning rate
     *   @param word_model Use the Skip-Gram model
     *   @param pre_trained Id of a data frame that contains a pre-trained (external) word2vec model
     *   @param model_id Destination id for this model; auto-generated if not specified.
     *   @param training_frame Id of the training data frame.
     *   @param validation_frame Id of the validation data frame.
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or &gt;= 2).
     *   @param keep_cross_validation_models Whether to keep the cross-validation models.
     *   @param keep_cross_validation_predictions Whether to keep the predictions of the cross-validation models.
     *   @param keep_cross_validation_fold_assignment Whether to keep the cross-validation fold assignment.
     *   @param parallelize_cross_validation Allow parallel training of cross-validation models
     *   @param distribution Distribution function
     *   @param tweedie_power Tweedie power for Tweedie regression, must be between 1 and 2.
     *   @param quantile_alpha Desired quantile for Quantile regression, must be between 0 and 1.
     *   @param huber_alpha Desired quantile for Huber/M-regression (threshold between quadratic and linear loss, must be
     *                      between 0 and 1).
     *   @param response_column Response variable column.
     *   @param weights_column Column with observation weights. Giving some observation a weight of zero is equivalent to
     *                         excluding it from the dataset; giving an observation a relative weight of 2 is equivalent
     *                         to repeating that row twice. Negative weights are not allowed. Note: Weights are per-row
     *                         observation weights and do not increase the size of the data frame. This is typically the
     *                         number of times a row is repeated, but non-integer values are supported as well. During
     *                         training, rows with higher weights matter more, due to the larger loss function pre-factor.
     *   @param offset_column Offset column. This will be added to the combination of columns before applying the link
     *                        function.
     *   @param fold_column Column with cross-validation fold index assignment per observation.
     *   @param fold_assignment Cross-validation fold assignment scheme, if fold_column is not specified. The 'Stratified'
     *                          option will stratify the folds based on the response variable, for classification
     *                          problems.
     *   @param categorical_encoding Encoding scheme for categorical features
     *   @param max_categorical_levels For every categorical feature, only use this many most frequent categorical levels
     *                                 for model training. Only used for categorical_encoding == EnumLimited.
     *   @param ignored_columns Names of columns to ignore for training.
     *   @param ignore_const_cols Ignore constant columns.
     *   @param score_each_iteration Whether to score during each iteration of model training.
     *   @param checkpoint Model checkpoint to resume training with.
     *   @param stopping_rounds Early stopping based on convergence of stopping_metric. Stop if simple moving average of
     *                          length k of the stopping_metric does not improve for k:=stopping_rounds scoring events (0
     *                          to disable)
     *   @param max_runtime_secs Maximum allowed runtime in seconds for model training. Use 0 to disable.
     *   @param stopping_metric Metric to use for early stopping (AUTO: logloss for classification, deviance for
     *                          regression and anonomaly_score for Isolation Forest). Note that custom and
     *                          custom_increasing can only be used in GBM and DRF with the Python client.
     *   @param stopping_tolerance Relative tolerance for metric-based stopping criterion (stop if relative improvement is
     *                             not at least this much)
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     */
    @FormUrlEncoded
    @POST("/99/Grid/word2vec")
    Call<Word2VecV3> trainWord2vec(@Field("vec_size") int vec_size, @Field("window_size") int window_size,
            @Field("sent_sample_rate") float sent_sample_rate, @Field("norm_model") Word2VecNormModel norm_model,
            @Field("epochs") int epochs, @Field("min_word_freq") int min_word_freq, @Field("init_learning_rate") float init_learning_rate,
            @Field("word_model") Word2VecWordModel word_model, @Field("pre_trained") String pre_trained, @Field("model_id") String model_id,
            @Field("training_frame") String training_frame, @Field("validation_frame") String validation_frame, @Field("nfolds") int nfolds,
            @Field("keep_cross_validation_models") boolean keep_cross_validation_models,
            @Field("keep_cross_validation_predictions") boolean keep_cross_validation_predictions,
            @Field("keep_cross_validation_fold_assignment") boolean keep_cross_validation_fold_assignment,
            @Field("parallelize_cross_validation") boolean parallelize_cross_validation,
            @Field("distribution") GenmodelutilsDistributionFamily distribution, @Field("tweedie_power") double tweedie_power,
            @Field("quantile_alpha") double quantile_alpha, @Field("huber_alpha") double huber_alpha,
            @Field("response_column") String response_column, @Field("weights_column") String weights_column,
            @Field("offset_column") String offset_column, @Field("fold_column") String fold_column,
            @Field("fold_assignment") ModelParametersFoldAssignmentScheme fold_assignment,
            @Field("categorical_encoding") ModelParametersCategoricalEncodingScheme categorical_encoding,
            @Field("max_categorical_levels") int max_categorical_levels, @Field("ignored_columns") String[] ignored_columns,
            @Field("ignore_const_cols") boolean ignore_const_cols, @Field("score_each_iteration") boolean score_each_iteration,
            @Field("checkpoint") String checkpoint, @Field("stopping_rounds") int stopping_rounds,
            @Field("max_runtime_secs") double max_runtime_secs, @Field("stopping_metric") ScoreKeeperStoppingMetric stopping_metric,
            @Field("stopping_tolerance") double stopping_tolerance, @Field("custom_metric_func") String custom_metric_func,
            @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir);

    @FormUrlEncoded
    @POST("/99/Grid/word2vec")
    Call<Word2VecV3> trainWord2vec();

    /**
     * Run grid search for StackedEnsemble model.
     *   @param base_models List of models (or model ids) to ensemble/stack together. If not using blending frame, then
     *                      models must have been cross-validated using nfolds &gt; 1, and folds must be identical across
     *                      models.
     *   @param metalearner_algorithm Type of algorithm to use as the metalearner. Options include 'AUTO' (GLM with non
     *                                negative weights; if validation_frame is present, a lambda search is performed),
     *                                'glm' (GLM with default parameters), 'gbm' (GBM with default parameters), 'drf'
     *                                (Random Forest with default parameters), or 'deeplearning' (Deep Learning with
     *                                default parameters).
     *   @param metalearner_nfolds Number of folds for K-fold cross-validation of the metalearner algorithm (0 to disable
     *                             or &gt;= 2).
     *   @param metalearner_fold_assignment Cross-validation fold assignment scheme for metalearner cross-validation.
     *                                      Defaults to AUTO (which is currently set to Random). The 'Stratified' option
     *                                      will stratify the folds based on the response variable, for classification
     *                                      problems.
     *   @param metalearner_fold_column Column with cross-validation fold index assignment per observation for cross-
     *                                  validation of the metalearner.
     *   @param keep_levelone_frame Keep level one frame used for metalearner training.
     *   @param metalearner_params Parameters for metalearner algorithm
     *   @param blending_frame Frame used to compute the predictions that serve as the training frame for the metalearner
     *                         (triggers blending mode if provided)
     *   @param seed Seed for random numbers; passed through to the metalearner algorithm. Defaults to -1 (time-based
     *               random number)
     *   @param model_id Destination id for this model; auto-generated if not specified.
     *   @param training_frame Id of the training data frame.
     *   @param validation_frame Id of the validation data frame.
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or &gt;= 2).
     *   @param keep_cross_validation_models Whether to keep the cross-validation models.
     *   @param keep_cross_validation_predictions Whether to keep the predictions of the cross-validation models.
     *   @param keep_cross_validation_fold_assignment Whether to keep the cross-validation fold assignment.
     *   @param parallelize_cross_validation Allow parallel training of cross-validation models
     *   @param distribution Distribution function
     *   @param tweedie_power Tweedie power for Tweedie regression, must be between 1 and 2.
     *   @param quantile_alpha Desired quantile for Quantile regression, must be between 0 and 1.
     *   @param huber_alpha Desired quantile for Huber/M-regression (threshold between quadratic and linear loss, must be
     *                      between 0 and 1).
     *   @param response_column Response variable column.
     *   @param weights_column Column with observation weights. Giving some observation a weight of zero is equivalent to
     *                         excluding it from the dataset; giving an observation a relative weight of 2 is equivalent
     *                         to repeating that row twice. Negative weights are not allowed. Note: Weights are per-row
     *                         observation weights and do not increase the size of the data frame. This is typically the
     *                         number of times a row is repeated, but non-integer values are supported as well. During
     *                         training, rows with higher weights matter more, due to the larger loss function pre-factor.
     *   @param offset_column Offset column. This will be added to the combination of columns before applying the link
     *                        function.
     *   @param fold_column Column with cross-validation fold index assignment per observation.
     *   @param fold_assignment Cross-validation fold assignment scheme, if fold_column is not specified. The 'Stratified'
     *                          option will stratify the folds based on the response variable, for classification
     *                          problems.
     *   @param categorical_encoding Encoding scheme for categorical features
     *   @param max_categorical_levels For every categorical feature, only use this many most frequent categorical levels
     *                                 for model training. Only used for categorical_encoding == EnumLimited.
     *   @param ignored_columns Names of columns to ignore for training.
     *   @param ignore_const_cols Ignore constant columns.
     *   @param score_each_iteration Whether to score during each iteration of model training.
     *   @param checkpoint Model checkpoint to resume training with.
     *   @param stopping_rounds Early stopping based on convergence of stopping_metric. Stop if simple moving average of
     *                          length k of the stopping_metric does not improve for k:=stopping_rounds scoring events (0
     *                          to disable)
     *   @param max_runtime_secs Maximum allowed runtime in seconds for model training. Use 0 to disable.
     *   @param stopping_metric Metric to use for early stopping (AUTO: logloss for classification, deviance for
     *                          regression and anonomaly_score for Isolation Forest). Note that custom and
     *                          custom_increasing can only be used in GBM and DRF with the Python client.
     *   @param stopping_tolerance Relative tolerance for metric-based stopping criterion (stop if relative improvement is
     *                             not at least this much)
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     */
    @FormUrlEncoded
    @POST("/99/Grid/stackedensemble")
    Call<StackedEnsembleV99> trainStackedensemble(@Field("base_models") String[] base_models,
            @Field("metalearner_algorithm") EnsembleMetalearnerAlgorithm metalearner_algorithm,
            @Field("metalearner_nfolds") int metalearner_nfolds,
            @Field("metalearner_fold_assignment") ModelParametersFoldAssignmentScheme metalearner_fold_assignment,
            @Field("metalearner_fold_column") String metalearner_fold_column, @Field("keep_levelone_frame") boolean keep_levelone_frame,
            @Field("metalearner_params") String metalearner_params, @Field("blending_frame") String blending_frame,
            @Field("seed") long seed, @Field("model_id") String model_id, @Field("training_frame") String training_frame,
            @Field("validation_frame") String validation_frame, @Field("nfolds") int nfolds,
            @Field("keep_cross_validation_models") boolean keep_cross_validation_models,
            @Field("keep_cross_validation_predictions") boolean keep_cross_validation_predictions,
            @Field("keep_cross_validation_fold_assignment") boolean keep_cross_validation_fold_assignment,
            @Field("parallelize_cross_validation") boolean parallelize_cross_validation,
            @Field("distribution") GenmodelutilsDistributionFamily distribution, @Field("tweedie_power") double tweedie_power,
            @Field("quantile_alpha") double quantile_alpha, @Field("huber_alpha") double huber_alpha,
            @Field("response_column") String response_column, @Field("weights_column") String weights_column,
            @Field("offset_column") String offset_column, @Field("fold_column") String fold_column,
            @Field("fold_assignment") ModelParametersFoldAssignmentScheme fold_assignment,
            @Field("categorical_encoding") ModelParametersCategoricalEncodingScheme categorical_encoding,
            @Field("max_categorical_levels") int max_categorical_levels, @Field("ignored_columns") String[] ignored_columns,
            @Field("ignore_const_cols") boolean ignore_const_cols, @Field("score_each_iteration") boolean score_each_iteration,
            @Field("checkpoint") String checkpoint, @Field("stopping_rounds") int stopping_rounds,
            @Field("max_runtime_secs") double max_runtime_secs, @Field("stopping_metric") ScoreKeeperStoppingMetric stopping_metric,
            @Field("stopping_tolerance") double stopping_tolerance, @Field("custom_metric_func") String custom_metric_func,
            @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir);

    @FormUrlEncoded
    @POST("/99/Grid/stackedensemble")
    Call<StackedEnsembleV99> trainStackedensemble(@Field("base_models") String[] base_models);

    /**
     * Run grid search for CoxPH model.
     *   @param start_column Start Time Column.
     *   @param stop_column Stop Time Column.
     *   @param stratify_by List of columns to use for stratification.
     *   @param ties Method for Handling Ties.
     *   @param init Coefficient starting value.
     *   @param lre_min Minimum log-relative error.
     *   @param max_iterations Maximum number of iterations.
     *   @param interactions_only A list of columns that should only be used to create interactions but should not itself
     *                            participate in model training.
     *   @param interactions A list of predictor column indices to interact. All pairwise combinations will be computed
     *                       for the list.
     *   @param interaction_pairs A list of pairwise (first order) column interactions.
     *   @param use_all_factor_levels (Internal. For development only!) Indicates whether to use all factor levels.
     *   @param model_id Destination id for this model; auto-generated if not specified.
     *   @param training_frame Id of the training data frame.
     *   @param validation_frame Id of the validation data frame.
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or &gt;= 2).
     *   @param keep_cross_validation_models Whether to keep the cross-validation models.
     *   @param keep_cross_validation_predictions Whether to keep the predictions of the cross-validation models.
     *   @param keep_cross_validation_fold_assignment Whether to keep the cross-validation fold assignment.
     *   @param parallelize_cross_validation Allow parallel training of cross-validation models
     *   @param distribution Distribution function
     *   @param tweedie_power Tweedie power for Tweedie regression, must be between 1 and 2.
     *   @param quantile_alpha Desired quantile for Quantile regression, must be between 0 and 1.
     *   @param huber_alpha Desired quantile for Huber/M-regression (threshold between quadratic and linear loss, must be
     *                      between 0 and 1).
     *   @param response_column Response variable column.
     *   @param weights_column Column with observation weights. Giving some observation a weight of zero is equivalent to
     *                         excluding it from the dataset; giving an observation a relative weight of 2 is equivalent
     *                         to repeating that row twice. Negative weights are not allowed. Note: Weights are per-row
     *                         observation weights and do not increase the size of the data frame. This is typically the
     *                         number of times a row is repeated, but non-integer values are supported as well. During
     *                         training, rows with higher weights matter more, due to the larger loss function pre-factor.
     *   @param offset_column Offset column. This will be added to the combination of columns before applying the link
     *                        function.
     *   @param fold_column Column with cross-validation fold index assignment per observation.
     *   @param fold_assignment Cross-validation fold assignment scheme, if fold_column is not specified. The 'Stratified'
     *                          option will stratify the folds based on the response variable, for classification
     *                          problems.
     *   @param categorical_encoding Encoding scheme for categorical features
     *   @param max_categorical_levels For every categorical feature, only use this many most frequent categorical levels
     *                                 for model training. Only used for categorical_encoding == EnumLimited.
     *   @param ignored_columns Names of columns to ignore for training.
     *   @param ignore_const_cols Ignore constant columns.
     *   @param score_each_iteration Whether to score during each iteration of model training.
     *   @param checkpoint Model checkpoint to resume training with.
     *   @param stopping_rounds Early stopping based on convergence of stopping_metric. Stop if simple moving average of
     *                          length k of the stopping_metric does not improve for k:=stopping_rounds scoring events (0
     *                          to disable)
     *   @param max_runtime_secs Maximum allowed runtime in seconds for model training. Use 0 to disable.
     *   @param stopping_metric Metric to use for early stopping (AUTO: logloss for classification, deviance for
     *                          regression and anonomaly_score for Isolation Forest). Note that custom and
     *                          custom_increasing can only be used in GBM and DRF with the Python client.
     *   @param stopping_tolerance Relative tolerance for metric-based stopping criterion (stop if relative improvement is
     *                             not at least this much)
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     */
    @FormUrlEncoded
    @POST("/99/Grid/coxph")
    Call<CoxPHV3> trainCoxph(@Field("start_column") String start_column, @Field("stop_column") String stop_column,
            @Field("stratify_by") String[] stratify_by, @Field("ties") CoxPHTies ties, @Field("init") double init,
            @Field("lre_min") double lre_min, @Field("max_iterations") int max_iterations,
            @Field("interactions_only") String[] interactions_only, @Field("interactions") String[] interactions,
            @Field("interaction_pairs") StringPairV3[] interaction_pairs, @Field("use_all_factor_levels") boolean use_all_factor_levels,
            @Field("model_id") String model_id, @Field("training_frame") String training_frame,
            @Field("validation_frame") String validation_frame, @Field("nfolds") int nfolds,
            @Field("keep_cross_validation_models") boolean keep_cross_validation_models,
            @Field("keep_cross_validation_predictions") boolean keep_cross_validation_predictions,
            @Field("keep_cross_validation_fold_assignment") boolean keep_cross_validation_fold_assignment,
            @Field("parallelize_cross_validation") boolean parallelize_cross_validation,
            @Field("distribution") GenmodelutilsDistributionFamily distribution, @Field("tweedie_power") double tweedie_power,
            @Field("quantile_alpha") double quantile_alpha, @Field("huber_alpha") double huber_alpha,
            @Field("response_column") String response_column, @Field("weights_column") String weights_column,
            @Field("offset_column") String offset_column, @Field("fold_column") String fold_column,
            @Field("fold_assignment") ModelParametersFoldAssignmentScheme fold_assignment,
            @Field("categorical_encoding") ModelParametersCategoricalEncodingScheme categorical_encoding,
            @Field("max_categorical_levels") int max_categorical_levels, @Field("ignored_columns") String[] ignored_columns,
            @Field("ignore_const_cols") boolean ignore_const_cols, @Field("score_each_iteration") boolean score_each_iteration,
            @Field("checkpoint") String checkpoint, @Field("stopping_rounds") int stopping_rounds,
            @Field("max_runtime_secs") double max_runtime_secs, @Field("stopping_metric") ScoreKeeperStoppingMetric stopping_metric,
            @Field("stopping_tolerance") double stopping_tolerance, @Field("custom_metric_func") String custom_metric_func,
            @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir);

    @FormUrlEncoded
    @POST("/99/Grid/coxph")
    Call<CoxPHV3> trainCoxph();

    /**
     * Run grid search for Generic model.
     *   @param path Path to file with self-contained model archive.
     *   @param model_key Key to the self-contained model archive already uploaded to H2O.
     *   @param model_id Destination id for this model; auto-generated if not specified.
     *   @param training_frame Id of the training data frame.
     *   @param validation_frame Id of the validation data frame.
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or &gt;= 2).
     *   @param keep_cross_validation_models Whether to keep the cross-validation models.
     *   @param keep_cross_validation_predictions Whether to keep the predictions of the cross-validation models.
     *   @param keep_cross_validation_fold_assignment Whether to keep the cross-validation fold assignment.
     *   @param parallelize_cross_validation Allow parallel training of cross-validation models
     *   @param distribution Distribution function
     *   @param tweedie_power Tweedie power for Tweedie regression, must be between 1 and 2.
     *   @param quantile_alpha Desired quantile for Quantile regression, must be between 0 and 1.
     *   @param huber_alpha Desired quantile for Huber/M-regression (threshold between quadratic and linear loss, must be
     *                      between 0 and 1).
     *   @param response_column Response variable column.
     *   @param weights_column Column with observation weights. Giving some observation a weight of zero is equivalent to
     *                         excluding it from the dataset; giving an observation a relative weight of 2 is equivalent
     *                         to repeating that row twice. Negative weights are not allowed. Note: Weights are per-row
     *                         observation weights and do not increase the size of the data frame. This is typically the
     *                         number of times a row is repeated, but non-integer values are supported as well. During
     *                         training, rows with higher weights matter more, due to the larger loss function pre-factor.
     *   @param offset_column Offset column. This will be added to the combination of columns before applying the link
     *                        function.
     *   @param fold_column Column with cross-validation fold index assignment per observation.
     *   @param fold_assignment Cross-validation fold assignment scheme, if fold_column is not specified. The 'Stratified'
     *                          option will stratify the folds based on the response variable, for classification
     *                          problems.
     *   @param categorical_encoding Encoding scheme for categorical features
     *   @param max_categorical_levels For every categorical feature, only use this many most frequent categorical levels
     *                                 for model training. Only used for categorical_encoding == EnumLimited.
     *   @param ignored_columns Names of columns to ignore for training.
     *   @param ignore_const_cols Ignore constant columns.
     *   @param score_each_iteration Whether to score during each iteration of model training.
     *   @param checkpoint Model checkpoint to resume training with.
     *   @param stopping_rounds Early stopping based on convergence of stopping_metric. Stop if simple moving average of
     *                          length k of the stopping_metric does not improve for k:=stopping_rounds scoring events (0
     *                          to disable)
     *   @param max_runtime_secs Maximum allowed runtime in seconds for model training. Use 0 to disable.
     *   @param stopping_metric Metric to use for early stopping (AUTO: logloss for classification, deviance for
     *                          regression and anonomaly_score for Isolation Forest). Note that custom and
     *                          custom_increasing can only be used in GBM and DRF with the Python client.
     *   @param stopping_tolerance Relative tolerance for metric-based stopping criterion (stop if relative improvement is
     *                             not at least this much)
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     */
    @FormUrlEncoded
    @POST("/99/Grid/generic")
    Call<GenericV3> trainGeneric(@Field("path") String path, @Field("model_key") String model_key, @Field("model_id") String model_id,
            @Field("training_frame") String training_frame, @Field("validation_frame") String validation_frame, @Field("nfolds") int nfolds,
            @Field("keep_cross_validation_models") boolean keep_cross_validation_models,
            @Field("keep_cross_validation_predictions") boolean keep_cross_validation_predictions,
            @Field("keep_cross_validation_fold_assignment") boolean keep_cross_validation_fold_assignment,
            @Field("parallelize_cross_validation") boolean parallelize_cross_validation,
            @Field("distribution") GenmodelutilsDistributionFamily distribution, @Field("tweedie_power") double tweedie_power,
            @Field("quantile_alpha") double quantile_alpha, @Field("huber_alpha") double huber_alpha,
            @Field("response_column") String response_column, @Field("weights_column") String weights_column,
            @Field("offset_column") String offset_column, @Field("fold_column") String fold_column,
            @Field("fold_assignment") ModelParametersFoldAssignmentScheme fold_assignment,
            @Field("categorical_encoding") ModelParametersCategoricalEncodingScheme categorical_encoding,
            @Field("max_categorical_levels") int max_categorical_levels, @Field("ignored_columns") String[] ignored_columns,
            @Field("ignore_const_cols") boolean ignore_const_cols, @Field("score_each_iteration") boolean score_each_iteration,
            @Field("checkpoint") String checkpoint, @Field("stopping_rounds") int stopping_rounds,
            @Field("max_runtime_secs") double max_runtime_secs, @Field("stopping_metric") ScoreKeeperStoppingMetric stopping_metric,
            @Field("stopping_tolerance") double stopping_tolerance, @Field("custom_metric_func") String custom_metric_func,
            @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir);

    @FormUrlEncoded
    @POST("/99/Grid/generic")
    Call<GenericV3> trainGeneric();

    /**
     * Run grid search for PSVM model.
     *   @param hyper_param Penalty parameter C of the error term
     *   @param kernel_type Type of used kernel
     *   @param gamma Coefficient of the kernel (currently RBF gamma for gaussian kernel, -1 means 1/#features)
     *   @param rank_ratio Desired rank of the ICF matrix expressed as an ration of number of input rows (-1 means use
     *                     sqrt(#rows)).
     *   @param positive_weight Weight of positive (+1) class of observations
     *   @param negative_weight Weight of positive (-1) class of observations
     *   @param disable_training_metrics Disable calculating training metrics (expensive on large datasets)
     *   @param sv_threshold Threshold for accepting a candidate observation into the set of support vectors
     *   @param max_iterations Maximum number of iteration of the algorithm
     *   @param fact_threshold Convergence threshold of the Incomplete Cholesky Factorization (ICF)
     *   @param feasible_threshold Convergence threshold for primal-dual residuals in the IPM iteration
     *   @param surrogate_gap_threshold Feasibility criterion of the surrogate duality gap (eta)
     *   @param mu_factor Increasing factor mu
     *   @param seed Seed for pseudo random number generator (if applicable)
     *   @param model_id Destination id for this model; auto-generated if not specified.
     *   @param training_frame Id of the training data frame.
     *   @param validation_frame Id of the validation data frame.
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or &gt;= 2).
     *   @param keep_cross_validation_models Whether to keep the cross-validation models.
     *   @param keep_cross_validation_predictions Whether to keep the predictions of the cross-validation models.
     *   @param keep_cross_validation_fold_assignment Whether to keep the cross-validation fold assignment.
     *   @param parallelize_cross_validation Allow parallel training of cross-validation models
     *   @param distribution Distribution function
     *   @param tweedie_power Tweedie power for Tweedie regression, must be between 1 and 2.
     *   @param quantile_alpha Desired quantile for Quantile regression, must be between 0 and 1.
     *   @param huber_alpha Desired quantile for Huber/M-regression (threshold between quadratic and linear loss, must be
     *                      between 0 and 1).
     *   @param response_column Response variable column.
     *   @param weights_column Column with observation weights. Giving some observation a weight of zero is equivalent to
     *                         excluding it from the dataset; giving an observation a relative weight of 2 is equivalent
     *                         to repeating that row twice. Negative weights are not allowed. Note: Weights are per-row
     *                         observation weights and do not increase the size of the data frame. This is typically the
     *                         number of times a row is repeated, but non-integer values are supported as well. During
     *                         training, rows with higher weights matter more, due to the larger loss function pre-factor.
     *   @param offset_column Offset column. This will be added to the combination of columns before applying the link
     *                        function.
     *   @param fold_column Column with cross-validation fold index assignment per observation.
     *   @param fold_assignment Cross-validation fold assignment scheme, if fold_column is not specified. The 'Stratified'
     *                          option will stratify the folds based on the response variable, for classification
     *                          problems.
     *   @param categorical_encoding Encoding scheme for categorical features
     *   @param max_categorical_levels For every categorical feature, only use this many most frequent categorical levels
     *                                 for model training. Only used for categorical_encoding == EnumLimited.
     *   @param ignored_columns Names of columns to ignore for training.
     *   @param ignore_const_cols Ignore constant columns.
     *   @param score_each_iteration Whether to score during each iteration of model training.
     *   @param checkpoint Model checkpoint to resume training with.
     *   @param stopping_rounds Early stopping based on convergence of stopping_metric. Stop if simple moving average of
     *                          length k of the stopping_metric does not improve for k:=stopping_rounds scoring events (0
     *                          to disable)
     *   @param max_runtime_secs Maximum allowed runtime in seconds for model training. Use 0 to disable.
     *   @param stopping_metric Metric to use for early stopping (AUTO: logloss for classification, deviance for
     *                          regression and anonomaly_score for Isolation Forest). Note that custom and
     *                          custom_increasing can only be used in GBM and DRF with the Python client.
     *   @param stopping_tolerance Relative tolerance for metric-based stopping criterion (stop if relative improvement is
     *                             not at least this much)
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     */
    @FormUrlEncoded
    @POST("/99/Grid/psvm")
    Call<PSVMV3> trainPsvm(@Field("hyper_param") double hyper_param, @Field("kernel_type") GenmodelalgospsvmKernelType kernel_type,
            @Field("gamma") double gamma, @Field("rank_ratio") double rank_ratio, @Field("positive_weight") double positive_weight,
            @Field("negative_weight") double negative_weight, @Field("disable_training_metrics") boolean disable_training_metrics,
            @Field("sv_threshold") double sv_threshold, @Field("max_iterations") int max_iterations,
            @Field("fact_threshold") double fact_threshold, @Field("feasible_threshold") double feasible_threshold,
            @Field("surrogate_gap_threshold") double surrogate_gap_threshold, @Field("mu_factor") double mu_factor,
            @Field("seed") long seed, @Field("model_id") String model_id, @Field("training_frame") String training_frame,
            @Field("validation_frame") String validation_frame, @Field("nfolds") int nfolds,
            @Field("keep_cross_validation_models") boolean keep_cross_validation_models,
            @Field("keep_cross_validation_predictions") boolean keep_cross_validation_predictions,
            @Field("keep_cross_validation_fold_assignment") boolean keep_cross_validation_fold_assignment,
            @Field("parallelize_cross_validation") boolean parallelize_cross_validation,
            @Field("distribution") GenmodelutilsDistributionFamily distribution, @Field("tweedie_power") double tweedie_power,
            @Field("quantile_alpha") double quantile_alpha, @Field("huber_alpha") double huber_alpha,
            @Field("response_column") String response_column, @Field("weights_column") String weights_column,
            @Field("offset_column") String offset_column, @Field("fold_column") String fold_column,
            @Field("fold_assignment") ModelParametersFoldAssignmentScheme fold_assignment,
            @Field("categorical_encoding") ModelParametersCategoricalEncodingScheme categorical_encoding,
            @Field("max_categorical_levels") int max_categorical_levels, @Field("ignored_columns") String[] ignored_columns,
            @Field("ignore_const_cols") boolean ignore_const_cols, @Field("score_each_iteration") boolean score_each_iteration,
            @Field("checkpoint") String checkpoint, @Field("stopping_rounds") int stopping_rounds,
            @Field("max_runtime_secs") double max_runtime_secs, @Field("stopping_metric") ScoreKeeperStoppingMetric stopping_metric,
            @Field("stopping_tolerance") double stopping_tolerance, @Field("custom_metric_func") String custom_metric_func,
            @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir);

    @FormUrlEncoded
    @POST("/99/Grid/psvm")
    Call<PSVMV3> trainPsvm();

    /**
     * Import previously saved grid model
     *   @param grid_path Full path to the file containing saved Grid
     */
    @FormUrlEncoded
    @POST("/3/Grid.bin/import")
    Call<GridKeyV3> importGrid(@Field("grid_path") String grid_path);

    /**
     * Export a Grid and its models.
     *   @param grid_id ID of the Grid to load from the directory
     *   @param grid_directory Path to the directory with saved Grid search
     */
    @FormUrlEncoded
    @POST("/3/Grid.bin/{grid_id}/export")
    Call<GridKeyV3> exportGrid(@Path("grid_id") String grid_id, @Field("grid_directory") String grid_directory);

    @SuppressWarnings("unused")
    class Helper {
        /**
         * Run grid search for XGBoost model.
         */
        public static Call<XGBoostV3> trainXgboost(final Grid z, final XGBoostParametersV3 p) {
            return z.trainXgboost(p.ntrees, p.nEstimators, p.maxDepth, p.minRows, p.minChildWeight, p.learnRate, p.eta, p.sampleRate,
                    p.subsample, p.colSampleRate, p.colsampleBylevel, p.colSampleRatePerTree, p.colsampleBytree, p.monotoneConstraints,
                    p.maxAbsLeafnodePred, p.maxDeltaStep, p.scoreTreeInterval, p.seed, p.minSplitImprovement, p.gamma, p.nthread,
                    p.saveMatrixDirectory, p.calibrateModel, (p.calibrationFrame == null ? null : p.calibrationFrame.name), p.maxBins,
                    p.maxLeaves, p.minSumHessianInLeaf, p.minDataInLeaf, p.treeMethod, p.growPolicy, p.booster, p.regLambda, p.regAlpha,
                    p.quietMode, p.sampleType, p.normalizeType, p.rateDrop, p.oneDrop, p.skipDrop, p.dmatrixType, p.backend, p.gpuId,
                    (p.modelId == null ? null : p.modelId.name), (p.trainingFrame == null ? null : p.trainingFrame.name),
                    (p.validationFrame == null ? null : p.validationFrame.name), p.nfolds, p.keepCrossValidationModels,
                    p.keepCrossValidationPredictions, p.keepCrossValidationFoldAssignment, p.parallelizeCrossValidation, p.distribution,
                    p.tweediePower, p.quantileAlpha, p.huberAlpha, (p.responseColumn == null ? null : p.responseColumn.columnName),
                    (p.weightsColumn == null ? null : p.weightsColumn.columnName),
                    (p.offsetColumn == null ? null : p.offsetColumn.columnName), (p.foldColumn == null ? null : p.foldColumn.columnName),
                    p.foldAssignment, p.categoricalEncoding, p.maxCategoricalLevels, p.ignoredColumns, p.ignoreConstCols,
                    p.scoreEachIteration, (p.checkpoint == null ? null : p.checkpoint.name), p.stoppingRounds, p.maxRuntimeSecs,
                    p.stoppingMetric, p.stoppingTolerance, p.customMetricFunc, p.customDistributionFunc, p.exportCheckpointsDir);
        }

        /**
         * Run grid search for TargetEncoderBuilder model.
         */
        public static Call<TargetEncoderV3> trainTargetencoder(final Grid z, final TargetEncoderParametersV3 p) {
            return z.trainTargetencoder(p.blending, p.k, p.f, p.dataLeakageHandling, p.noiseLevel, p.seed,
                    (p.modelId == null ? null : p.modelId.name), (p.trainingFrame == null ? null : p.trainingFrame.name),
                    (p.validationFrame == null ? null : p.validationFrame.name), p.nfolds, p.keepCrossValidationModels,
                    p.keepCrossValidationPredictions, p.keepCrossValidationFoldAssignment, p.parallelizeCrossValidation, p.distribution,
                    p.tweediePower, p.quantileAlpha, p.huberAlpha, (p.responseColumn == null ? null : p.responseColumn.columnName),
                    (p.weightsColumn == null ? null : p.weightsColumn.columnName),
                    (p.offsetColumn == null ? null : p.offsetColumn.columnName), (p.foldColumn == null ? null : p.foldColumn.columnName),
                    p.foldAssignment, p.categoricalEncoding, p.maxCategoricalLevels, p.ignoredColumns, p.ignoreConstCols,
                    p.scoreEachIteration, (p.checkpoint == null ? null : p.checkpoint.name), p.stoppingRounds, p.maxRuntimeSecs,
                    p.stoppingMetric, p.stoppingTolerance, p.customMetricFunc, p.customDistributionFunc, p.exportCheckpointsDir);
        }

        /**
         * Run grid search for DeepLearning model.
         */
        public static Call<DeepLearningV3> trainDeeplearning(final Grid z, final DeepLearningParametersV3 p) {
            return z.trainDeeplearning(p.balanceClasses, p.classSamplingFactors, p.maxAfterBalanceSize, p.maxConfusionMatrixSize,
                    p.maxHitRatioK, p.activation, p.hidden, p.epochs, p.trainSamplesPerIteration, p.targetRatioCommToComp, p.seed,
                    p.adaptiveRate, p.rho, p.epsilon, p.rate, p.rateAnnealing, p.rateDecay, p.momentumStart, p.momentumRamp,
                    p.momentumStable, p.nesterovAcceleratedGradient, p.inputDropoutRatio, p.hiddenDropoutRatios, p.l1, p.l2, p.maxW2,
                    p.initialWeightDistribution, p.initialWeightScale,
                    (p.initialWeights == null ? null : keyArrayToStringArray(p.initialWeights)),
                    (p.initialBiases == null ? null : keyArrayToStringArray(p.initialBiases)), p.loss, p.scoreInterval,
                    p.scoreTrainingSamples, p.scoreValidationSamples, p.scoreDutyCycle, p.classificationStop, p.regressionStop, p.quietMode,
                    p.scoreValidationSampling, p.overwriteWithBestModel, p.autoencoder, p.useAllFactorLevels, p.standardize, p.diagnostics,
                    p.variableImportances, p.fastMode, p.forceLoadBalance, p.replicateTrainingData, p.singleNodeMode, p.shuffleTrainingData,
                    p.missingValuesHandling, p.sparse, p.colMajor, p.averageActivation, p.sparsityBeta, p.maxCategoricalFeatures,
                    p.reproducible, p.exportWeightsAndBiases, p.miniBatchSize, p.elasticAveraging, p.elasticAveragingMovingRate,
                    p.elasticAveragingRegularization, (p.pretrainedAutoencoder == null ? null : p.pretrainedAutoencoder.name),
                    (p.modelId == null ? null : p.modelId.name), (p.trainingFrame == null ? null : p.trainingFrame.name),
                    (p.validationFrame == null ? null : p.validationFrame.name), p.nfolds, p.keepCrossValidationModels,
                    p.keepCrossValidationPredictions, p.keepCrossValidationFoldAssignment, p.parallelizeCrossValidation, p.distribution,
                    p.tweediePower, p.quantileAlpha, p.huberAlpha, (p.responseColumn == null ? null : p.responseColumn.columnName),
                    (p.weightsColumn == null ? null : p.weightsColumn.columnName),
                    (p.offsetColumn == null ? null : p.offsetColumn.columnName), (p.foldColumn == null ? null : p.foldColumn.columnName),
                    p.foldAssignment, p.categoricalEncoding, p.maxCategoricalLevels, p.ignoredColumns, p.ignoreConstCols,
                    p.scoreEachIteration, (p.checkpoint == null ? null : p.checkpoint.name), p.stoppingRounds, p.maxRuntimeSecs,
                    p.stoppingMetric, p.stoppingTolerance, p.customMetricFunc, p.customDistributionFunc, p.exportCheckpointsDir);
        }

        /**
         * Run grid search for GLM model.
         */
        public static Call<GLMV3> trainGlm(final Grid z, final GLMParametersV3 p) {
            return z.trainGlm(p.seed, p.family, p.randFamily, p.tweedieVariancePower, p.tweedieLinkPower, p.theta, p.solver, p.alpha,
                    p.lambda, p.lambdaSearch, p.earlyStopping, p.nlambdas, p.standardize, p.missingValuesHandling,
                    (p.plugValues == null ? null : p.plugValues.name), p.nonNegative, p.maxIterations, p.betaEpsilon, p.objectiveEpsilon,
                    p.gradientEpsilon, p.objReg, p.link, p.randLink, p.startval, p.randomColumns, p.calcLike, p.intercept, p.hglm, p.prior,
                    p.lambdaMinRatio, (p.betaConstraints == null ? null : p.betaConstraints.name), p.maxActivePredictors, p.interactions,
                    p.interactionPairs, p.balanceClasses, p.classSamplingFactors, p.maxAfterBalanceSize, p.maxConfusionMatrixSize,
                    p.maxHitRatioK, p.computePValues, p.removeCollinearColumns, (p.modelId == null ? null : p.modelId.name),
                    (p.trainingFrame == null ? null : p.trainingFrame.name), (p.validationFrame == null ? null : p.validationFrame.name),
                    p.nfolds, p.keepCrossValidationModels, p.keepCrossValidationPredictions, p.keepCrossValidationFoldAssignment,
                    p.parallelizeCrossValidation, p.distribution, p.tweediePower, p.quantileAlpha, p.huberAlpha,
                    (p.responseColumn == null ? null : p.responseColumn.columnName),
                    (p.weightsColumn == null ? null : p.weightsColumn.columnName),
                    (p.offsetColumn == null ? null : p.offsetColumn.columnName), (p.foldColumn == null ? null : p.foldColumn.columnName),
                    p.foldAssignment, p.categoricalEncoding, p.maxCategoricalLevels, p.ignoredColumns, p.ignoreConstCols,
                    p.scoreEachIteration, (p.checkpoint == null ? null : p.checkpoint.name), p.stoppingRounds, p.maxRuntimeSecs,
                    p.stoppingMetric, p.stoppingTolerance, p.customMetricFunc, p.customDistributionFunc, p.exportCheckpointsDir);
        }

        /**
         * Run grid search for GLRM model.
         */
        public static Call<GLRMV3> trainGlrm(final Grid z, final GLRMParametersV3 p) {
            return z.trainGlrm(p.transform, p.k, p.loss, p.multiLoss, p.lossByCol, p.lossByColIdx, p.period, p.regularizationX,
                    p.regularizationY, p.gammaX, p.gammaY, p.maxIterations, p.maxUpdates, p.initStepSize, p.minStepSize, p.seed, p.init,
                    p.svdMethod, (p.userY == null ? null : p.userY.name), (p.userX == null ? null : p.userX.name), p.loadingName,
                    p.expandUserY, p.imputeOriginal, p.recoverSvd, (p.modelId == null ? null : p.modelId.name),
                    (p.trainingFrame == null ? null : p.trainingFrame.name), (p.validationFrame == null ? null : p.validationFrame.name),
                    p.nfolds, p.keepCrossValidationModels, p.keepCrossValidationPredictions, p.keepCrossValidationFoldAssignment,
                    p.parallelizeCrossValidation, p.distribution, p.tweediePower, p.quantileAlpha, p.huberAlpha,
                    (p.responseColumn == null ? null : p.responseColumn.columnName),
                    (p.weightsColumn == null ? null : p.weightsColumn.columnName),
                    (p.offsetColumn == null ? null : p.offsetColumn.columnName), (p.foldColumn == null ? null : p.foldColumn.columnName),
                    p.foldAssignment, p.categoricalEncoding, p.maxCategoricalLevels, p.ignoredColumns, p.ignoreConstCols,
                    p.scoreEachIteration, (p.checkpoint == null ? null : p.checkpoint.name), p.stoppingRounds, p.maxRuntimeSecs,
                    p.stoppingMetric, p.stoppingTolerance, p.customMetricFunc, p.customDistributionFunc, p.exportCheckpointsDir);
        }

        /**
         * Run grid search for KMeans model.
         */
        public static Call<KMeansV3> trainKmeans(final Grid z, final KMeansParametersV3 p) {
            return z.trainKmeans((p.userPoints == null ? null : p.userPoints.name), p.maxIterations, p.standardize, p.seed, p.init,
                    p.estimateK, p.k, (p.modelId == null ? null : p.modelId.name), (p.trainingFrame == null ? null : p.trainingFrame.name),
                    (p.validationFrame == null ? null : p.validationFrame.name), p.nfolds, p.keepCrossValidationModels,
                    p.keepCrossValidationPredictions, p.keepCrossValidationFoldAssignment, p.parallelizeCrossValidation, p.distribution,
                    p.tweediePower, p.quantileAlpha, p.huberAlpha, (p.responseColumn == null ? null : p.responseColumn.columnName),
                    (p.weightsColumn == null ? null : p.weightsColumn.columnName),
                    (p.offsetColumn == null ? null : p.offsetColumn.columnName), (p.foldColumn == null ? null : p.foldColumn.columnName),
                    p.foldAssignment, p.categoricalEncoding, p.maxCategoricalLevels, p.ignoredColumns, p.ignoreConstCols,
                    p.scoreEachIteration, (p.checkpoint == null ? null : p.checkpoint.name), p.stoppingRounds, p.maxRuntimeSecs,
                    p.stoppingMetric, p.stoppingTolerance, p.customMetricFunc, p.customDistributionFunc, p.exportCheckpointsDir);
        }

        /**
         * Run grid search for NaiveBayes model.
         */
        public static Call<NaiveBayesV3> trainNaivebayes(final Grid z, final NaiveBayesParametersV3 p) {
            return z.trainNaivebayes(p.balanceClasses, p.classSamplingFactors, p.maxAfterBalanceSize, p.maxConfusionMatrixSize,
                    p.maxHitRatioK, p.laplace, p.minSdev, p.epsSdev, p.minProb, p.epsProb, p.computeMetrics, p.seed,
                    (p.modelId == null ? null : p.modelId.name), (p.trainingFrame == null ? null : p.trainingFrame.name),
                    (p.validationFrame == null ? null : p.validationFrame.name), p.nfolds, p.keepCrossValidationModels,
                    p.keepCrossValidationPredictions, p.keepCrossValidationFoldAssignment, p.parallelizeCrossValidation, p.distribution,
                    p.tweediePower, p.quantileAlpha, p.huberAlpha, (p.responseColumn == null ? null : p.responseColumn.columnName),
                    (p.weightsColumn == null ? null : p.weightsColumn.columnName),
                    (p.offsetColumn == null ? null : p.offsetColumn.columnName), (p.foldColumn == null ? null : p.foldColumn.columnName),
                    p.foldAssignment, p.categoricalEncoding, p.maxCategoricalLevels, p.ignoredColumns, p.ignoreConstCols,
                    p.scoreEachIteration, (p.checkpoint == null ? null : p.checkpoint.name), p.stoppingRounds, p.maxRuntimeSecs,
                    p.stoppingMetric, p.stoppingTolerance, p.customMetricFunc, p.customDistributionFunc, p.exportCheckpointsDir);
        }

        /**
         * Run grid search for PCA model.
         */
        public static Call<PCAV3> trainPca(final Grid z, final PCAParametersV3 p) {
            return z.trainPca(p.transform, p.pcaMethod, p.pcaImpl, p.k, p.maxIterations, p.seed, p.useAllFactorLevels, p.computeMetrics,
                    p.imputeMissing, (p.modelId == null ? null : p.modelId.name), (p.trainingFrame == null ? null : p.trainingFrame.name),
                    (p.validationFrame == null ? null : p.validationFrame.name), p.nfolds, p.keepCrossValidationModels,
                    p.keepCrossValidationPredictions, p.keepCrossValidationFoldAssignment, p.parallelizeCrossValidation, p.distribution,
                    p.tweediePower, p.quantileAlpha, p.huberAlpha, (p.responseColumn == null ? null : p.responseColumn.columnName),
                    (p.weightsColumn == null ? null : p.weightsColumn.columnName),
                    (p.offsetColumn == null ? null : p.offsetColumn.columnName), (p.foldColumn == null ? null : p.foldColumn.columnName),
                    p.foldAssignment, p.categoricalEncoding, p.maxCategoricalLevels, p.ignoredColumns, p.ignoreConstCols,
                    p.scoreEachIteration, (p.checkpoint == null ? null : p.checkpoint.name), p.stoppingRounds, p.maxRuntimeSecs,
                    p.stoppingMetric, p.stoppingTolerance, p.customMetricFunc, p.customDistributionFunc, p.exportCheckpointsDir);
        }

        /**
         * Run grid search for SVD model.
         */
        public static Call<SVDV99> trainSvd(final Grid z, final SVDParametersV99 p) {
            return z.trainSvd(p.transform, p.svdMethod, p.nv, p.maxIterations, p.seed, p.keepU, p.uName, p.useAllFactorLevels,
                    (p.modelId == null ? null : p.modelId.name), (p.trainingFrame == null ? null : p.trainingFrame.name),
                    (p.validationFrame == null ? null : p.validationFrame.name), p.nfolds, p.keepCrossValidationModels,
                    p.keepCrossValidationPredictions, p.keepCrossValidationFoldAssignment, p.parallelizeCrossValidation, p.distribution,
                    p.tweediePower, p.quantileAlpha, p.huberAlpha, (p.responseColumn == null ? null : p.responseColumn.columnName),
                    (p.weightsColumn == null ? null : p.weightsColumn.columnName),
                    (p.offsetColumn == null ? null : p.offsetColumn.columnName), (p.foldColumn == null ? null : p.foldColumn.columnName),
                    p.foldAssignment, p.categoricalEncoding, p.maxCategoricalLevels, p.ignoredColumns, p.ignoreConstCols,
                    p.scoreEachIteration, (p.checkpoint == null ? null : p.checkpoint.name), p.stoppingRounds, p.maxRuntimeSecs,
                    p.stoppingMetric, p.stoppingTolerance, p.customMetricFunc, p.customDistributionFunc, p.exportCheckpointsDir);
        }

        /**
         * Run grid search for DRF model.
         */
        public static Call<DRFV3> trainDrf(final Grid z, final DRFParametersV3 p) {
            return z.trainDrf(p.mtries, p.binomialDoubleTrees, p.sampleRate, p.balanceClasses, p.classSamplingFactors,
                    p.maxAfterBalanceSize, p.maxConfusionMatrixSize, p.maxHitRatioK, p.ntrees, p.maxDepth, p.minRows, p.nbins,
                    p.nbinsTopLevel, p.nbinsCats, p.r2Stopping, p.seed, p.buildTreeOneNode, p.sampleRatePerClass, p.colSampleRatePerTree,
                    p.colSampleRateChangePerLevel, p.scoreTreeInterval, p.minSplitImprovement, p.histogramType, p.calibrateModel,
                    (p.calibrationFrame == null ? null : p.calibrationFrame.name), p.checkConstantResponse,
                    (p.modelId == null ? null : p.modelId.name), (p.trainingFrame == null ? null : p.trainingFrame.name),
                    (p.validationFrame == null ? null : p.validationFrame.name), p.nfolds, p.keepCrossValidationModels,
                    p.keepCrossValidationPredictions, p.keepCrossValidationFoldAssignment, p.parallelizeCrossValidation, p.distribution,
                    p.tweediePower, p.quantileAlpha, p.huberAlpha, (p.responseColumn == null ? null : p.responseColumn.columnName),
                    (p.weightsColumn == null ? null : p.weightsColumn.columnName),
                    (p.offsetColumn == null ? null : p.offsetColumn.columnName), (p.foldColumn == null ? null : p.foldColumn.columnName),
                    p.foldAssignment, p.categoricalEncoding, p.maxCategoricalLevels, p.ignoredColumns, p.ignoreConstCols,
                    p.scoreEachIteration, (p.checkpoint == null ? null : p.checkpoint.name), p.stoppingRounds, p.maxRuntimeSecs,
                    p.stoppingMetric, p.stoppingTolerance, p.customMetricFunc, p.customDistributionFunc, p.exportCheckpointsDir);
        }

        /**
         * Run grid search for GBM model.
         */
        public static Call<GBMV3> trainGbm(final Grid z, final GBMParametersV3 p) {
            return z.trainGbm(p.learnRate, p.learnRateAnnealing, p.sampleRate, p.colSampleRate, p.monotoneConstraints, p.maxAbsLeafnodePred,
                    p.predNoiseBandwidth, p.balanceClasses, p.classSamplingFactors, p.maxAfterBalanceSize, p.maxConfusionMatrixSize,
                    p.maxHitRatioK, p.ntrees, p.maxDepth, p.minRows, p.nbins, p.nbinsTopLevel, p.nbinsCats, p.r2Stopping, p.seed,
                    p.buildTreeOneNode, p.sampleRatePerClass, p.colSampleRatePerTree, p.colSampleRateChangePerLevel, p.scoreTreeInterval,
                    p.minSplitImprovement, p.histogramType, p.calibrateModel, (p.calibrationFrame == null ? null : p.calibrationFrame.name),
                    p.checkConstantResponse, (p.modelId == null ? null : p.modelId.name),
                    (p.trainingFrame == null ? null : p.trainingFrame.name), (p.validationFrame == null ? null : p.validationFrame.name),
                    p.nfolds, p.keepCrossValidationModels, p.keepCrossValidationPredictions, p.keepCrossValidationFoldAssignment,
                    p.parallelizeCrossValidation, p.distribution, p.tweediePower, p.quantileAlpha, p.huberAlpha,
                    (p.responseColumn == null ? null : p.responseColumn.columnName),
                    (p.weightsColumn == null ? null : p.weightsColumn.columnName),
                    (p.offsetColumn == null ? null : p.offsetColumn.columnName), (p.foldColumn == null ? null : p.foldColumn.columnName),
                    p.foldAssignment, p.categoricalEncoding, p.maxCategoricalLevels, p.ignoredColumns, p.ignoreConstCols,
                    p.scoreEachIteration, (p.checkpoint == null ? null : p.checkpoint.name), p.stoppingRounds, p.maxRuntimeSecs,
                    p.stoppingMetric, p.stoppingTolerance, p.customMetricFunc, p.customDistributionFunc, p.exportCheckpointsDir);
        }

        /**
         * Run grid search for IsolationForest model.
         */
        public static Call<IsolationForestV3> trainIsolationforest(final Grid z, final IsolationForestParametersV3 p) {
            return z.trainIsolationforest(p.sampleSize, p.sampleRate, p.mtries, p.balanceClasses, p.classSamplingFactors,
                    p.maxAfterBalanceSize, p.maxConfusionMatrixSize, p.maxHitRatioK, p.ntrees, p.maxDepth, p.minRows, p.nbins,
                    p.nbinsTopLevel, p.nbinsCats, p.r2Stopping, p.seed, p.buildTreeOneNode, p.sampleRatePerClass, p.colSampleRatePerTree,
                    p.colSampleRateChangePerLevel, p.scoreTreeInterval, p.minSplitImprovement, p.histogramType, p.calibrateModel,
                    (p.calibrationFrame == null ? null : p.calibrationFrame.name), p.checkConstantResponse,
                    (p.modelId == null ? null : p.modelId.name), (p.trainingFrame == null ? null : p.trainingFrame.name),
                    (p.validationFrame == null ? null : p.validationFrame.name), p.nfolds, p.keepCrossValidationModels,
                    p.keepCrossValidationPredictions, p.keepCrossValidationFoldAssignment, p.parallelizeCrossValidation, p.distribution,
                    p.tweediePower, p.quantileAlpha, p.huberAlpha, (p.responseColumn == null ? null : p.responseColumn.columnName),
                    (p.weightsColumn == null ? null : p.weightsColumn.columnName),
                    (p.offsetColumn == null ? null : p.offsetColumn.columnName), (p.foldColumn == null ? null : p.foldColumn.columnName),
                    p.foldAssignment, p.categoricalEncoding, p.maxCategoricalLevels, p.ignoredColumns, p.ignoreConstCols,
                    p.scoreEachIteration, (p.checkpoint == null ? null : p.checkpoint.name), p.stoppingRounds, p.maxRuntimeSecs,
                    p.stoppingMetric, p.stoppingTolerance, p.customMetricFunc, p.customDistributionFunc, p.exportCheckpointsDir);
        }

        /**
         * Run grid search for Aggregator model.
         */
        public static Call<AggregatorV99> trainAggregator(final Grid z, final AggregatorParametersV99 p) {
            return z.trainAggregator(p.transform, p.pcaMethod, p.k, p.maxIterations, p.targetNumExemplars, p.relTolNumExemplars, p.seed,
                    p.useAllFactorLevels, p.saveMappingFrame, p.numIterationWithoutNewExemplar, (p.modelId == null ? null : p.modelId.name),
                    (p.trainingFrame == null ? null : p.trainingFrame.name), (p.validationFrame == null ? null : p.validationFrame.name),
                    p.nfolds, p.keepCrossValidationModels, p.keepCrossValidationPredictions, p.keepCrossValidationFoldAssignment,
                    p.parallelizeCrossValidation, p.distribution, p.tweediePower, p.quantileAlpha, p.huberAlpha,
                    (p.responseColumn == null ? null : p.responseColumn.columnName),
                    (p.weightsColumn == null ? null : p.weightsColumn.columnName),
                    (p.offsetColumn == null ? null : p.offsetColumn.columnName), (p.foldColumn == null ? null : p.foldColumn.columnName),
                    p.foldAssignment, p.categoricalEncoding, p.maxCategoricalLevels, p.ignoredColumns, p.ignoreConstCols,
                    p.scoreEachIteration, (p.checkpoint == null ? null : p.checkpoint.name), p.stoppingRounds, p.maxRuntimeSecs,
                    p.stoppingMetric, p.stoppingTolerance, p.customMetricFunc, p.customDistributionFunc, p.exportCheckpointsDir);
        }

        /**
         * Run grid search for DeepWater model.
         */
        public static Call<DeepWaterV3> trainDeepwater(final Grid z, final DeepWaterParametersV3 p) {
            return z.trainDeepwater(p.problemType, p.activation, p.hidden, p.inputDropoutRatio, p.hiddenDropoutRatios,
                    p.maxConfusionMatrixSize, p.sparse, p.maxHitRatioK, p.epochs, p.trainSamplesPerIteration, p.targetRatioCommToComp,
                    p.seed, p.learningRate, p.learningRateAnnealing, p.momentumStart, p.momentumRamp, p.momentumStable, p.scoreInterval,
                    p.scoreTrainingSamples, p.scoreValidationSamples, p.scoreDutyCycle, p.classificationStop, p.regressionStop, p.quietMode,
                    p.overwriteWithBestModel, p.autoencoder, p.diagnostics, p.variableImportances, p.replicateTrainingData,
                    p.singleNodeMode, p.shuffleTrainingData, p.miniBatchSize, p.clipGradient, p.network, p.backend, p.imageShape,
                    p.channels, p.gpu, p.deviceId, p.cacheData, p.networkDefinitionFile, p.networkParametersFile, p.meanImageFile,
                    p.exportNativeParametersPrefix, p.standardize, p.balanceClasses, p.classSamplingFactors, p.maxAfterBalanceSize,
                    (p.modelId == null ? null : p.modelId.name), (p.trainingFrame == null ? null : p.trainingFrame.name),
                    (p.validationFrame == null ? null : p.validationFrame.name), p.nfolds, p.keepCrossValidationModels,
                    p.keepCrossValidationPredictions, p.keepCrossValidationFoldAssignment, p.parallelizeCrossValidation, p.distribution,
                    p.tweediePower, p.quantileAlpha, p.huberAlpha, (p.responseColumn == null ? null : p.responseColumn.columnName),
                    (p.weightsColumn == null ? null : p.weightsColumn.columnName),
                    (p.offsetColumn == null ? null : p.offsetColumn.columnName), (p.foldColumn == null ? null : p.foldColumn.columnName),
                    p.foldAssignment, p.categoricalEncoding, p.maxCategoricalLevels, p.ignoredColumns, p.ignoreConstCols,
                    p.scoreEachIteration, (p.checkpoint == null ? null : p.checkpoint.name), p.stoppingRounds, p.maxRuntimeSecs,
                    p.stoppingMetric, p.stoppingTolerance, p.customMetricFunc, p.customDistributionFunc, p.exportCheckpointsDir);
        }

        /**
         * Run grid search for Word2Vec model.
         */
        public static Call<Word2VecV3> trainWord2vec(final Grid z, final Word2VecParametersV3 p) {
            return z.trainWord2vec(p.vecSize, p.windowSize, p.sentSampleRate, p.normModel, p.epochs, p.minWordFreq, p.initLearningRate,
                    p.wordModel, (p.preTrained == null ? null : p.preTrained.name), (p.modelId == null ? null : p.modelId.name),
                    (p.trainingFrame == null ? null : p.trainingFrame.name), (p.validationFrame == null ? null : p.validationFrame.name),
                    p.nfolds, p.keepCrossValidationModels, p.keepCrossValidationPredictions, p.keepCrossValidationFoldAssignment,
                    p.parallelizeCrossValidation, p.distribution, p.tweediePower, p.quantileAlpha, p.huberAlpha,
                    (p.responseColumn == null ? null : p.responseColumn.columnName),
                    (p.weightsColumn == null ? null : p.weightsColumn.columnName),
                    (p.offsetColumn == null ? null : p.offsetColumn.columnName), (p.foldColumn == null ? null : p.foldColumn.columnName),
                    p.foldAssignment, p.categoricalEncoding, p.maxCategoricalLevels, p.ignoredColumns, p.ignoreConstCols,
                    p.scoreEachIteration, (p.checkpoint == null ? null : p.checkpoint.name), p.stoppingRounds, p.maxRuntimeSecs,
                    p.stoppingMetric, p.stoppingTolerance, p.customMetricFunc, p.customDistributionFunc, p.exportCheckpointsDir);
        }

        /**
         * Run grid search for StackedEnsemble model.
         */
        public static Call<StackedEnsembleV99> trainStackedensemble(final Grid z, final StackedEnsembleParametersV99 p) {
            return z.trainStackedensemble((p.baseModels == null ? null : keyArrayToStringArray(p.baseModels)), p.metalearnerAlgorithm,
                    p.metalearnerNfolds, p.metalearnerFoldAssignment,
                    (p.metalearnerFoldColumn == null ? null : p.metalearnerFoldColumn.columnName), p.keepLeveloneFrame, p.metalearnerParams,
                    (p.blendingFrame == null ? null : p.blendingFrame.name), p.seed, (p.modelId == null ? null : p.modelId.name),
                    (p.trainingFrame == null ? null : p.trainingFrame.name), (p.validationFrame == null ? null : p.validationFrame.name),
                    p.nfolds, p.keepCrossValidationModels, p.keepCrossValidationPredictions, p.keepCrossValidationFoldAssignment,
                    p.parallelizeCrossValidation, p.distribution, p.tweediePower, p.quantileAlpha, p.huberAlpha,
                    (p.responseColumn == null ? null : p.responseColumn.columnName),
                    (p.weightsColumn == null ? null : p.weightsColumn.columnName),
                    (p.offsetColumn == null ? null : p.offsetColumn.columnName), (p.foldColumn == null ? null : p.foldColumn.columnName),
                    p.foldAssignment, p.categoricalEncoding, p.maxCategoricalLevels, p.ignoredColumns, p.ignoreConstCols,
                    p.scoreEachIteration, (p.checkpoint == null ? null : p.checkpoint.name), p.stoppingRounds, p.maxRuntimeSecs,
                    p.stoppingMetric, p.stoppingTolerance, p.customMetricFunc, p.customDistributionFunc, p.exportCheckpointsDir);
        }

        /**
         * Run grid search for CoxPH model.
         */
        public static Call<CoxPHV3> trainCoxph(final Grid z, final CoxPHParametersV3 p) {
            return z.trainCoxph((p.startColumn == null ? null : p.startColumn.columnName),
                    (p.stopColumn == null ? null : p.stopColumn.columnName), p.stratifyBy, p.ties, p.init, p.lreMin, p.maxIterations,
                    p.interactionsOnly, p.interactions, p.interactionPairs, p.useAllFactorLevels,
                    (p.modelId == null ? null : p.modelId.name), (p.trainingFrame == null ? null : p.trainingFrame.name),
                    (p.validationFrame == null ? null : p.validationFrame.name), p.nfolds, p.keepCrossValidationModels,
                    p.keepCrossValidationPredictions, p.keepCrossValidationFoldAssignment, p.parallelizeCrossValidation, p.distribution,
                    p.tweediePower, p.quantileAlpha, p.huberAlpha, (p.responseColumn == null ? null : p.responseColumn.columnName),
                    (p.weightsColumn == null ? null : p.weightsColumn.columnName),
                    (p.offsetColumn == null ? null : p.offsetColumn.columnName), (p.foldColumn == null ? null : p.foldColumn.columnName),
                    p.foldAssignment, p.categoricalEncoding, p.maxCategoricalLevels, p.ignoredColumns, p.ignoreConstCols,
                    p.scoreEachIteration, (p.checkpoint == null ? null : p.checkpoint.name), p.stoppingRounds, p.maxRuntimeSecs,
                    p.stoppingMetric, p.stoppingTolerance, p.customMetricFunc, p.customDistributionFunc, p.exportCheckpointsDir);
        }

        /**
         * Run grid search for Generic model.
         */
        public static Call<GenericV3> trainGeneric(final Grid z, final GenericParametersV3 p) {
            return z.trainGeneric(p.path, (p.modelKey == null ? null : p.modelKey.name), (p.modelId == null ? null : p.modelId.name),
                    (p.trainingFrame == null ? null : p.trainingFrame.name), (p.validationFrame == null ? null : p.validationFrame.name),
                    p.nfolds, p.keepCrossValidationModels, p.keepCrossValidationPredictions, p.keepCrossValidationFoldAssignment,
                    p.parallelizeCrossValidation, p.distribution, p.tweediePower, p.quantileAlpha, p.huberAlpha,
                    (p.responseColumn == null ? null : p.responseColumn.columnName),
                    (p.weightsColumn == null ? null : p.weightsColumn.columnName),
                    (p.offsetColumn == null ? null : p.offsetColumn.columnName), (p.foldColumn == null ? null : p.foldColumn.columnName),
                    p.foldAssignment, p.categoricalEncoding, p.maxCategoricalLevels, p.ignoredColumns, p.ignoreConstCols,
                    p.scoreEachIteration, (p.checkpoint == null ? null : p.checkpoint.name), p.stoppingRounds, p.maxRuntimeSecs,
                    p.stoppingMetric, p.stoppingTolerance, p.customMetricFunc, p.customDistributionFunc, p.exportCheckpointsDir);
        }

        /**
         * Run grid search for PSVM model.
         */
        public static Call<PSVMV3> trainPsvm(final Grid z, final PSVMParametersV3 p) {
            return z.trainPsvm(p.hyperParam, p.kernelType, p.gamma, p.rankRatio, p.positiveWeight, p.negativeWeight,
                    p.disableTrainingMetrics, p.svThreshold, p.maxIterations, p.factThreshold, p.feasibleThreshold, p.surrogateGapThreshold,
                    p.muFactor, p.seed, (p.modelId == null ? null : p.modelId.name),
                    (p.trainingFrame == null ? null : p.trainingFrame.name), (p.validationFrame == null ? null : p.validationFrame.name),
                    p.nfolds, p.keepCrossValidationModels, p.keepCrossValidationPredictions, p.keepCrossValidationFoldAssignment,
                    p.parallelizeCrossValidation, p.distribution, p.tweediePower, p.quantileAlpha, p.huberAlpha,
                    (p.responseColumn == null ? null : p.responseColumn.columnName),
                    (p.weightsColumn == null ? null : p.weightsColumn.columnName),
                    (p.offsetColumn == null ? null : p.offsetColumn.columnName), (p.foldColumn == null ? null : p.foldColumn.columnName),
                    p.foldAssignment, p.categoricalEncoding, p.maxCategoricalLevels, p.ignoredColumns, p.ignoreConstCols,
                    p.scoreEachIteration, (p.checkpoint == null ? null : p.checkpoint.name), p.stoppingRounds, p.maxRuntimeSecs,
                    p.stoppingMetric, p.stoppingTolerance, p.customMetricFunc, p.customDistributionFunc, p.exportCheckpointsDir);
        }

        /**
         * Return an array of Strings for an array of keys.
         */
        public static String[] keyArrayToStringArray(final KeyV3[] keys) {
            if (keys == null) {
                return null;
            }
            final var ids = new String[keys.length];
            var i = 0;
            for (final KeyV3 key : keys) {
                ids[i] = key.name;
                i++;
            }
            return ids;
        }
    }

}
