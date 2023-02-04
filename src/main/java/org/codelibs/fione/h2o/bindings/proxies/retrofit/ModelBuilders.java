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
package org.codelibs.fione.h2o.bindings.proxies.retrofit;

import org.codelibs.fione.h2o.bindings.pojos.ANOVAGLMParametersV3;
import org.codelibs.fione.h2o.bindings.pojos.ANOVAGLMV3;
import org.codelibs.fione.h2o.bindings.pojos.AUUCType;
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
import org.codelibs.fione.h2o.bindings.pojos.EnsembleMetalearnerAlgorithm;
import org.codelibs.fione.h2o.bindings.pojos.EnsembleStackedEnsembleModelStackedEnsembleParametersMetalearnerTransform;
import org.codelibs.fione.h2o.bindings.pojos.ExtendedIsolationForestParametersV3;
import org.codelibs.fione.h2o.bindings.pojos.ExtendedIsolationForestV3;
import org.codelibs.fione.h2o.bindings.pojos.GAMParametersV3;
import org.codelibs.fione.h2o.bindings.pojos.GAMV3;
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
import org.codelibs.fione.h2o.bindings.pojos.H2otargetencodingTargetEncoderModelDataLeakageHandlingStrategy;
import org.codelibs.fione.h2o.bindings.pojos.InfogramAlgorithm;
import org.codelibs.fione.h2o.bindings.pojos.InfogramParametersV3;
import org.codelibs.fione.h2o.bindings.pojos.InfogramV3;
import org.codelibs.fione.h2o.bindings.pojos.IsolationForestParametersV3;
import org.codelibs.fione.h2o.bindings.pojos.IsolationForestV3;
import org.codelibs.fione.h2o.bindings.pojos.KMeansInitialization;
import org.codelibs.fione.h2o.bindings.pojos.KMeansParametersV3;
import org.codelibs.fione.h2o.bindings.pojos.KMeansV3;
import org.codelibs.fione.h2o.bindings.pojos.KeyV3;
import org.codelibs.fione.h2o.bindings.pojos.KeyValueV3;
import org.codelibs.fione.h2o.bindings.pojos.ModelBuildersV3;
import org.codelibs.fione.h2o.bindings.pojos.ModelIdV3;
import org.codelibs.fione.h2o.bindings.pojos.ModelParametersCategoricalEncodingScheme;
import org.codelibs.fione.h2o.bindings.pojos.ModelParametersFoldAssignmentScheme;
import org.codelibs.fione.h2o.bindings.pojos.ModelSelectionMode;
import org.codelibs.fione.h2o.bindings.pojos.ModelSelectionParametersV3;
import org.codelibs.fione.h2o.bindings.pojos.ModelSelectionV3;
import org.codelibs.fione.h2o.bindings.pojos.MultinomialAucType;
import org.codelibs.fione.h2o.bindings.pojos.NaiveBayesParametersV3;
import org.codelibs.fione.h2o.bindings.pojos.NaiveBayesV3;
import org.codelibs.fione.h2o.bindings.pojos.PCAImplementation;
import org.codelibs.fione.h2o.bindings.pojos.PCAMethod;
import org.codelibs.fione.h2o.bindings.pojos.PCAParametersV3;
import org.codelibs.fione.h2o.bindings.pojos.PCAV3;
import org.codelibs.fione.h2o.bindings.pojos.PSVMParametersV3;
import org.codelibs.fione.h2o.bindings.pojos.PSVMV3;
import org.codelibs.fione.h2o.bindings.pojos.RuleFitModelAlgorithm;
import org.codelibs.fione.h2o.bindings.pojos.RuleFitModelModelType;
import org.codelibs.fione.h2o.bindings.pojos.RuleFitParametersV3;
import org.codelibs.fione.h2o.bindings.pojos.RuleFitV3;
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
import org.codelibs.fione.h2o.bindings.pojos.TreeupliftUpliftDRFModelUpliftDRFParametersUpliftMetricType;
import org.codelibs.fione.h2o.bindings.pojos.TreexgboostXGBoostModelXGBoostParametersBackend;
import org.codelibs.fione.h2o.bindings.pojos.TreexgboostXGBoostModelXGBoostParametersBooster;
import org.codelibs.fione.h2o.bindings.pojos.TreexgboostXGBoostModelXGBoostParametersDMatrixType;
import org.codelibs.fione.h2o.bindings.pojos.TreexgboostXGBoostModelXGBoostParametersDartNormalizeType;
import org.codelibs.fione.h2o.bindings.pojos.TreexgboostXGBoostModelXGBoostParametersDartSampleType;
import org.codelibs.fione.h2o.bindings.pojos.TreexgboostXGBoostModelXGBoostParametersGrowPolicy;
import org.codelibs.fione.h2o.bindings.pojos.TreexgboostXGBoostModelXGBoostParametersTreeMethod;
import org.codelibs.fione.h2o.bindings.pojos.UpliftDRFParametersV3;
import org.codelibs.fione.h2o.bindings.pojos.UpliftDRFV3;
import org.codelibs.fione.h2o.bindings.pojos.Word2VecNormModel;
import org.codelibs.fione.h2o.bindings.pojos.Word2VecParametersV3;
import org.codelibs.fione.h2o.bindings.pojos.Word2VecV3;
import org.codelibs.fione.h2o.bindings.pojos.Word2VecWordModel;
import org.codelibs.fione.h2o.bindings.pojos.XGBoostParametersV3;
import org.codelibs.fione.h2o.bindings.pojos.XGBoostV3;

import retrofit2.Call;
import retrofit2.http.Field;
import retrofit2.http.FormUrlEncoded;
import retrofit2.http.GET;
import retrofit2.http.POST;
import retrofit2.http.Path;
import retrofit2.http.Query;

public interface ModelBuilders {

    /**
     * Train a XGBoost model.
     *   @param ntrees (same as n_estimators) Number of trees.
     *   @param max_depth Maximum tree depth (0 for unlimited).
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
     *   @param colsample_bynode Column sample rate per tree node (from 0.0 to 1.0)
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
     *   @param build_tree_one_node Run on one node only; no network overhead but fewer cpus used. Suitable for small
     *                              datasets.
     *   @param save_matrix_directory Directory where to save matrices passed to XGBoost library. Useful for debugging.
     *   @param calibrate_model Use Platt Scaling to calculate calibrated class probabilities. Calibration can provide
     *                          more accurate estimates of class probabilities.
     *   @param calibration_frame Calibration frame for Platt Scaling
     *   @param max_bins For tree_method=hist only: maximum number of bins
     *   @param max_leaves For tree_method=hist only: maximum number of leaves
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
     *   @param gpu_id Which GPU(s) to use.
     *   @param interaction_constraints A set of allowed column interactions.
     *   @param scale_pos_weight Controls the effect of observations with positive labels in relation to the observations
     *                           with negative labels on gradient calculation. Useful for imbalanced problems.
     *   @param model_id Destination id for this model; auto-generated if not specified.
     *   @param training_frame Id of the training data frame.
     *   @param validation_frame Id of the validation data frame.
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or >= 2).
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
     *                         If you set weight = 0 for a row, the returned prediction frame at that row is zero and this
     *                         is incorrect. To get an accurate prediction, remove all rows with weight == 0.
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
     *   @param gainslift_bins Gains/Lift table number of bins. 0 means disabled.. Default value -1 means automatic
     *                         binning.
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     *   @param auc_type Set default multinomial AUC type.
     */
    @FormUrlEncoded
    @POST("/3/ModelBuilders/xgboost")
    Call<XGBoostV3> trainXgboost(@Field("ntrees") int ntrees, @Field("max_depth") int max_depth, @Field("min_rows") double min_rows,
            @Field("min_child_weight") double min_child_weight, @Field("learn_rate") double learn_rate, @Field("eta") double eta,
            @Field("sample_rate") double sample_rate, @Field("subsample") double subsample,
            @Field("col_sample_rate") double col_sample_rate, @Field("colsample_bylevel") double colsample_bylevel,
            @Field("col_sample_rate_per_tree") double col_sample_rate_per_tree, @Field("colsample_bytree") double colsample_bytree,
            @Field("colsample_bynode") double colsample_bynode, @Field("monotone_constraints") KeyValueV3[] monotone_constraints,
            @Field("max_abs_leafnode_pred") float max_abs_leafnode_pred, @Field("max_delta_step") float max_delta_step,
            @Field("score_tree_interval") int score_tree_interval, @Field("seed") long seed,
            @Field("min_split_improvement") float min_split_improvement, @Field("gamma") float gamma, @Field("nthread") int nthread,
            @Field("build_tree_one_node") boolean build_tree_one_node, @Field("save_matrix_directory") String save_matrix_directory,
            @Field("calibrate_model") boolean calibrate_model, @Field("calibration_frame") String calibration_frame,
            @Field("max_bins") int max_bins, @Field("max_leaves") int max_leaves,
            @Field("tree_method") TreexgboostXGBoostModelXGBoostParametersTreeMethod tree_method,
            @Field("grow_policy") TreexgboostXGBoostModelXGBoostParametersGrowPolicy grow_policy,
            @Field("booster") TreexgboostXGBoostModelXGBoostParametersBooster booster, @Field("reg_lambda") float reg_lambda,
            @Field("reg_alpha") float reg_alpha, @Field("quiet_mode") boolean quiet_mode,
            @Field("sample_type") TreexgboostXGBoostModelXGBoostParametersDartSampleType sample_type,
            @Field("normalize_type") TreexgboostXGBoostModelXGBoostParametersDartNormalizeType normalize_type,
            @Field("rate_drop") float rate_drop, @Field("one_drop") boolean one_drop, @Field("skip_drop") float skip_drop,
            @Field("dmatrix_type") TreexgboostXGBoostModelXGBoostParametersDMatrixType dmatrix_type,
            @Field("backend") TreexgboostXGBoostModelXGBoostParametersBackend backend, @Field("gpu_id") int[] gpu_id,
            @Field("interaction_constraints") String[][] interaction_constraints, @Field("scale_pos_weight") float scale_pos_weight,
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
            @Field("stopping_tolerance") double stopping_tolerance, @Field("gainslift_bins") int gainslift_bins,
            @Field("custom_metric_func") String custom_metric_func, @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir, @Field("auc_type") MultinomialAucType auc_type);

    @FormUrlEncoded
    @POST("/3/ModelBuilders/xgboost")
    Call<XGBoostV3> trainXgboost();

    /**
     * Validate a set of XGBoost model builder parameters.
     *   @param ntrees (same as n_estimators) Number of trees.
     *   @param max_depth Maximum tree depth (0 for unlimited).
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
     *   @param colsample_bynode Column sample rate per tree node (from 0.0 to 1.0)
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
     *   @param build_tree_one_node Run on one node only; no network overhead but fewer cpus used. Suitable for small
     *                              datasets.
     *   @param save_matrix_directory Directory where to save matrices passed to XGBoost library. Useful for debugging.
     *   @param calibrate_model Use Platt Scaling to calculate calibrated class probabilities. Calibration can provide
     *                          more accurate estimates of class probabilities.
     *   @param calibration_frame Calibration frame for Platt Scaling
     *   @param max_bins For tree_method=hist only: maximum number of bins
     *   @param max_leaves For tree_method=hist only: maximum number of leaves
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
     *   @param gpu_id Which GPU(s) to use.
     *   @param interaction_constraints A set of allowed column interactions.
     *   @param scale_pos_weight Controls the effect of observations with positive labels in relation to the observations
     *                           with negative labels on gradient calculation. Useful for imbalanced problems.
     *   @param model_id Destination id for this model; auto-generated if not specified.
     *   @param training_frame Id of the training data frame.
     *   @param validation_frame Id of the validation data frame.
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or >= 2).
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
     *                         If you set weight = 0 for a row, the returned prediction frame at that row is zero and this
     *                         is incorrect. To get an accurate prediction, remove all rows with weight == 0.
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
     *   @param gainslift_bins Gains/Lift table number of bins. 0 means disabled.. Default value -1 means automatic
     *                         binning.
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     *   @param auc_type Set default multinomial AUC type.
     */
    @FormUrlEncoded
    @POST("/3/ModelBuilders/xgboost/parameters")
    Call<XGBoostV3> validate_parametersXgboost(@Field("ntrees") int ntrees, @Field("max_depth") int max_depth,
            @Field("min_rows") double min_rows, @Field("min_child_weight") double min_child_weight, @Field("learn_rate") double learn_rate,
            @Field("eta") double eta, @Field("sample_rate") double sample_rate, @Field("subsample") double subsample,
            @Field("col_sample_rate") double col_sample_rate, @Field("colsample_bylevel") double colsample_bylevel,
            @Field("col_sample_rate_per_tree") double col_sample_rate_per_tree, @Field("colsample_bytree") double colsample_bytree,
            @Field("colsample_bynode") double colsample_bynode, @Field("monotone_constraints") KeyValueV3[] monotone_constraints,
            @Field("max_abs_leafnode_pred") float max_abs_leafnode_pred, @Field("max_delta_step") float max_delta_step,
            @Field("score_tree_interval") int score_tree_interval, @Field("seed") long seed,
            @Field("min_split_improvement") float min_split_improvement, @Field("gamma") float gamma, @Field("nthread") int nthread,
            @Field("build_tree_one_node") boolean build_tree_one_node, @Field("save_matrix_directory") String save_matrix_directory,
            @Field("calibrate_model") boolean calibrate_model, @Field("calibration_frame") String calibration_frame,
            @Field("max_bins") int max_bins, @Field("max_leaves") int max_leaves,
            @Field("tree_method") TreexgboostXGBoostModelXGBoostParametersTreeMethod tree_method,
            @Field("grow_policy") TreexgboostXGBoostModelXGBoostParametersGrowPolicy grow_policy,
            @Field("booster") TreexgboostXGBoostModelXGBoostParametersBooster booster, @Field("reg_lambda") float reg_lambda,
            @Field("reg_alpha") float reg_alpha, @Field("quiet_mode") boolean quiet_mode,
            @Field("sample_type") TreexgboostXGBoostModelXGBoostParametersDartSampleType sample_type,
            @Field("normalize_type") TreexgboostXGBoostModelXGBoostParametersDartNormalizeType normalize_type,
            @Field("rate_drop") float rate_drop, @Field("one_drop") boolean one_drop, @Field("skip_drop") float skip_drop,
            @Field("dmatrix_type") TreexgboostXGBoostModelXGBoostParametersDMatrixType dmatrix_type,
            @Field("backend") TreexgboostXGBoostModelXGBoostParametersBackend backend, @Field("gpu_id") int[] gpu_id,
            @Field("interaction_constraints") String[][] interaction_constraints, @Field("scale_pos_weight") float scale_pos_weight,
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
            @Field("stopping_tolerance") double stopping_tolerance, @Field("gainslift_bins") int gainslift_bins,
            @Field("custom_metric_func") String custom_metric_func, @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir, @Field("auc_type") MultinomialAucType auc_type);

    @FormUrlEncoded
    @POST("/3/ModelBuilders/xgboost/parameters")
    Call<XGBoostV3> validate_parametersXgboost();

    /**
     * Train a Infogram model.
     *   @param seed Seed for pseudo random number generator (if applicable).
     *   @param standardize Standardize numeric columns to have zero mean and unit variance.
     *   @param plug_values Plug Values (a single row frame containing values that will be used to impute missing values
     *                      of the training/validation frame, use with conjunction missing_values_handling = PlugValues).
     *   @param max_iterations Maximum number of iterations.
     *   @param prior Prior probability for y==1. To be used only for logistic regression iff the data has been sampled
     *                and the mean of response does not reflect reality.
     *   @param balance_classes Balance training data class counts via over/under-sampling (for imbalanced data).
     *   @param class_sampling_factors Desired over/under-sampling ratios per class (in lexicographic order). If not
     *                                 specified, sampling factors will be automatically computed to obtain class balance
     *                                 during training. Requires balance_classes.
     *   @param max_after_balance_size Maximum relative size of the training data after balancing class counts (can be
     *                                 less than 1.0). Requires balance_classes.
     *   @param algorithm Type of machine learning algorithm used to build the infogram. Options include 'AUTO' (gbm),
     *                    'deeplearning' (Deep Learning with default parameters), 'drf' (Random Forest with default
     *                    parameters), 'gbm' (GBM with default parameters), 'glm' (GLM with default parameters), or
     *                    'xgboost' (if available, XGBoost with default parameters).
     *   @param algorithm_params Customized parameters for the machine learning algorithm specified in the algorithm
     *                           parameter.
     *   @param protected_columns Columns that contain features that are sensitive and need to be protected (legally, or
     *                            otherwise), if applicable. These features (e.g. race, gender, etc) should not drive the
     *                            prediction of the response.
     *   @param total_information_threshold A number between 0 and 1 representing a threshold for total information,
     *                                      defaulting to 0.1. For a specific feature, if the total information is higher
     *                                      than this threshold, and the corresponding net information is also higher than
     *                                      the threshold ``net_information_threshold``, that feature will be considered
     *                                      admissible. The total information is the x-axis of the Core Infogram. Default
     *                                      is -1 which gets set to 0.1.
     *   @param net_information_threshold A number between 0 and 1 representing a threshold for net information,
     *                                    defaulting to 0.1.  For a specific feature, if the net information is higher
     *                                    than this threshold, and the corresponding total information is also higher than
     *                                    the total_information_threshold, that feature will be considered admissible. The
     *                                    net information is the y-axis of the Core Infogram. Default is -1 which gets set
     *                                    to 0.1.
     *   @param relevance_index_threshold A number between 0 and 1 representing a threshold for the relevance index,
     *                                    defaulting to 0.1.  This is only used when ``protected_columns`` is set by the
     *                                    user.  For a specific feature, if the relevance index value is higher than this
     *                                    threshold, and the corresponding safety index is also higher than the
     *                                    safety_index_threshold``, that feature will be considered admissible.  The
     *                                    relevance index is the x-axis of the Fair Infogram. Default is -1 which gets set
     *                                    to 0.1.
     *   @param safety_index_threshold A number between 0 and 1 representing a threshold for the safety index, defaulting
     *                                 to 0.1.  This is only used when protected_columns is set by the user.  For a
     *                                 specific feature, if the safety index value is higher than this threshold, and the
     *                                 corresponding relevance index is also higher than the relevance_index_threshold,
     *                                 that feature will be considered admissible.  The safety index is the y-axis of the
     *                                 Fair Infogram. Default is -1 which gets set to 0.1.
     *   @param data_fraction The fraction of training frame to use to build the infogram model. Defaults to 1.0, and any
     *                        value greater than 0 and less than or equal to 1.0 is acceptable.
     *   @param top_n_features An integer specifying the number of columns to evaluate in the infogram.  The columns are
     *                         ranked by variable importance, and the top N are evaluated.  Defaults to 50.
     *   @param model_id Destination id for this model; auto-generated if not specified.
     *   @param training_frame Id of the training data frame.
     *   @param validation_frame Id of the validation data frame.
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or >= 2).
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
     *                         If you set weight = 0 for a row, the returned prediction frame at that row is zero and this
     *                         is incorrect. To get an accurate prediction, remove all rows with weight == 0.
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
     *   @param gainslift_bins Gains/Lift table number of bins. 0 means disabled.. Default value -1 means automatic
     *                         binning.
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     *   @param auc_type Set default multinomial AUC type.
     */
    @FormUrlEncoded
    @POST("/3/ModelBuilders/infogram")
    Call<InfogramV3> trainInfogram(@Field("seed") long seed, @Field("standardize") boolean standardize,
            @Field("plug_values") String plug_values, @Field("max_iterations") int max_iterations, @Field("prior") double prior,
            @Field("balance_classes") boolean balance_classes, @Field("class_sampling_factors") float[] class_sampling_factors,
            @Field("max_after_balance_size") float max_after_balance_size, @Field("algorithm") InfogramAlgorithm algorithm,
            @Field("algorithm_params") String algorithm_params, @Field("protected_columns") String[] protected_columns,
            @Field("total_information_threshold") double total_information_threshold,
            @Field("net_information_threshold") double net_information_threshold,
            @Field("relevance_index_threshold") double relevance_index_threshold,
            @Field("safety_index_threshold") double safety_index_threshold, @Field("data_fraction") double data_fraction,
            @Field("top_n_features") int top_n_features, @Field("model_id") String model_id, @Field("training_frame") String training_frame,
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
            @Field("stopping_tolerance") double stopping_tolerance, @Field("gainslift_bins") int gainslift_bins,
            @Field("custom_metric_func") String custom_metric_func, @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir, @Field("auc_type") MultinomialAucType auc_type);

    @FormUrlEncoded
    @POST("/3/ModelBuilders/infogram")
    Call<InfogramV3> trainInfogram();

    /**
     * Validate a set of Infogram model builder parameters.
     *   @param seed Seed for pseudo random number generator (if applicable).
     *   @param standardize Standardize numeric columns to have zero mean and unit variance.
     *   @param plug_values Plug Values (a single row frame containing values that will be used to impute missing values
     *                      of the training/validation frame, use with conjunction missing_values_handling = PlugValues).
     *   @param max_iterations Maximum number of iterations.
     *   @param prior Prior probability for y==1. To be used only for logistic regression iff the data has been sampled
     *                and the mean of response does not reflect reality.
     *   @param balance_classes Balance training data class counts via over/under-sampling (for imbalanced data).
     *   @param class_sampling_factors Desired over/under-sampling ratios per class (in lexicographic order). If not
     *                                 specified, sampling factors will be automatically computed to obtain class balance
     *                                 during training. Requires balance_classes.
     *   @param max_after_balance_size Maximum relative size of the training data after balancing class counts (can be
     *                                 less than 1.0). Requires balance_classes.
     *   @param algorithm Type of machine learning algorithm used to build the infogram. Options include 'AUTO' (gbm),
     *                    'deeplearning' (Deep Learning with default parameters), 'drf' (Random Forest with default
     *                    parameters), 'gbm' (GBM with default parameters), 'glm' (GLM with default parameters), or
     *                    'xgboost' (if available, XGBoost with default parameters).
     *   @param algorithm_params Customized parameters for the machine learning algorithm specified in the algorithm
     *                           parameter.
     *   @param protected_columns Columns that contain features that are sensitive and need to be protected (legally, or
     *                            otherwise), if applicable. These features (e.g. race, gender, etc) should not drive the
     *                            prediction of the response.
     *   @param total_information_threshold A number between 0 and 1 representing a threshold for total information,
     *                                      defaulting to 0.1. For a specific feature, if the total information is higher
     *                                      than this threshold, and the corresponding net information is also higher than
     *                                      the threshold ``net_information_threshold``, that feature will be considered
     *                                      admissible. The total information is the x-axis of the Core Infogram. Default
     *                                      is -1 which gets set to 0.1.
     *   @param net_information_threshold A number between 0 and 1 representing a threshold for net information,
     *                                    defaulting to 0.1.  For a specific feature, if the net information is higher
     *                                    than this threshold, and the corresponding total information is also higher than
     *                                    the total_information_threshold, that feature will be considered admissible. The
     *                                    net information is the y-axis of the Core Infogram. Default is -1 which gets set
     *                                    to 0.1.
     *   @param relevance_index_threshold A number between 0 and 1 representing a threshold for the relevance index,
     *                                    defaulting to 0.1.  This is only used when ``protected_columns`` is set by the
     *                                    user.  For a specific feature, if the relevance index value is higher than this
     *                                    threshold, and the corresponding safety index is also higher than the
     *                                    safety_index_threshold``, that feature will be considered admissible.  The
     *                                    relevance index is the x-axis of the Fair Infogram. Default is -1 which gets set
     *                                    to 0.1.
     *   @param safety_index_threshold A number between 0 and 1 representing a threshold for the safety index, defaulting
     *                                 to 0.1.  This is only used when protected_columns is set by the user.  For a
     *                                 specific feature, if the safety index value is higher than this threshold, and the
     *                                 corresponding relevance index is also higher than the relevance_index_threshold,
     *                                 that feature will be considered admissible.  The safety index is the y-axis of the
     *                                 Fair Infogram. Default is -1 which gets set to 0.1.
     *   @param data_fraction The fraction of training frame to use to build the infogram model. Defaults to 1.0, and any
     *                        value greater than 0 and less than or equal to 1.0 is acceptable.
     *   @param top_n_features An integer specifying the number of columns to evaluate in the infogram.  The columns are
     *                         ranked by variable importance, and the top N are evaluated.  Defaults to 50.
     *   @param model_id Destination id for this model; auto-generated if not specified.
     *   @param training_frame Id of the training data frame.
     *   @param validation_frame Id of the validation data frame.
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or >= 2).
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
     *                         If you set weight = 0 for a row, the returned prediction frame at that row is zero and this
     *                         is incorrect. To get an accurate prediction, remove all rows with weight == 0.
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
     *   @param gainslift_bins Gains/Lift table number of bins. 0 means disabled.. Default value -1 means automatic
     *                         binning.
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     *   @param auc_type Set default multinomial AUC type.
     */
    @FormUrlEncoded
    @POST("/3/ModelBuilders/infogram/parameters")
    Call<InfogramV3> validate_parametersInfogram(@Field("seed") long seed, @Field("standardize") boolean standardize,
            @Field("plug_values") String plug_values, @Field("max_iterations") int max_iterations, @Field("prior") double prior,
            @Field("balance_classes") boolean balance_classes, @Field("class_sampling_factors") float[] class_sampling_factors,
            @Field("max_after_balance_size") float max_after_balance_size, @Field("algorithm") InfogramAlgorithm algorithm,
            @Field("algorithm_params") String algorithm_params, @Field("protected_columns") String[] protected_columns,
            @Field("total_information_threshold") double total_information_threshold,
            @Field("net_information_threshold") double net_information_threshold,
            @Field("relevance_index_threshold") double relevance_index_threshold,
            @Field("safety_index_threshold") double safety_index_threshold, @Field("data_fraction") double data_fraction,
            @Field("top_n_features") int top_n_features, @Field("model_id") String model_id, @Field("training_frame") String training_frame,
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
            @Field("stopping_tolerance") double stopping_tolerance, @Field("gainslift_bins") int gainslift_bins,
            @Field("custom_metric_func") String custom_metric_func, @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir, @Field("auc_type") MultinomialAucType auc_type);

    @FormUrlEncoded
    @POST("/3/ModelBuilders/infogram/parameters")
    Call<InfogramV3> validate_parametersInfogram();

    /**
     * Train a TargetEncoder model.
     *   @param columns_to_encode List of categorical columns or groups of categorical columns to encode. When groups of
     *                            columns are specified, each group is encoded as a single column (interactions are
     *                            created internally).
     *   @param keep_original_categorical_columns If true, the original non-encoded categorical features will remain in
     *                                            the result frame.
     *   @param blending If true, enables blending of posterior probabilities (computed for a given categorical value)
     *                   with prior probabilities (computed on the entire set). This allows to mitigate the effect of
     *                   categorical values with small cardinality. The blending effect can be tuned using the
     *                   `inflection_point` and `smoothing` parameters.
     *   @param inflection_point Inflection point of the sigmoid used to blend probabilities (see `blending` parameter).
     *                           For a given categorical value, if it appears less that `inflection_point` in a data
     *                           sample, then the influence of the posterior probability will be smaller than the prior.
     *   @param smoothing Smoothing factor corresponds to the inverse of the slope at the inflection point on the sigmoid
     *                    used to blend probabilities (see `blending` parameter). If smoothing tends towards 0, then the
     *                    sigmoid used for blending turns into a Heaviside step function.
     *   @param data_leakage_handling Data leakage handling strategy used to generate the encoding. Supported options are:
     *                                1) "none" (default) - no holdout, using the entire training frame.
     *                                2) "leave_one_out" - current row's response value is subtracted from the per-level
     *                                frequencies pre-calculated on the entire training frame.
     *                                3) "k_fold" - encodings for a fold are generated based on out-of-fold data.
     *   @param noise The amount of noise to add to the encoded column. Use 0 to disable noise, and -1 (=AUTO) to let the
     *                algorithm determine a reasonable amount of noise.
     *   @param seed Seed used to generate the noise. By default, the seed is chosen randomly.
     *   @param model_id Destination id for this model; auto-generated if not specified.
     *   @param training_frame Id of the training data frame.
     *   @param validation_frame Id of the validation data frame.
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or >= 2).
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
     *                         If you set weight = 0 for a row, the returned prediction frame at that row is zero and this
     *                         is incorrect. To get an accurate prediction, remove all rows with weight == 0.
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
     *   @param gainslift_bins Gains/Lift table number of bins. 0 means disabled.. Default value -1 means automatic
     *                         binning.
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     *   @param auc_type Set default multinomial AUC type.
     */
    @FormUrlEncoded
    @POST("/3/ModelBuilders/targetencoder")
    Call<TargetEncoderV3> trainTargetencoder(@Field("columns_to_encode") String[][] columns_to_encode,
            @Field("keep_original_categorical_columns") boolean keep_original_categorical_columns, @Field("blending") boolean blending,
            @Field("inflection_point") double inflection_point, @Field("smoothing") double smoothing,
            @Field("data_leakage_handling") H2otargetencodingTargetEncoderModelDataLeakageHandlingStrategy data_leakage_handling,
            @Field("noise") double noise, @Field("seed") long seed, @Field("model_id") String model_id,
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
            @Field("stopping_tolerance") double stopping_tolerance, @Field("gainslift_bins") int gainslift_bins,
            @Field("custom_metric_func") String custom_metric_func, @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir, @Field("auc_type") MultinomialAucType auc_type);

    @FormUrlEncoded
    @POST("/3/ModelBuilders/targetencoder")
    Call<TargetEncoderV3> trainTargetencoder();

    /**
     * Validate a set of TargetEncoder model builder parameters.
     *   @param columns_to_encode List of categorical columns or groups of categorical columns to encode. When groups of
     *                            columns are specified, each group is encoded as a single column (interactions are
     *                            created internally).
     *   @param keep_original_categorical_columns If true, the original non-encoded categorical features will remain in
     *                                            the result frame.
     *   @param blending If true, enables blending of posterior probabilities (computed for a given categorical value)
     *                   with prior probabilities (computed on the entire set). This allows to mitigate the effect of
     *                   categorical values with small cardinality. The blending effect can be tuned using the
     *                   `inflection_point` and `smoothing` parameters.
     *   @param inflection_point Inflection point of the sigmoid used to blend probabilities (see `blending` parameter).
     *                           For a given categorical value, if it appears less that `inflection_point` in a data
     *                           sample, then the influence of the posterior probability will be smaller than the prior.
     *   @param smoothing Smoothing factor corresponds to the inverse of the slope at the inflection point on the sigmoid
     *                    used to blend probabilities (see `blending` parameter). If smoothing tends towards 0, then the
     *                    sigmoid used for blending turns into a Heaviside step function.
     *   @param data_leakage_handling Data leakage handling strategy used to generate the encoding. Supported options are:
     *                                1) "none" (default) - no holdout, using the entire training frame.
     *                                2) "leave_one_out" - current row's response value is subtracted from the per-level
     *                                frequencies pre-calculated on the entire training frame.
     *                                3) "k_fold" - encodings for a fold are generated based on out-of-fold data.
     *   @param noise The amount of noise to add to the encoded column. Use 0 to disable noise, and -1 (=AUTO) to let the
     *                algorithm determine a reasonable amount of noise.
     *   @param seed Seed used to generate the noise. By default, the seed is chosen randomly.
     *   @param model_id Destination id for this model; auto-generated if not specified.
     *   @param training_frame Id of the training data frame.
     *   @param validation_frame Id of the validation data frame.
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or >= 2).
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
     *                         If you set weight = 0 for a row, the returned prediction frame at that row is zero and this
     *                         is incorrect. To get an accurate prediction, remove all rows with weight == 0.
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
     *   @param gainslift_bins Gains/Lift table number of bins. 0 means disabled.. Default value -1 means automatic
     *                         binning.
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     *   @param auc_type Set default multinomial AUC type.
     */
    @FormUrlEncoded
    @POST("/3/ModelBuilders/targetencoder/parameters")
    Call<TargetEncoderV3> validate_parametersTargetencoder(@Field("columns_to_encode") String[][] columns_to_encode,
            @Field("keep_original_categorical_columns") boolean keep_original_categorical_columns, @Field("blending") boolean blending,
            @Field("inflection_point") double inflection_point, @Field("smoothing") double smoothing,
            @Field("data_leakage_handling") H2otargetencodingTargetEncoderModelDataLeakageHandlingStrategy data_leakage_handling,
            @Field("noise") double noise, @Field("seed") long seed, @Field("model_id") String model_id,
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
            @Field("stopping_tolerance") double stopping_tolerance, @Field("gainslift_bins") int gainslift_bins,
            @Field("custom_metric_func") String custom_metric_func, @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir, @Field("auc_type") MultinomialAucType auc_type);

    @FormUrlEncoded
    @POST("/3/ModelBuilders/targetencoder/parameters")
    Call<TargetEncoderV3> validate_parametersTargetencoder();

    /**
     * Train a DeepLearning model.
     *   @param balance_classes Balance training data class counts via over/under-sampling (for imbalanced data).
     *   @param class_sampling_factors Desired over/under-sampling ratios per class (in lexicographic order). If not
     *                                 specified, sampling factors will be automatically computed to obtain class balance
     *                                 during training. Requires balance_classes.
     *   @param max_after_balance_size Maximum relative size of the training data after balancing class counts (can be
     *                                 less than 1.0). Requires balance_classes.
     *   @param max_confusion_matrix_size [Deprecated] Maximum size (# classes) for confusion matrices to be printed in
     *                                    the Logs.
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
     *   @param rate Learning rate (higher => less stable, lower => slower convergence).
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
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or >= 2).
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
     *                         If you set weight = 0 for a row, the returned prediction frame at that row is zero and this
     *                         is incorrect. To get an accurate prediction, remove all rows with weight == 0.
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
     *   @param gainslift_bins Gains/Lift table number of bins. 0 means disabled.. Default value -1 means automatic
     *                         binning.
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     *   @param auc_type Set default multinomial AUC type.
     */
    @FormUrlEncoded
    @POST("/3/ModelBuilders/deeplearning")
    Call<DeepLearningV3> trainDeeplearning(@Field("balance_classes") boolean balance_classes,
            @Field("class_sampling_factors") float[] class_sampling_factors, @Field("max_after_balance_size") float max_after_balance_size,
            @Field("max_confusion_matrix_size") int max_confusion_matrix_size, @Field("activation") DeepLearningActivation activation,
            @Field("hidden") int[] hidden, @Field("epochs") double epochs,
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
            @Field("stopping_tolerance") double stopping_tolerance, @Field("gainslift_bins") int gainslift_bins,
            @Field("custom_metric_func") String custom_metric_func, @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir, @Field("auc_type") MultinomialAucType auc_type);

    @FormUrlEncoded
    @POST("/3/ModelBuilders/deeplearning")
    Call<DeepLearningV3> trainDeeplearning();

    /**
     * Validate a set of DeepLearning model builder parameters.
     *   @param balance_classes Balance training data class counts via over/under-sampling (for imbalanced data).
     *   @param class_sampling_factors Desired over/under-sampling ratios per class (in lexicographic order). If not
     *                                 specified, sampling factors will be automatically computed to obtain class balance
     *                                 during training. Requires balance_classes.
     *   @param max_after_balance_size Maximum relative size of the training data after balancing class counts (can be
     *                                 less than 1.0). Requires balance_classes.
     *   @param max_confusion_matrix_size [Deprecated] Maximum size (# classes) for confusion matrices to be printed in
     *                                    the Logs.
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
     *   @param rate Learning rate (higher => less stable, lower => slower convergence).
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
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or >= 2).
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
     *                         If you set weight = 0 for a row, the returned prediction frame at that row is zero and this
     *                         is incorrect. To get an accurate prediction, remove all rows with weight == 0.
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
     *   @param gainslift_bins Gains/Lift table number of bins. 0 means disabled.. Default value -1 means automatic
     *                         binning.
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     *   @param auc_type Set default multinomial AUC type.
     */
    @FormUrlEncoded
    @POST("/3/ModelBuilders/deeplearning/parameters")
    Call<DeepLearningV3> validate_parametersDeeplearning(@Field("balance_classes") boolean balance_classes,
            @Field("class_sampling_factors") float[] class_sampling_factors, @Field("max_after_balance_size") float max_after_balance_size,
            @Field("max_confusion_matrix_size") int max_confusion_matrix_size, @Field("activation") DeepLearningActivation activation,
            @Field("hidden") int[] hidden, @Field("epochs") double epochs,
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
            @Field("stopping_tolerance") double stopping_tolerance, @Field("gainslift_bins") int gainslift_bins,
            @Field("custom_metric_func") String custom_metric_func, @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir, @Field("auc_type") MultinomialAucType auc_type);

    @FormUrlEncoded
    @POST("/3/ModelBuilders/deeplearning/parameters")
    Call<DeepLearningV3> validate_parametersDeeplearning();

    /**
     * Train a GLM model.
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
     *   @param score_iteration_interval Perform scoring for every score_iteration_interval iterations
     *   @param standardize Standardize numeric columns to have zero mean and unit variance
     *   @param cold_start Only applicable to multiple alpha/lambda values.  If false, build the next model for next set
     *                     of alpha/lambda values starting from the values provided by current model.  If true will start
     *                     GLM model from scratch.
     *   @param missing_values_handling Handling of missing values. Either MeanImputation, Skip or PlugValues.
     *   @param plug_values Plug Values (a single row frame containing values that will be used to impute missing values
     *                      of the training/validation frame, use with conjunction missing_values_handling = PlugValues)
     *   @param non_negative Restrict coefficients (not intercept) to be non-negative
     *   @param max_iterations Maximum number of iterations
     *   @param beta_epsilon Converge if  beta changes less (using L-infinity norm) than beta esilon, ONLY applies to
     *                       IRLSM solver
     *   @param objective_epsilon Converge if  objective value changes less than this. Default (of -1.0) indicates: If
     *                            lambda_search is set to True the value of objective_epsilon is set to .0001. If the
     *                            lambda_search is set to False and lambda is equal to zero, the value of
     *                            objective_epsilon is set to .000001, for any other value of lambda the default value of
     *                            objective_epsilon is set to .0001.
     *   @param gradient_epsilon Converge if  objective changes less (using L-infinity norm) than this, ONLY applies to
     *                           L-BFGS solver. Default (of -1.0) indicates: If lambda_search is set to False and lambda
     *                           is equal to zero, the default value of gradient_epsilon is equal to .000001, otherwise
     *                           the default value is .0001. If lambda_search is set to True, the conditional values above
     *                           are 1E-8 and 1E-6 respectively.
     *   @param obj_reg Likelihood divider in objective value computation, default (of -1.0) will set it to 1/nobs
     *   @param link Link function.
     *   @param rand_link Link function array for random component in HGLM.
     *   @param startval double array to initialize fixed and random coefficients for HGLM, coefficients for GLM.
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
     *   @param compute_p_values Request p-values computation, p-values work only with IRLSM solver and no regularization
     *   @param remove_collinear_columns In case of linearly dependent columns, remove some of the dependent columns
     *   @param generate_scoring_history If set to true, will generate scoring history for GLM.  This may significantly
     *                                   slow down the algo.
     *   @param model_id Destination id for this model; auto-generated if not specified.
     *   @param training_frame Id of the training data frame.
     *   @param validation_frame Id of the validation data frame.
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or >= 2).
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
     *                         If you set weight = 0 for a row, the returned prediction frame at that row is zero and this
     *                         is incorrect. To get an accurate prediction, remove all rows with weight == 0.
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
     *   @param gainslift_bins Gains/Lift table number of bins. 0 means disabled.. Default value -1 means automatic
     *                         binning.
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     *   @param auc_type Set default multinomial AUC type.
     */
    @FormUrlEncoded
    @POST("/3/ModelBuilders/glm")
    Call<GLMV3> trainGlm(@Field("seed") long seed, @Field("family") GLMFamily family, @Field("rand_family") GLMFamily[] rand_family,
            @Field("tweedie_variance_power") double tweedie_variance_power, @Field("tweedie_link_power") double tweedie_link_power,
            @Field("theta") double theta, @Field("solver") GLMSolver solver, @Field("alpha") double[] alpha,
            @Field("lambda") double[] lambda, @Field("lambda_search") boolean lambda_search,
            @Field("early_stopping") boolean early_stopping, @Field("nlambdas") int nlambdas,
            @Field("score_iteration_interval") int score_iteration_interval, @Field("standardize") boolean standardize,
            @Field("cold_start") boolean cold_start, @Field("missing_values_handling") GLMMissingValuesHandling missing_values_handling,
            @Field("plug_values") String plug_values, @Field("non_negative") boolean non_negative,
            @Field("max_iterations") int max_iterations, @Field("beta_epsilon") double beta_epsilon,
            @Field("objective_epsilon") double objective_epsilon, @Field("gradient_epsilon") double gradient_epsilon,
            @Field("obj_reg") double obj_reg, @Field("link") GLMLink link, @Field("rand_link") GLMLink[] rand_link,
            @Field("startval") double[] startval, @Field("random_columns") int[] random_columns, @Field("calc_like") boolean calc_like,
            @Field("intercept") boolean intercept, @Field("HGLM") boolean HGLM, @Field("prior") double prior,
            @Field("lambda_min_ratio") double lambda_min_ratio, @Field("beta_constraints") String beta_constraints,
            @Field("max_active_predictors") int max_active_predictors, @Field("interactions") String[] interactions,
            @Field("interaction_pairs") StringPairV3[] interaction_pairs, @Field("balance_classes") boolean balance_classes,
            @Field("class_sampling_factors") float[] class_sampling_factors, @Field("max_after_balance_size") float max_after_balance_size,
            @Field("max_confusion_matrix_size") int max_confusion_matrix_size, @Field("compute_p_values") boolean compute_p_values,
            @Field("remove_collinear_columns") boolean remove_collinear_columns,
            @Field("generate_scoring_history") boolean generate_scoring_history, @Field("model_id") String model_id,
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
            @Field("stopping_tolerance") double stopping_tolerance, @Field("gainslift_bins") int gainslift_bins,
            @Field("custom_metric_func") String custom_metric_func, @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir, @Field("auc_type") MultinomialAucType auc_type);

    @FormUrlEncoded
    @POST("/3/ModelBuilders/glm")
    Call<GLMV3> trainGlm();

    /**
     * Validate a set of GLM model builder parameters.
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
     *   @param score_iteration_interval Perform scoring for every score_iteration_interval iterations
     *   @param standardize Standardize numeric columns to have zero mean and unit variance
     *   @param cold_start Only applicable to multiple alpha/lambda values.  If false, build the next model for next set
     *                     of alpha/lambda values starting from the values provided by current model.  If true will start
     *                     GLM model from scratch.
     *   @param missing_values_handling Handling of missing values. Either MeanImputation, Skip or PlugValues.
     *   @param plug_values Plug Values (a single row frame containing values that will be used to impute missing values
     *                      of the training/validation frame, use with conjunction missing_values_handling = PlugValues)
     *   @param non_negative Restrict coefficients (not intercept) to be non-negative
     *   @param max_iterations Maximum number of iterations
     *   @param beta_epsilon Converge if  beta changes less (using L-infinity norm) than beta esilon, ONLY applies to
     *                       IRLSM solver
     *   @param objective_epsilon Converge if  objective value changes less than this. Default (of -1.0) indicates: If
     *                            lambda_search is set to True the value of objective_epsilon is set to .0001. If the
     *                            lambda_search is set to False and lambda is equal to zero, the value of
     *                            objective_epsilon is set to .000001, for any other value of lambda the default value of
     *                            objective_epsilon is set to .0001.
     *   @param gradient_epsilon Converge if  objective changes less (using L-infinity norm) than this, ONLY applies to
     *                           L-BFGS solver. Default (of -1.0) indicates: If lambda_search is set to False and lambda
     *                           is equal to zero, the default value of gradient_epsilon is equal to .000001, otherwise
     *                           the default value is .0001. If lambda_search is set to True, the conditional values above
     *                           are 1E-8 and 1E-6 respectively.
     *   @param obj_reg Likelihood divider in objective value computation, default (of -1.0) will set it to 1/nobs
     *   @param link Link function.
     *   @param rand_link Link function array for random component in HGLM.
     *   @param startval double array to initialize fixed and random coefficients for HGLM, coefficients for GLM.
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
     *   @param compute_p_values Request p-values computation, p-values work only with IRLSM solver and no regularization
     *   @param remove_collinear_columns In case of linearly dependent columns, remove some of the dependent columns
     *   @param generate_scoring_history If set to true, will generate scoring history for GLM.  This may significantly
     *                                   slow down the algo.
     *   @param model_id Destination id for this model; auto-generated if not specified.
     *   @param training_frame Id of the training data frame.
     *   @param validation_frame Id of the validation data frame.
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or >= 2).
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
     *                         If you set weight = 0 for a row, the returned prediction frame at that row is zero and this
     *                         is incorrect. To get an accurate prediction, remove all rows with weight == 0.
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
     *   @param gainslift_bins Gains/Lift table number of bins. 0 means disabled.. Default value -1 means automatic
     *                         binning.
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     *   @param auc_type Set default multinomial AUC type.
     */
    @FormUrlEncoded
    @POST("/3/ModelBuilders/glm/parameters")
    Call<GLMV3> validate_parametersGlm(@Field("seed") long seed, @Field("family") GLMFamily family,
            @Field("rand_family") GLMFamily[] rand_family, @Field("tweedie_variance_power") double tweedie_variance_power,
            @Field("tweedie_link_power") double tweedie_link_power, @Field("theta") double theta, @Field("solver") GLMSolver solver,
            @Field("alpha") double[] alpha, @Field("lambda") double[] lambda, @Field("lambda_search") boolean lambda_search,
            @Field("early_stopping") boolean early_stopping, @Field("nlambdas") int nlambdas,
            @Field("score_iteration_interval") int score_iteration_interval, @Field("standardize") boolean standardize,
            @Field("cold_start") boolean cold_start, @Field("missing_values_handling") GLMMissingValuesHandling missing_values_handling,
            @Field("plug_values") String plug_values, @Field("non_negative") boolean non_negative,
            @Field("max_iterations") int max_iterations, @Field("beta_epsilon") double beta_epsilon,
            @Field("objective_epsilon") double objective_epsilon, @Field("gradient_epsilon") double gradient_epsilon,
            @Field("obj_reg") double obj_reg, @Field("link") GLMLink link, @Field("rand_link") GLMLink[] rand_link,
            @Field("startval") double[] startval, @Field("random_columns") int[] random_columns, @Field("calc_like") boolean calc_like,
            @Field("intercept") boolean intercept, @Field("HGLM") boolean HGLM, @Field("prior") double prior,
            @Field("lambda_min_ratio") double lambda_min_ratio, @Field("beta_constraints") String beta_constraints,
            @Field("max_active_predictors") int max_active_predictors, @Field("interactions") String[] interactions,
            @Field("interaction_pairs") StringPairV3[] interaction_pairs, @Field("balance_classes") boolean balance_classes,
            @Field("class_sampling_factors") float[] class_sampling_factors, @Field("max_after_balance_size") float max_after_balance_size,
            @Field("max_confusion_matrix_size") int max_confusion_matrix_size, @Field("compute_p_values") boolean compute_p_values,
            @Field("remove_collinear_columns") boolean remove_collinear_columns,
            @Field("generate_scoring_history") boolean generate_scoring_history, @Field("model_id") String model_id,
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
            @Field("stopping_tolerance") double stopping_tolerance, @Field("gainslift_bins") int gainslift_bins,
            @Field("custom_metric_func") String custom_metric_func, @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir, @Field("auc_type") MultinomialAucType auc_type);

    @FormUrlEncoded
    @POST("/3/ModelBuilders/glm/parameters")
    Call<GLMV3> validate_parametersGlm();

    /**
     * Train a GLRM model.
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
     *   @param loading_name [Deprecated] Use representation_name instead.  Frame key to save resulting X.
     *   @param representation_name Frame key to save resulting X
     *   @param expand_user_y Expand categorical columns in user-specified initial Y
     *   @param impute_original Reconstruct original training data by reversing transform
     *   @param recover_svd Recover singular values and eigenvectors of XY
     *   @param model_id Destination id for this model; auto-generated if not specified.
     *   @param training_frame Id of the training data frame.
     *   @param validation_frame Id of the validation data frame.
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or >= 2).
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
     *                         If you set weight = 0 for a row, the returned prediction frame at that row is zero and this
     *                         is incorrect. To get an accurate prediction, remove all rows with weight == 0.
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
     *   @param gainslift_bins Gains/Lift table number of bins. 0 means disabled.. Default value -1 means automatic
     *                         binning.
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     *   @param auc_type Set default multinomial AUC type.
     */
    @FormUrlEncoded
    @POST("/3/ModelBuilders/glrm")
    Call<GLRMV3> trainGlrm(@Field("transform") DataInfoTransformType transform, @Field("k") int k,
            @Field("loss") GenmodelalgosglrmGlrmLoss loss, @Field("multi_loss") GenmodelalgosglrmGlrmLoss multi_loss,
            @Field("loss_by_col") GenmodelalgosglrmGlrmLoss[] loss_by_col, @Field("loss_by_col_idx") int[] loss_by_col_idx,
            @Field("period") int period, @Field("regularization_x") GenmodelalgosglrmGlrmRegularizer regularization_x,
            @Field("regularization_y") GenmodelalgosglrmGlrmRegularizer regularization_y, @Field("gamma_x") double gamma_x,
            @Field("gamma_y") double gamma_y, @Field("max_iterations") int max_iterations, @Field("max_updates") int max_updates,
            @Field("init_step_size") double init_step_size, @Field("min_step_size") double min_step_size, @Field("seed") long seed,
            @Field("init") GenmodelalgosglrmGlrmInitialization init, @Field("svd_method") SVDMethod svd_method,
            @Field("user_y") String user_y, @Field("user_x") String user_x, @Field("loading_name") String loading_name,
            @Field("representation_name") String representation_name, @Field("expand_user_y") boolean expand_user_y,
            @Field("impute_original") boolean impute_original, @Field("recover_svd") boolean recover_svd,
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
            @Field("stopping_tolerance") double stopping_tolerance, @Field("gainslift_bins") int gainslift_bins,
            @Field("custom_metric_func") String custom_metric_func, @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir, @Field("auc_type") MultinomialAucType auc_type);

    @FormUrlEncoded
    @POST("/3/ModelBuilders/glrm")
    Call<GLRMV3> trainGlrm(@Field("k") int k);

    /**
     * Validate a set of GLRM model builder parameters.
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
     *   @param loading_name [Deprecated] Use representation_name instead.  Frame key to save resulting X.
     *   @param representation_name Frame key to save resulting X
     *   @param expand_user_y Expand categorical columns in user-specified initial Y
     *   @param impute_original Reconstruct original training data by reversing transform
     *   @param recover_svd Recover singular values and eigenvectors of XY
     *   @param model_id Destination id for this model; auto-generated if not specified.
     *   @param training_frame Id of the training data frame.
     *   @param validation_frame Id of the validation data frame.
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or >= 2).
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
     *                         If you set weight = 0 for a row, the returned prediction frame at that row is zero and this
     *                         is incorrect. To get an accurate prediction, remove all rows with weight == 0.
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
     *   @param gainslift_bins Gains/Lift table number of bins. 0 means disabled.. Default value -1 means automatic
     *                         binning.
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     *   @param auc_type Set default multinomial AUC type.
     */
    @FormUrlEncoded
    @POST("/3/ModelBuilders/glrm/parameters")
    Call<GLRMV3> validate_parametersGlrm(@Field("transform") DataInfoTransformType transform, @Field("k") int k,
            @Field("loss") GenmodelalgosglrmGlrmLoss loss, @Field("multi_loss") GenmodelalgosglrmGlrmLoss multi_loss,
            @Field("loss_by_col") GenmodelalgosglrmGlrmLoss[] loss_by_col, @Field("loss_by_col_idx") int[] loss_by_col_idx,
            @Field("period") int period, @Field("regularization_x") GenmodelalgosglrmGlrmRegularizer regularization_x,
            @Field("regularization_y") GenmodelalgosglrmGlrmRegularizer regularization_y, @Field("gamma_x") double gamma_x,
            @Field("gamma_y") double gamma_y, @Field("max_iterations") int max_iterations, @Field("max_updates") int max_updates,
            @Field("init_step_size") double init_step_size, @Field("min_step_size") double min_step_size, @Field("seed") long seed,
            @Field("init") GenmodelalgosglrmGlrmInitialization init, @Field("svd_method") SVDMethod svd_method,
            @Field("user_y") String user_y, @Field("user_x") String user_x, @Field("loading_name") String loading_name,
            @Field("representation_name") String representation_name, @Field("expand_user_y") boolean expand_user_y,
            @Field("impute_original") boolean impute_original, @Field("recover_svd") boolean recover_svd,
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
            @Field("stopping_tolerance") double stopping_tolerance, @Field("gainslift_bins") int gainslift_bins,
            @Field("custom_metric_func") String custom_metric_func, @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir, @Field("auc_type") MultinomialAucType auc_type);

    @FormUrlEncoded
    @POST("/3/ModelBuilders/glrm/parameters")
    Call<GLRMV3> validate_parametersGlrm(@Field("k") int k);

    /**
     * Train a KMeans model.
     *   @param user_points This option allows you to specify a dataframe, where each row represents an initial cluster
     *                      center. The user-specified points must have the same number of columns as the training
     *                      observations. The number of rows must equal the number of clusters
     *   @param max_iterations Maximum training iterations (if estimate_k is enabled, then this is for each inner Lloyds
     *                         iteration)
     *   @param standardize Standardize columns before computing distances
     *   @param seed RNG Seed
     *   @param init Initialization mode
     *   @param estimate_k Whether to estimate the number of clusters (&lt;=k) iteratively and deterministically.
     *   @param cluster_size_constraints An array specifying the minimum number of points that should be in each cluster.
     *                                   The length of the constraints array has to be the same as the number of clusters.
     *   @param k The max. number of clusters. If estimate_k is disabled, the model will find k centroids, otherwise it
     *            will find up to k centroids.
     *   @param model_id Destination id for this model; auto-generated if not specified.
     *   @param training_frame Id of the training data frame.
     *   @param validation_frame Id of the validation data frame.
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or >= 2).
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
     *                         If you set weight = 0 for a row, the returned prediction frame at that row is zero and this
     *                         is incorrect. To get an accurate prediction, remove all rows with weight == 0.
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
     *   @param gainslift_bins Gains/Lift table number of bins. 0 means disabled.. Default value -1 means automatic
     *                         binning.
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     *   @param auc_type Set default multinomial AUC type.
     */
    @FormUrlEncoded
    @POST("/3/ModelBuilders/kmeans")
    Call<KMeansV3> trainKmeans(@Field("user_points") String user_points, @Field("max_iterations") int max_iterations,
            @Field("standardize") boolean standardize, @Field("seed") long seed, @Field("init") KMeansInitialization init,
            @Field("estimate_k") boolean estimate_k, @Field("cluster_size_constraints") int[] cluster_size_constraints, @Field("k") int k,
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
            @Field("stopping_tolerance") double stopping_tolerance, @Field("gainslift_bins") int gainslift_bins,
            @Field("custom_metric_func") String custom_metric_func, @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir, @Field("auc_type") MultinomialAucType auc_type);

    @FormUrlEncoded
    @POST("/3/ModelBuilders/kmeans")
    Call<KMeansV3> trainKmeans();

    /**
     * Validate a set of KMeans model builder parameters.
     *   @param user_points This option allows you to specify a dataframe, where each row represents an initial cluster
     *                      center. The user-specified points must have the same number of columns as the training
     *                      observations. The number of rows must equal the number of clusters
     *   @param max_iterations Maximum training iterations (if estimate_k is enabled, then this is for each inner Lloyds
     *                         iteration)
     *   @param standardize Standardize columns before computing distances
     *   @param seed RNG Seed
     *   @param init Initialization mode
     *   @param estimate_k Whether to estimate the number of clusters (&lt;=k) iteratively and deterministically.
     *   @param cluster_size_constraints An array specifying the minimum number of points that should be in each cluster.
     *                                   The length of the constraints array has to be the same as the number of clusters.
     *   @param k The max. number of clusters. If estimate_k is disabled, the model will find k centroids, otherwise it
     *            will find up to k centroids.
     *   @param model_id Destination id for this model; auto-generated if not specified.
     *   @param training_frame Id of the training data frame.
     *   @param validation_frame Id of the validation data frame.
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or >= 2).
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
     *                         If you set weight = 0 for a row, the returned prediction frame at that row is zero and this
     *                         is incorrect. To get an accurate prediction, remove all rows with weight == 0.
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
     *   @param gainslift_bins Gains/Lift table number of bins. 0 means disabled.. Default value -1 means automatic
     *                         binning.
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     *   @param auc_type Set default multinomial AUC type.
     */
    @FormUrlEncoded
    @POST("/3/ModelBuilders/kmeans/parameters")
    Call<KMeansV3> validate_parametersKmeans(@Field("user_points") String user_points, @Field("max_iterations") int max_iterations,
            @Field("standardize") boolean standardize, @Field("seed") long seed, @Field("init") KMeansInitialization init,
            @Field("estimate_k") boolean estimate_k, @Field("cluster_size_constraints") int[] cluster_size_constraints, @Field("k") int k,
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
            @Field("stopping_tolerance") double stopping_tolerance, @Field("gainslift_bins") int gainslift_bins,
            @Field("custom_metric_func") String custom_metric_func, @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir, @Field("auc_type") MultinomialAucType auc_type);

    @FormUrlEncoded
    @POST("/3/ModelBuilders/kmeans/parameters")
    Call<KMeansV3> validate_parametersKmeans();

    /**
     * Train a NaiveBayes model.
     *   @param balance_classes Balance training data class counts via over/under-sampling (for imbalanced data).
     *   @param class_sampling_factors Desired over/under-sampling ratios per class (in lexicographic order). If not
     *                                 specified, sampling factors will be automatically computed to obtain class balance
     *                                 during training. Requires balance_classes.
     *   @param max_after_balance_size Maximum relative size of the training data after balancing class counts (can be
     *                                 less than 1.0). Requires balance_classes.
     *   @param max_confusion_matrix_size [Deprecated] Maximum size (# classes) for confusion matrices to be printed in
     *                                    the Logs
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
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or >= 2).
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
     *                         If you set weight = 0 for a row, the returned prediction frame at that row is zero and this
     *                         is incorrect. To get an accurate prediction, remove all rows with weight == 0.
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
     *   @param gainslift_bins Gains/Lift table number of bins. 0 means disabled.. Default value -1 means automatic
     *                         binning.
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     *   @param auc_type Set default multinomial AUC type.
     */
    @FormUrlEncoded
    @POST("/3/ModelBuilders/naivebayes")
    Call<NaiveBayesV3> trainNaivebayes(@Field("balance_classes") boolean balance_classes,
            @Field("class_sampling_factors") float[] class_sampling_factors, @Field("max_after_balance_size") float max_after_balance_size,
            @Field("max_confusion_matrix_size") int max_confusion_matrix_size, @Field("laplace") double laplace,
            @Field("min_sdev") double min_sdev, @Field("eps_sdev") double eps_sdev, @Field("min_prob") double min_prob,
            @Field("eps_prob") double eps_prob, @Field("compute_metrics") boolean compute_metrics, @Field("seed") long seed,
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
            @Field("stopping_tolerance") double stopping_tolerance, @Field("gainslift_bins") int gainslift_bins,
            @Field("custom_metric_func") String custom_metric_func, @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir, @Field("auc_type") MultinomialAucType auc_type);

    @FormUrlEncoded
    @POST("/3/ModelBuilders/naivebayes")
    Call<NaiveBayesV3> trainNaivebayes();

    /**
     * Validate a set of NaiveBayes model builder parameters.
     *   @param balance_classes Balance training data class counts via over/under-sampling (for imbalanced data).
     *   @param class_sampling_factors Desired over/under-sampling ratios per class (in lexicographic order). If not
     *                                 specified, sampling factors will be automatically computed to obtain class balance
     *                                 during training. Requires balance_classes.
     *   @param max_after_balance_size Maximum relative size of the training data after balancing class counts (can be
     *                                 less than 1.0). Requires balance_classes.
     *   @param max_confusion_matrix_size [Deprecated] Maximum size (# classes) for confusion matrices to be printed in
     *                                    the Logs
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
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or >= 2).
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
     *                         If you set weight = 0 for a row, the returned prediction frame at that row is zero and this
     *                         is incorrect. To get an accurate prediction, remove all rows with weight == 0.
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
     *   @param gainslift_bins Gains/Lift table number of bins. 0 means disabled.. Default value -1 means automatic
     *                         binning.
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     *   @param auc_type Set default multinomial AUC type.
     */
    @FormUrlEncoded
    @POST("/3/ModelBuilders/naivebayes/parameters")
    Call<NaiveBayesV3> validate_parametersNaivebayes(@Field("balance_classes") boolean balance_classes,
            @Field("class_sampling_factors") float[] class_sampling_factors, @Field("max_after_balance_size") float max_after_balance_size,
            @Field("max_confusion_matrix_size") int max_confusion_matrix_size, @Field("laplace") double laplace,
            @Field("min_sdev") double min_sdev, @Field("eps_sdev") double eps_sdev, @Field("min_prob") double min_prob,
            @Field("eps_prob") double eps_prob, @Field("compute_metrics") boolean compute_metrics, @Field("seed") long seed,
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
            @Field("stopping_tolerance") double stopping_tolerance, @Field("gainslift_bins") int gainslift_bins,
            @Field("custom_metric_func") String custom_metric_func, @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir, @Field("auc_type") MultinomialAucType auc_type);

    @FormUrlEncoded
    @POST("/3/ModelBuilders/naivebayes/parameters")
    Call<NaiveBayesV3> validate_parametersNaivebayes();

    /**
     * Train a PCA model.
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
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or >= 2).
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
     *                         If you set weight = 0 for a row, the returned prediction frame at that row is zero and this
     *                         is incorrect. To get an accurate prediction, remove all rows with weight == 0.
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
     *   @param gainslift_bins Gains/Lift table number of bins. 0 means disabled.. Default value -1 means automatic
     *                         binning.
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     *   @param auc_type Set default multinomial AUC type.
     */
    @FormUrlEncoded
    @POST("/3/ModelBuilders/pca")
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
            @Field("stopping_tolerance") double stopping_tolerance, @Field("gainslift_bins") int gainslift_bins,
            @Field("custom_metric_func") String custom_metric_func, @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir, @Field("auc_type") MultinomialAucType auc_type);

    @FormUrlEncoded
    @POST("/3/ModelBuilders/pca")
    Call<PCAV3> trainPca(@Field("k") int k);

    /**
     * Validate a set of PCA model builder parameters.
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
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or >= 2).
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
     *                         If you set weight = 0 for a row, the returned prediction frame at that row is zero and this
     *                         is incorrect. To get an accurate prediction, remove all rows with weight == 0.
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
     *   @param gainslift_bins Gains/Lift table number of bins. 0 means disabled.. Default value -1 means automatic
     *                         binning.
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     *   @param auc_type Set default multinomial AUC type.
     */
    @FormUrlEncoded
    @POST("/3/ModelBuilders/pca/parameters")
    Call<PCAV3> validate_parametersPca(@Field("transform") DataInfoTransformType transform, @Field("pca_method") PCAMethod pca_method,
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
            @Field("stopping_tolerance") double stopping_tolerance, @Field("gainslift_bins") int gainslift_bins,
            @Field("custom_metric_func") String custom_metric_func, @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir, @Field("auc_type") MultinomialAucType auc_type);

    @FormUrlEncoded
    @POST("/3/ModelBuilders/pca/parameters")
    Call<PCAV3> validate_parametersPca(@Field("k") int k);

    /**
     * Train a SVD model.
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
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or >= 2).
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
     *                         If you set weight = 0 for a row, the returned prediction frame at that row is zero and this
     *                         is incorrect. To get an accurate prediction, remove all rows with weight == 0.
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
     *   @param gainslift_bins Gains/Lift table number of bins. 0 means disabled.. Default value -1 means automatic
     *                         binning.
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     *   @param auc_type Set default multinomial AUC type.
     */
    @FormUrlEncoded
    @POST("/99/ModelBuilders/svd")
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
            @Field("stopping_tolerance") double stopping_tolerance, @Field("gainslift_bins") int gainslift_bins,
            @Field("custom_metric_func") String custom_metric_func, @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir, @Field("auc_type") MultinomialAucType auc_type);

    @FormUrlEncoded
    @POST("/99/ModelBuilders/svd")
    Call<SVDV99> trainSvd();

    /**
     * Validate a set of SVD model builder parameters.
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
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or >= 2).
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
     *                         If you set weight = 0 for a row, the returned prediction frame at that row is zero and this
     *                         is incorrect. To get an accurate prediction, remove all rows with weight == 0.
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
     *   @param gainslift_bins Gains/Lift table number of bins. 0 means disabled.. Default value -1 means automatic
     *                         binning.
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     *   @param auc_type Set default multinomial AUC type.
     */
    @FormUrlEncoded
    @POST("/99/ModelBuilders/svd/parameters")
    Call<SVDV99> validate_parametersSvd(@Field("transform") DataInfoTransformType transform, @Field("svd_method") SVDMethod svd_method,
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
            @Field("stopping_tolerance") double stopping_tolerance, @Field("gainslift_bins") int gainslift_bins,
            @Field("custom_metric_func") String custom_metric_func, @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir, @Field("auc_type") MultinomialAucType auc_type);

    @FormUrlEncoded
    @POST("/99/ModelBuilders/svd/parameters")
    Call<SVDV99> validate_parametersSvd();

    /**
     * Train a DRF model.
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
     *   @param ntrees Number of trees.
     *   @param max_depth Maximum tree depth (0 for unlimited).
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
     *   @param build_tree_one_node Run on one node only; no network overhead but fewer cpus used. Suitable for small
     *                              datasets.
     *   @param sample_rate_per_class A list of row sample rates per class (relative fraction for each class, from 0.0 to
     *                                1.0), for each tree
     *   @param col_sample_rate_per_tree Column sample rate per tree (from 0.0 to 1.0)
     *   @param col_sample_rate_change_per_level Relative change of the column sampling rate for every level (must be >
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
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or >= 2).
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
     *                         If you set weight = 0 for a row, the returned prediction frame at that row is zero and this
     *                         is incorrect. To get an accurate prediction, remove all rows with weight == 0.
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
     *   @param gainslift_bins Gains/Lift table number of bins. 0 means disabled.. Default value -1 means automatic
     *                         binning.
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     *   @param auc_type Set default multinomial AUC type.
     */
    @FormUrlEncoded
    @POST("/3/ModelBuilders/drf")
    Call<DRFV3> trainDrf(@Field("mtries") int mtries, @Field("binomial_double_trees") boolean binomial_double_trees,
            @Field("sample_rate") double sample_rate, @Field("balance_classes") boolean balance_classes,
            @Field("class_sampling_factors") float[] class_sampling_factors, @Field("max_after_balance_size") float max_after_balance_size,
            @Field("max_confusion_matrix_size") int max_confusion_matrix_size, @Field("ntrees") int ntrees,
            @Field("max_depth") int max_depth, @Field("min_rows") double min_rows, @Field("nbins") int nbins,
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
            @Field("stopping_tolerance") double stopping_tolerance, @Field("gainslift_bins") int gainslift_bins,
            @Field("custom_metric_func") String custom_metric_func, @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir, @Field("auc_type") MultinomialAucType auc_type);

    @FormUrlEncoded
    @POST("/3/ModelBuilders/drf")
    Call<DRFV3> trainDrf();

    /**
     * Validate a set of DRF model builder parameters.
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
     *   @param ntrees Number of trees.
     *   @param max_depth Maximum tree depth (0 for unlimited).
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
     *   @param build_tree_one_node Run on one node only; no network overhead but fewer cpus used. Suitable for small
     *                              datasets.
     *   @param sample_rate_per_class A list of row sample rates per class (relative fraction for each class, from 0.0 to
     *                                1.0), for each tree
     *   @param col_sample_rate_per_tree Column sample rate per tree (from 0.0 to 1.0)
     *   @param col_sample_rate_change_per_level Relative change of the column sampling rate for every level (must be >
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
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or >= 2).
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
     *                         If you set weight = 0 for a row, the returned prediction frame at that row is zero and this
     *                         is incorrect. To get an accurate prediction, remove all rows with weight == 0.
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
     *   @param gainslift_bins Gains/Lift table number of bins. 0 means disabled.. Default value -1 means automatic
     *                         binning.
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     *   @param auc_type Set default multinomial AUC type.
     */
    @FormUrlEncoded
    @POST("/3/ModelBuilders/drf/parameters")
    Call<DRFV3> validate_parametersDrf(@Field("mtries") int mtries, @Field("binomial_double_trees") boolean binomial_double_trees,
            @Field("sample_rate") double sample_rate, @Field("balance_classes") boolean balance_classes,
            @Field("class_sampling_factors") float[] class_sampling_factors, @Field("max_after_balance_size") float max_after_balance_size,
            @Field("max_confusion_matrix_size") int max_confusion_matrix_size, @Field("ntrees") int ntrees,
            @Field("max_depth") int max_depth, @Field("min_rows") double min_rows, @Field("nbins") int nbins,
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
            @Field("stopping_tolerance") double stopping_tolerance, @Field("gainslift_bins") int gainslift_bins,
            @Field("custom_metric_func") String custom_metric_func, @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir, @Field("auc_type") MultinomialAucType auc_type);

    @FormUrlEncoded
    @POST("/3/ModelBuilders/drf/parameters")
    Call<DRFV3> validate_parametersDrf();

    /**
     * Train a GBM model.
     *   @param learn_rate Learning rate (from 0.0 to 1.0)
     *   @param learn_rate_annealing Scale the learning rate by this factor after each tree (e.g., 0.99 or 0.999)
     *   @param sample_rate Row sample rate per tree (from 0.0 to 1.0)
     *   @param col_sample_rate Column sample rate (from 0.0 to 1.0)
     *   @param monotone_constraints A mapping representing monotonic constraints. Use +1 to enforce an increasing
     *                               constraint and -1 to specify a decreasing constraint.
     *   @param max_abs_leafnode_pred Maximum absolute value of a leaf node prediction
     *   @param pred_noise_bandwidth Bandwidth (sigma) of Gaussian multiplicative noise ~N(1,sigma) for tree node
     *                               predictions
     *   @param interaction_constraints A set of allowed column interactions.
     *   @param balance_classes Balance training data class counts via over/under-sampling (for imbalanced data).
     *   @param class_sampling_factors Desired over/under-sampling ratios per class (in lexicographic order). If not
     *                                 specified, sampling factors will be automatically computed to obtain class balance
     *                                 during training. Requires balance_classes.
     *   @param max_after_balance_size Maximum relative size of the training data after balancing class counts (can be
     *                                 less than 1.0). Requires balance_classes.
     *   @param max_confusion_matrix_size [Deprecated] Maximum size (# classes) for confusion matrices to be printed in
     *                                    the Logs
     *   @param ntrees Number of trees.
     *   @param max_depth Maximum tree depth (0 for unlimited).
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
     *   @param build_tree_one_node Run on one node only; no network overhead but fewer cpus used. Suitable for small
     *                              datasets.
     *   @param sample_rate_per_class A list of row sample rates per class (relative fraction for each class, from 0.0 to
     *                                1.0), for each tree
     *   @param col_sample_rate_per_tree Column sample rate per tree (from 0.0 to 1.0)
     *   @param col_sample_rate_change_per_level Relative change of the column sampling rate for every level (must be >
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
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or >= 2).
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
     *                         If you set weight = 0 for a row, the returned prediction frame at that row is zero and this
     *                         is incorrect. To get an accurate prediction, remove all rows with weight == 0.
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
     *   @param gainslift_bins Gains/Lift table number of bins. 0 means disabled.. Default value -1 means automatic
     *                         binning.
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     *   @param auc_type Set default multinomial AUC type.
     */
    @FormUrlEncoded
    @POST("/3/ModelBuilders/gbm")
    Call<GBMV3> trainGbm(@Field("learn_rate") double learn_rate, @Field("learn_rate_annealing") double learn_rate_annealing,
            @Field("sample_rate") double sample_rate, @Field("col_sample_rate") double col_sample_rate,
            @Field("monotone_constraints") KeyValueV3[] monotone_constraints, @Field("max_abs_leafnode_pred") double max_abs_leafnode_pred,
            @Field("pred_noise_bandwidth") double pred_noise_bandwidth,
            @Field("interaction_constraints") String[][] interaction_constraints, @Field("balance_classes") boolean balance_classes,
            @Field("class_sampling_factors") float[] class_sampling_factors, @Field("max_after_balance_size") float max_after_balance_size,
            @Field("max_confusion_matrix_size") int max_confusion_matrix_size, @Field("ntrees") int ntrees,
            @Field("max_depth") int max_depth, @Field("min_rows") double min_rows, @Field("nbins") int nbins,
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
            @Field("stopping_tolerance") double stopping_tolerance, @Field("gainslift_bins") int gainslift_bins,
            @Field("custom_metric_func") String custom_metric_func, @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir, @Field("auc_type") MultinomialAucType auc_type);

    @FormUrlEncoded
    @POST("/3/ModelBuilders/gbm")
    Call<GBMV3> trainGbm();

    /**
     * Validate a set of GBM model builder parameters.
     *   @param learn_rate Learning rate (from 0.0 to 1.0)
     *   @param learn_rate_annealing Scale the learning rate by this factor after each tree (e.g., 0.99 or 0.999)
     *   @param sample_rate Row sample rate per tree (from 0.0 to 1.0)
     *   @param col_sample_rate Column sample rate (from 0.0 to 1.0)
     *   @param monotone_constraints A mapping representing monotonic constraints. Use +1 to enforce an increasing
     *                               constraint and -1 to specify a decreasing constraint.
     *   @param max_abs_leafnode_pred Maximum absolute value of a leaf node prediction
     *   @param pred_noise_bandwidth Bandwidth (sigma) of Gaussian multiplicative noise ~N(1,sigma) for tree node
     *                               predictions
     *   @param interaction_constraints A set of allowed column interactions.
     *   @param balance_classes Balance training data class counts via over/under-sampling (for imbalanced data).
     *   @param class_sampling_factors Desired over/under-sampling ratios per class (in lexicographic order). If not
     *                                 specified, sampling factors will be automatically computed to obtain class balance
     *                                 during training. Requires balance_classes.
     *   @param max_after_balance_size Maximum relative size of the training data after balancing class counts (can be
     *                                 less than 1.0). Requires balance_classes.
     *   @param max_confusion_matrix_size [Deprecated] Maximum size (# classes) for confusion matrices to be printed in
     *                                    the Logs
     *   @param ntrees Number of trees.
     *   @param max_depth Maximum tree depth (0 for unlimited).
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
     *   @param build_tree_one_node Run on one node only; no network overhead but fewer cpus used. Suitable for small
     *                              datasets.
     *   @param sample_rate_per_class A list of row sample rates per class (relative fraction for each class, from 0.0 to
     *                                1.0), for each tree
     *   @param col_sample_rate_per_tree Column sample rate per tree (from 0.0 to 1.0)
     *   @param col_sample_rate_change_per_level Relative change of the column sampling rate for every level (must be >
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
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or >= 2).
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
     *                         If you set weight = 0 for a row, the returned prediction frame at that row is zero and this
     *                         is incorrect. To get an accurate prediction, remove all rows with weight == 0.
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
     *   @param gainslift_bins Gains/Lift table number of bins. 0 means disabled.. Default value -1 means automatic
     *                         binning.
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     *   @param auc_type Set default multinomial AUC type.
     */
    @FormUrlEncoded
    @POST("/3/ModelBuilders/gbm/parameters")
    Call<GBMV3> validate_parametersGbm(@Field("learn_rate") double learn_rate, @Field("learn_rate_annealing") double learn_rate_annealing,
            @Field("sample_rate") double sample_rate, @Field("col_sample_rate") double col_sample_rate,
            @Field("monotone_constraints") KeyValueV3[] monotone_constraints, @Field("max_abs_leafnode_pred") double max_abs_leafnode_pred,
            @Field("pred_noise_bandwidth") double pred_noise_bandwidth,
            @Field("interaction_constraints") String[][] interaction_constraints, @Field("balance_classes") boolean balance_classes,
            @Field("class_sampling_factors") float[] class_sampling_factors, @Field("max_after_balance_size") float max_after_balance_size,
            @Field("max_confusion_matrix_size") int max_confusion_matrix_size, @Field("ntrees") int ntrees,
            @Field("max_depth") int max_depth, @Field("min_rows") double min_rows, @Field("nbins") int nbins,
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
            @Field("stopping_tolerance") double stopping_tolerance, @Field("gainslift_bins") int gainslift_bins,
            @Field("custom_metric_func") String custom_metric_func, @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir, @Field("auc_type") MultinomialAucType auc_type);

    @FormUrlEncoded
    @POST("/3/ModelBuilders/gbm/parameters")
    Call<GBMV3> validate_parametersGbm();

    /**
     * Train a IsolationForest model.
     *   @param sample_size Number of randomly sampled observations used to train each Isolation Forest tree. Only one of
     *                      parameters sample_size and sample_rate should be defined. If sample_rate is defined,
     *                      sample_size will be ignored.
     *   @param sample_rate Rate of randomly sampled observations used to train each Isolation Forest tree. Needs to be in
     *                      range from 0.0 to 1.0. If set to -1, sample_rate is disabled and sample_size will be used
     *                      instead.
     *   @param mtries Number of variables randomly sampled as candidates at each split. If set to -1, defaults (number of
     *                 predictors)/3.
     *   @param contamination Contamination ratio - the proportion of anomalies in the input dataset. If undefined (-1)
     *                        the predict function will not mark observations as anomalies and only anomaly score will be
     *                        returned. Defaults to -1 (undefined).
     *   @param validation_response_column (experimental) Name of the response column in the validation frame. Response
     *                                     column should be binary and indicate not anomaly/anomaly.
     *   @param balance_classes Balance training data class counts via over/under-sampling (for imbalanced data).
     *   @param class_sampling_factors Desired over/under-sampling ratios per class (in lexicographic order). If not
     *                                 specified, sampling factors will be automatically computed to obtain class balance
     *                                 during training. Requires balance_classes.
     *   @param max_after_balance_size Maximum relative size of the training data after balancing class counts (can be
     *                                 less than 1.0). Requires balance_classes.
     *   @param max_confusion_matrix_size [Deprecated] Maximum size (# classes) for confusion matrices to be printed in
     *                                    the Logs
     *   @param ntrees Number of trees.
     *   @param max_depth Maximum tree depth (0 for unlimited).
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
     *   @param build_tree_one_node Run on one node only; no network overhead but fewer cpus used. Suitable for small
     *                              datasets.
     *   @param sample_rate_per_class A list of row sample rates per class (relative fraction for each class, from 0.0 to
     *                                1.0), for each tree
     *   @param col_sample_rate_per_tree Column sample rate per tree (from 0.0 to 1.0)
     *   @param col_sample_rate_change_per_level Relative change of the column sampling rate for every level (must be >
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
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or >= 2).
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
     *                         If you set weight = 0 for a row, the returned prediction frame at that row is zero and this
     *                         is incorrect. To get an accurate prediction, remove all rows with weight == 0.
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
     *   @param gainslift_bins Gains/Lift table number of bins. 0 means disabled.. Default value -1 means automatic
     *                         binning.
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     *   @param auc_type Set default multinomial AUC type.
     */
    @FormUrlEncoded
    @POST("/3/ModelBuilders/isolationforest")
    Call<IsolationForestV3> trainIsolationforest(@Field("sample_size") long sample_size, @Field("sample_rate") double sample_rate,
            @Field("mtries") int mtries, @Field("contamination") double contamination,
            @Field("validation_response_column") String validation_response_column, @Field("balance_classes") boolean balance_classes,
            @Field("class_sampling_factors") float[] class_sampling_factors, @Field("max_after_balance_size") float max_after_balance_size,
            @Field("max_confusion_matrix_size") int max_confusion_matrix_size, @Field("ntrees") int ntrees,
            @Field("max_depth") int max_depth, @Field("min_rows") double min_rows, @Field("nbins") int nbins,
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
            @Field("stopping_tolerance") double stopping_tolerance, @Field("gainslift_bins") int gainslift_bins,
            @Field("custom_metric_func") String custom_metric_func, @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir, @Field("auc_type") MultinomialAucType auc_type);

    @FormUrlEncoded
    @POST("/3/ModelBuilders/isolationforest")
    Call<IsolationForestV3> trainIsolationforest();

    /**
     * Validate a set of IsolationForest model builder parameters.
     *   @param sample_size Number of randomly sampled observations used to train each Isolation Forest tree. Only one of
     *                      parameters sample_size and sample_rate should be defined. If sample_rate is defined,
     *                      sample_size will be ignored.
     *   @param sample_rate Rate of randomly sampled observations used to train each Isolation Forest tree. Needs to be in
     *                      range from 0.0 to 1.0. If set to -1, sample_rate is disabled and sample_size will be used
     *                      instead.
     *   @param mtries Number of variables randomly sampled as candidates at each split. If set to -1, defaults (number of
     *                 predictors)/3.
     *   @param contamination Contamination ratio - the proportion of anomalies in the input dataset. If undefined (-1)
     *                        the predict function will not mark observations as anomalies and only anomaly score will be
     *                        returned. Defaults to -1 (undefined).
     *   @param validation_response_column (experimental) Name of the response column in the validation frame. Response
     *                                     column should be binary and indicate not anomaly/anomaly.
     *   @param balance_classes Balance training data class counts via over/under-sampling (for imbalanced data).
     *   @param class_sampling_factors Desired over/under-sampling ratios per class (in lexicographic order). If not
     *                                 specified, sampling factors will be automatically computed to obtain class balance
     *                                 during training. Requires balance_classes.
     *   @param max_after_balance_size Maximum relative size of the training data after balancing class counts (can be
     *                                 less than 1.0). Requires balance_classes.
     *   @param max_confusion_matrix_size [Deprecated] Maximum size (# classes) for confusion matrices to be printed in
     *                                    the Logs
     *   @param ntrees Number of trees.
     *   @param max_depth Maximum tree depth (0 for unlimited).
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
     *   @param build_tree_one_node Run on one node only; no network overhead but fewer cpus used. Suitable for small
     *                              datasets.
     *   @param sample_rate_per_class A list of row sample rates per class (relative fraction for each class, from 0.0 to
     *                                1.0), for each tree
     *   @param col_sample_rate_per_tree Column sample rate per tree (from 0.0 to 1.0)
     *   @param col_sample_rate_change_per_level Relative change of the column sampling rate for every level (must be >
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
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or >= 2).
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
     *                         If you set weight = 0 for a row, the returned prediction frame at that row is zero and this
     *                         is incorrect. To get an accurate prediction, remove all rows with weight == 0.
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
     *   @param gainslift_bins Gains/Lift table number of bins. 0 means disabled.. Default value -1 means automatic
     *                         binning.
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     *   @param auc_type Set default multinomial AUC type.
     */
    @FormUrlEncoded
    @POST("/3/ModelBuilders/isolationforest/parameters")
    Call<IsolationForestV3> validate_parametersIsolationforest(@Field("sample_size") long sample_size,
            @Field("sample_rate") double sample_rate, @Field("mtries") int mtries, @Field("contamination") double contamination,
            @Field("validation_response_column") String validation_response_column, @Field("balance_classes") boolean balance_classes,
            @Field("class_sampling_factors") float[] class_sampling_factors, @Field("max_after_balance_size") float max_after_balance_size,
            @Field("max_confusion_matrix_size") int max_confusion_matrix_size, @Field("ntrees") int ntrees,
            @Field("max_depth") int max_depth, @Field("min_rows") double min_rows, @Field("nbins") int nbins,
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
            @Field("stopping_tolerance") double stopping_tolerance, @Field("gainslift_bins") int gainslift_bins,
            @Field("custom_metric_func") String custom_metric_func, @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir, @Field("auc_type") MultinomialAucType auc_type);

    @FormUrlEncoded
    @POST("/3/ModelBuilders/isolationforest/parameters")
    Call<IsolationForestV3> validate_parametersIsolationforest();

    /**
     * Train a ExtendedIsolationForest model.
     *   @param ntrees Number of Extended Isolation Forest trees.
     *   @param sample_size Number of randomly sampled observations used to train each Extended Isolation Forest tree.
     *   @param extension_level Maximum is N - 1 (N = numCols). Minimum is 0. Extended Isolation Forest with
     *                          extension_Level = 0 behaves like Isolation Forest.
     *   @param seed Seed for pseudo random number generator (if applicable)
     *   @param model_id Destination id for this model; auto-generated if not specified.
     *   @param training_frame Id of the training data frame.
     *   @param validation_frame Id of the validation data frame.
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or >= 2).
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
     *                         If you set weight = 0 for a row, the returned prediction frame at that row is zero and this
     *                         is incorrect. To get an accurate prediction, remove all rows with weight == 0.
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
     *   @param gainslift_bins Gains/Lift table number of bins. 0 means disabled.. Default value -1 means automatic
     *                         binning.
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     *   @param auc_type Set default multinomial AUC type.
     */
    @FormUrlEncoded
    @POST("/3/ModelBuilders/extendedisolationforest")
    Call<ExtendedIsolationForestV3> trainExtendedisolationforest(@Field("ntrees") int ntrees, @Field("sample_size") int sample_size,
            @Field("extension_level") int extension_level, @Field("seed") long seed, @Field("model_id") String model_id,
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
            @Field("stopping_tolerance") double stopping_tolerance, @Field("gainslift_bins") int gainslift_bins,
            @Field("custom_metric_func") String custom_metric_func, @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir, @Field("auc_type") MultinomialAucType auc_type);

    @FormUrlEncoded
    @POST("/3/ModelBuilders/extendedisolationforest")
    Call<ExtendedIsolationForestV3> trainExtendedisolationforest();

    /**
     * Validate a set of ExtendedIsolationForest model builder parameters.
     *   @param ntrees Number of Extended Isolation Forest trees.
     *   @param sample_size Number of randomly sampled observations used to train each Extended Isolation Forest tree.
     *   @param extension_level Maximum is N - 1 (N = numCols). Minimum is 0. Extended Isolation Forest with
     *                          extension_Level = 0 behaves like Isolation Forest.
     *   @param seed Seed for pseudo random number generator (if applicable)
     *   @param model_id Destination id for this model; auto-generated if not specified.
     *   @param training_frame Id of the training data frame.
     *   @param validation_frame Id of the validation data frame.
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or >= 2).
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
     *                         If you set weight = 0 for a row, the returned prediction frame at that row is zero and this
     *                         is incorrect. To get an accurate prediction, remove all rows with weight == 0.
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
     *   @param gainslift_bins Gains/Lift table number of bins. 0 means disabled.. Default value -1 means automatic
     *                         binning.
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     *   @param auc_type Set default multinomial AUC type.
     */
    @FormUrlEncoded
    @POST("/3/ModelBuilders/extendedisolationforest/parameters")
    Call<ExtendedIsolationForestV3> validate_parametersExtendedisolationforest(@Field("ntrees") int ntrees,
            @Field("sample_size") int sample_size, @Field("extension_level") int extension_level, @Field("seed") long seed,
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
            @Field("stopping_tolerance") double stopping_tolerance, @Field("gainslift_bins") int gainslift_bins,
            @Field("custom_metric_func") String custom_metric_func, @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir, @Field("auc_type") MultinomialAucType auc_type);

    @FormUrlEncoded
    @POST("/3/ModelBuilders/extendedisolationforest/parameters")
    Call<ExtendedIsolationForestV3> validate_parametersExtendedisolationforest();

    /**
     * Train a Aggregator model.
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
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or >= 2).
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
     *                         If you set weight = 0 for a row, the returned prediction frame at that row is zero and this
     *                         is incorrect. To get an accurate prediction, remove all rows with weight == 0.
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
     *   @param gainslift_bins Gains/Lift table number of bins. 0 means disabled.. Default value -1 means automatic
     *                         binning.
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     *   @param auc_type Set default multinomial AUC type.
     */
    @FormUrlEncoded
    @POST("/99/ModelBuilders/aggregator")
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
            @Field("stopping_tolerance") double stopping_tolerance, @Field("gainslift_bins") int gainslift_bins,
            @Field("custom_metric_func") String custom_metric_func, @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir, @Field("auc_type") MultinomialAucType auc_type);

    @FormUrlEncoded
    @POST("/99/ModelBuilders/aggregator")
    Call<AggregatorV99> trainAggregator();

    /**
     * Validate a set of Aggregator model builder parameters.
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
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or >= 2).
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
     *                         If you set weight = 0 for a row, the returned prediction frame at that row is zero and this
     *                         is incorrect. To get an accurate prediction, remove all rows with weight == 0.
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
     *   @param gainslift_bins Gains/Lift table number of bins. 0 means disabled.. Default value -1 means automatic
     *                         binning.
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     *   @param auc_type Set default multinomial AUC type.
     */
    @FormUrlEncoded
    @POST("/99/ModelBuilders/aggregator/parameters")
    Call<AggregatorV99> validate_parametersAggregator(@Field("transform") DataInfoTransformType transform,
            @Field("pca_method") PCAMethod pca_method, @Field("k") int k, @Field("max_iterations") int max_iterations,
            @Field("target_num_exemplars") int target_num_exemplars, @Field("rel_tol_num_exemplars") double rel_tol_num_exemplars,
            @Field("seed") long seed, @Field("use_all_factor_levels") boolean use_all_factor_levels,
            @Field("save_mapping_frame") boolean save_mapping_frame,
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
            @Field("stopping_tolerance") double stopping_tolerance, @Field("gainslift_bins") int gainslift_bins,
            @Field("custom_metric_func") String custom_metric_func, @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir, @Field("auc_type") MultinomialAucType auc_type);

    @FormUrlEncoded
    @POST("/99/ModelBuilders/aggregator/parameters")
    Call<AggregatorV99> validate_parametersAggregator();

    /**
     * Train a Word2Vec model.
     *   @param vec_size Set size of word vectors
     *   @param window_size Set max skip length between words
     *   @param sent_sample_rate Set threshold for occurrence of words. Those that appear with higher frequency in the
     *                           training data
     *                                           will be randomly down-sampled; useful range is (0, 1e-5)
     *   @param norm_model Use Hierarchical Softmax
     *   @param epochs Number of training iterations to run
     *   @param min_word_freq This will discard words that appear less than &lt;int&gt; times
     *   @param init_learning_rate Set the starting learning rate
     *   @param word_model The word model to use (SkipGram or CBOW)
     *   @param pre_trained Id of a data frame that contains a pre-trained (external) word2vec model
     *   @param model_id Destination id for this model; auto-generated if not specified.
     *   @param training_frame Id of the training data frame.
     *   @param validation_frame Id of the validation data frame.
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or >= 2).
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
     *                         If you set weight = 0 for a row, the returned prediction frame at that row is zero and this
     *                         is incorrect. To get an accurate prediction, remove all rows with weight == 0.
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
     *   @param gainslift_bins Gains/Lift table number of bins. 0 means disabled.. Default value -1 means automatic
     *                         binning.
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     *   @param auc_type Set default multinomial AUC type.
     */
    @FormUrlEncoded
    @POST("/3/ModelBuilders/word2vec")
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
            @Field("stopping_tolerance") double stopping_tolerance, @Field("gainslift_bins") int gainslift_bins,
            @Field("custom_metric_func") String custom_metric_func, @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir, @Field("auc_type") MultinomialAucType auc_type);

    @FormUrlEncoded
    @POST("/3/ModelBuilders/word2vec")
    Call<Word2VecV3> trainWord2vec();

    /**
     * Validate a set of Word2Vec model builder parameters.
     *   @param vec_size Set size of word vectors
     *   @param window_size Set max skip length between words
     *   @param sent_sample_rate Set threshold for occurrence of words. Those that appear with higher frequency in the
     *                           training data
     *                                           will be randomly down-sampled; useful range is (0, 1e-5)
     *   @param norm_model Use Hierarchical Softmax
     *   @param epochs Number of training iterations to run
     *   @param min_word_freq This will discard words that appear less than &lt;int&gt; times
     *   @param init_learning_rate Set the starting learning rate
     *   @param word_model The word model to use (SkipGram or CBOW)
     *   @param pre_trained Id of a data frame that contains a pre-trained (external) word2vec model
     *   @param model_id Destination id for this model; auto-generated if not specified.
     *   @param training_frame Id of the training data frame.
     *   @param validation_frame Id of the validation data frame.
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or >= 2).
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
     *                         If you set weight = 0 for a row, the returned prediction frame at that row is zero and this
     *                         is incorrect. To get an accurate prediction, remove all rows with weight == 0.
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
     *   @param gainslift_bins Gains/Lift table number of bins. 0 means disabled.. Default value -1 means automatic
     *                         binning.
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     *   @param auc_type Set default multinomial AUC type.
     */
    @FormUrlEncoded
    @POST("/3/ModelBuilders/word2vec/parameters")
    Call<Word2VecV3> validate_parametersWord2vec(@Field("vec_size") int vec_size, @Field("window_size") int window_size,
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
            @Field("stopping_tolerance") double stopping_tolerance, @Field("gainslift_bins") int gainslift_bins,
            @Field("custom_metric_func") String custom_metric_func, @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir, @Field("auc_type") MultinomialAucType auc_type);

    @FormUrlEncoded
    @POST("/3/ModelBuilders/word2vec/parameters")
    Call<Word2VecV3> validate_parametersWord2vec();

    /**
     * Train a StackedEnsemble model.
     *   @param base_models List of models or grids (or their ids) to ensemble/stack together. Grids are expanded to
     *                      individual models. If not using blending frame, then models must have been cross-validated
     *                      using nfolds > 1, and folds must be identical across models.
     *   @param metalearner_algorithm Type of algorithm to use as the metalearner. Options include 'AUTO' (GLM with non
     *                                negative weights; if validation_frame is present, a lambda search is performed),
     *                                'deeplearning' (Deep Learning with default parameters), 'drf' (Random Forest with
     *                                default parameters), 'gbm' (GBM with default parameters), 'glm' (GLM with default
     *                                parameters), 'naivebayes' (NaiveBayes with default parameters), or 'xgboost' (if
     *                                available, XGBoost with default parameters).
     *   @param metalearner_nfolds Number of folds for K-fold cross-validation of the metalearner algorithm (0 to disable
     *                             or >= 2).
     *   @param metalearner_fold_assignment Cross-validation fold assignment scheme for metalearner cross-validation.
     *                                      Defaults to AUTO (which is currently set to Random). The 'Stratified' option
     *                                      will stratify the folds based on the response variable, for classification
     *                                      problems.
     *   @param metalearner_fold_column Column with cross-validation fold index assignment per observation for cross-
     *                                  validation of the metalearner.
     *   @param metalearner_transform Transformation used for the level one frame.
     *   @param keep_levelone_frame Keep level one frame used for metalearner training.
     *   @param metalearner_params Parameters for metalearner algorithm
     *   @param blending_frame Frame used to compute the predictions that serve as the training frame for the metalearner
     *                         (triggers blending mode if provided)
     *   @param seed Seed for random numbers; passed through to the metalearner algorithm. Defaults to -1 (time-based
     *               random number)
     *   @param score_training_samples Specify the number of training set samples for scoring. The value must be >= 0. To
     *                                 use all training samples, enter 0.
     *   @param model_id Destination id for this model; auto-generated if not specified.
     *   @param training_frame Id of the training data frame.
     *   @param validation_frame Id of the validation data frame.
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or >= 2).
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
     *                         If you set weight = 0 for a row, the returned prediction frame at that row is zero and this
     *                         is incorrect. To get an accurate prediction, remove all rows with weight == 0.
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
     *   @param gainslift_bins Gains/Lift table number of bins. 0 means disabled.. Default value -1 means automatic
     *                         binning.
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     *   @param auc_type Set default multinomial AUC type.
     */
    @FormUrlEncoded
    @POST("/99/ModelBuilders/stackedensemble")
    Call<StackedEnsembleV99> trainStackedensemble(@Field("base_models") String[] base_models,
            @Field("metalearner_algorithm") EnsembleMetalearnerAlgorithm metalearner_algorithm,
            @Field("metalearner_nfolds") int metalearner_nfolds,
            @Field("metalearner_fold_assignment") ModelParametersFoldAssignmentScheme metalearner_fold_assignment,
            @Field("metalearner_fold_column") String metalearner_fold_column,
            @Field("metalearner_transform") EnsembleStackedEnsembleModelStackedEnsembleParametersMetalearnerTransform metalearner_transform,
            @Field("keep_levelone_frame") boolean keep_levelone_frame, @Field("metalearner_params") String metalearner_params,
            @Field("blending_frame") String blending_frame, @Field("seed") long seed,
            @Field("score_training_samples") long score_training_samples, @Field("model_id") String model_id,
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
            @Field("stopping_tolerance") double stopping_tolerance, @Field("gainslift_bins") int gainslift_bins,
            @Field("custom_metric_func") String custom_metric_func, @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir, @Field("auc_type") MultinomialAucType auc_type);

    @FormUrlEncoded
    @POST("/99/ModelBuilders/stackedensemble")
    Call<StackedEnsembleV99> trainStackedensemble(@Field("base_models") String[] base_models);

    /**
     * Validate a set of StackedEnsemble model builder parameters.
     *   @param base_models List of models or grids (or their ids) to ensemble/stack together. Grids are expanded to
     *                      individual models. If not using blending frame, then models must have been cross-validated
     *                      using nfolds > 1, and folds must be identical across models.
     *   @param metalearner_algorithm Type of algorithm to use as the metalearner. Options include 'AUTO' (GLM with non
     *                                negative weights; if validation_frame is present, a lambda search is performed),
     *                                'deeplearning' (Deep Learning with default parameters), 'drf' (Random Forest with
     *                                default parameters), 'gbm' (GBM with default parameters), 'glm' (GLM with default
     *                                parameters), 'naivebayes' (NaiveBayes with default parameters), or 'xgboost' (if
     *                                available, XGBoost with default parameters).
     *   @param metalearner_nfolds Number of folds for K-fold cross-validation of the metalearner algorithm (0 to disable
     *                             or >= 2).
     *   @param metalearner_fold_assignment Cross-validation fold assignment scheme for metalearner cross-validation.
     *                                      Defaults to AUTO (which is currently set to Random). The 'Stratified' option
     *                                      will stratify the folds based on the response variable, for classification
     *                                      problems.
     *   @param metalearner_fold_column Column with cross-validation fold index assignment per observation for cross-
     *                                  validation of the metalearner.
     *   @param metalearner_transform Transformation used for the level one frame.
     *   @param keep_levelone_frame Keep level one frame used for metalearner training.
     *   @param metalearner_params Parameters for metalearner algorithm
     *   @param blending_frame Frame used to compute the predictions that serve as the training frame for the metalearner
     *                         (triggers blending mode if provided)
     *   @param seed Seed for random numbers; passed through to the metalearner algorithm. Defaults to -1 (time-based
     *               random number)
     *   @param score_training_samples Specify the number of training set samples for scoring. The value must be >= 0. To
     *                                 use all training samples, enter 0.
     *   @param model_id Destination id for this model; auto-generated if not specified.
     *   @param training_frame Id of the training data frame.
     *   @param validation_frame Id of the validation data frame.
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or >= 2).
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
     *                         If you set weight = 0 for a row, the returned prediction frame at that row is zero and this
     *                         is incorrect. To get an accurate prediction, remove all rows with weight == 0.
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
     *   @param gainslift_bins Gains/Lift table number of bins. 0 means disabled.. Default value -1 means automatic
     *                         binning.
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     *   @param auc_type Set default multinomial AUC type.
     */
    @FormUrlEncoded
    @POST("/99/ModelBuilders/stackedensemble/parameters")
    Call<StackedEnsembleV99> validate_parametersStackedensemble(@Field("base_models") String[] base_models,
            @Field("metalearner_algorithm") EnsembleMetalearnerAlgorithm metalearner_algorithm,
            @Field("metalearner_nfolds") int metalearner_nfolds,
            @Field("metalearner_fold_assignment") ModelParametersFoldAssignmentScheme metalearner_fold_assignment,
            @Field("metalearner_fold_column") String metalearner_fold_column,
            @Field("metalearner_transform") EnsembleStackedEnsembleModelStackedEnsembleParametersMetalearnerTransform metalearner_transform,
            @Field("keep_levelone_frame") boolean keep_levelone_frame, @Field("metalearner_params") String metalearner_params,
            @Field("blending_frame") String blending_frame, @Field("seed") long seed,
            @Field("score_training_samples") long score_training_samples, @Field("model_id") String model_id,
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
            @Field("stopping_tolerance") double stopping_tolerance, @Field("gainslift_bins") int gainslift_bins,
            @Field("custom_metric_func") String custom_metric_func, @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir, @Field("auc_type") MultinomialAucType auc_type);

    @FormUrlEncoded
    @POST("/99/ModelBuilders/stackedensemble/parameters")
    Call<StackedEnsembleV99> validate_parametersStackedensemble(@Field("base_models") String[] base_models);

    /**
     * Train a CoxPH model.
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
     *   @param single_node_mode Run on a single node to reduce the effect of network overhead (for smaller datasets)
     *   @param model_id Destination id for this model; auto-generated if not specified.
     *   @param training_frame Id of the training data frame.
     *   @param validation_frame Id of the validation data frame.
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or >= 2).
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
     *                         If you set weight = 0 for a row, the returned prediction frame at that row is zero and this
     *                         is incorrect. To get an accurate prediction, remove all rows with weight == 0.
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
     *   @param gainslift_bins Gains/Lift table number of bins. 0 means disabled.. Default value -1 means automatic
     *                         binning.
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     *   @param auc_type Set default multinomial AUC type.
     */
    @FormUrlEncoded
    @POST("/3/ModelBuilders/coxph")
    Call<CoxPHV3> trainCoxph(@Field("start_column") String start_column, @Field("stop_column") String stop_column,
            @Field("stratify_by") String[] stratify_by, @Field("ties") CoxPHTies ties, @Field("init") double init,
            @Field("lre_min") double lre_min, @Field("max_iterations") int max_iterations,
            @Field("interactions_only") String[] interactions_only, @Field("interactions") String[] interactions,
            @Field("interaction_pairs") StringPairV3[] interaction_pairs, @Field("use_all_factor_levels") boolean use_all_factor_levels,
            @Field("single_node_mode") boolean single_node_mode, @Field("model_id") String model_id,
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
            @Field("stopping_tolerance") double stopping_tolerance, @Field("gainslift_bins") int gainslift_bins,
            @Field("custom_metric_func") String custom_metric_func, @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir, @Field("auc_type") MultinomialAucType auc_type);

    @FormUrlEncoded
    @POST("/3/ModelBuilders/coxph")
    Call<CoxPHV3> trainCoxph();

    /**
     * Validate a set of CoxPH model builder parameters.
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
     *   @param single_node_mode Run on a single node to reduce the effect of network overhead (for smaller datasets)
     *   @param model_id Destination id for this model; auto-generated if not specified.
     *   @param training_frame Id of the training data frame.
     *   @param validation_frame Id of the validation data frame.
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or >= 2).
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
     *                         If you set weight = 0 for a row, the returned prediction frame at that row is zero and this
     *                         is incorrect. To get an accurate prediction, remove all rows with weight == 0.
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
     *   @param gainslift_bins Gains/Lift table number of bins. 0 means disabled.. Default value -1 means automatic
     *                         binning.
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     *   @param auc_type Set default multinomial AUC type.
     */
    @FormUrlEncoded
    @POST("/3/ModelBuilders/coxph/parameters")
    Call<CoxPHV3> validate_parametersCoxph(@Field("start_column") String start_column, @Field("stop_column") String stop_column,
            @Field("stratify_by") String[] stratify_by, @Field("ties") CoxPHTies ties, @Field("init") double init,
            @Field("lre_min") double lre_min, @Field("max_iterations") int max_iterations,
            @Field("interactions_only") String[] interactions_only, @Field("interactions") String[] interactions,
            @Field("interaction_pairs") StringPairV3[] interaction_pairs, @Field("use_all_factor_levels") boolean use_all_factor_levels,
            @Field("single_node_mode") boolean single_node_mode, @Field("model_id") String model_id,
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
            @Field("stopping_tolerance") double stopping_tolerance, @Field("gainslift_bins") int gainslift_bins,
            @Field("custom_metric_func") String custom_metric_func, @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir, @Field("auc_type") MultinomialAucType auc_type);

    @FormUrlEncoded
    @POST("/3/ModelBuilders/coxph/parameters")
    Call<CoxPHV3> validate_parametersCoxph();

    /**
     * Train a Generic model.
     *   @param path Path to file with self-contained model archive.
     *   @param model_key Key to the self-contained model archive already uploaded to H2O.
     *   @param model_id Destination id for this model; auto-generated if not specified.
     *   @param training_frame Id of the training data frame.
     *   @param validation_frame Id of the validation data frame.
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or >= 2).
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
     *                         If you set weight = 0 for a row, the returned prediction frame at that row is zero and this
     *                         is incorrect. To get an accurate prediction, remove all rows with weight == 0.
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
     *   @param gainslift_bins Gains/Lift table number of bins. 0 means disabled.. Default value -1 means automatic
     *                         binning.
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     *   @param auc_type Set default multinomial AUC type.
     */
    @FormUrlEncoded
    @POST("/3/ModelBuilders/generic")
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
            @Field("stopping_tolerance") double stopping_tolerance, @Field("gainslift_bins") int gainslift_bins,
            @Field("custom_metric_func") String custom_metric_func, @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir, @Field("auc_type") MultinomialAucType auc_type);

    @FormUrlEncoded
    @POST("/3/ModelBuilders/generic")
    Call<GenericV3> trainGeneric();

    /**
     * Validate a set of Generic model builder parameters.
     *   @param path Path to file with self-contained model archive.
     *   @param model_key Key to the self-contained model archive already uploaded to H2O.
     *   @param model_id Destination id for this model; auto-generated if not specified.
     *   @param training_frame Id of the training data frame.
     *   @param validation_frame Id of the validation data frame.
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or >= 2).
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
     *                         If you set weight = 0 for a row, the returned prediction frame at that row is zero and this
     *                         is incorrect. To get an accurate prediction, remove all rows with weight == 0.
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
     *   @param gainslift_bins Gains/Lift table number of bins. 0 means disabled.. Default value -1 means automatic
     *                         binning.
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     *   @param auc_type Set default multinomial AUC type.
     */
    @FormUrlEncoded
    @POST("/3/ModelBuilders/generic/parameters")
    Call<GenericV3> validate_parametersGeneric(@Field("path") String path, @Field("model_key") String model_key,
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
            @Field("stopping_tolerance") double stopping_tolerance, @Field("gainslift_bins") int gainslift_bins,
            @Field("custom_metric_func") String custom_metric_func, @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir, @Field("auc_type") MultinomialAucType auc_type);

    @FormUrlEncoded
    @POST("/3/ModelBuilders/generic/parameters")
    Call<GenericV3> validate_parametersGeneric();

    /**
     * Train a GAM model.
     *   @param seed Seed for pseudo random number generator (if applicable)
     *   @param family Family. Use binomial for classification with logistic regression, others are for regression
     *                 problems.
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
     *   @param startval double array to initialize coefficients for GAM.
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
     *   @param intercept Include constant term in the model
     *   @param prior Prior probability for y==1. To be used only for logistic regression iff the data has been sampled
     *                and the mean of response does not reflect reality.
     *   @param cold_start Only applicable to multiple alpha/lambda values when calling GLM from GAM.  If false, build the
     *                     next model for next set of alpha/lambda values starting from the values provided by current
     *                     model.  If true will start GLM model from scratch.
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
     *   @param compute_p_values Request p-values computation, p-values work only with IRLSM solver and no regularization
     *   @param remove_collinear_columns In case of linearly dependent columns, remove some of the dependent columns
     *   @param num_knots Number of knots for gam predictors
     *   @param spline_orders Order of I-splines used for gam predictors. If specified, must be the same size as
     *                        gam_columns.Values for bs=0 or 1 will be ignored.
     *   @param gam_columns Arrays of predictor column names for gam for smoothers using single or multiple predictors
     *                      like {{'c1'},{'c2','c3'},{'c4'},...}
     *   @param scale Smoothing parameter for gam predictors.  If specified, must be of the same length as gam_columns
     *   @param bs Basis function type for each gam predictors, 0 for cr, 1 for thin plate regression with knots, 2 for
     *             monotone splines.  If specified, must be the same size as gam_columns
     *   @param keep_gam_cols Save keys of model matrix
     *   @param standardize_tp_gam_cols standardize tp (thin plate) predictor columns
     *   @param scale_tp_penalty_mat Scale penalty matrix for tp (thin plate) smoothers as in R
     *   @param knot_ids Array storing frame keys of knots.  One for each gam column set specified in gam_columns
     *   @param model_id Destination id for this model; auto-generated if not specified.
     *   @param training_frame Id of the training data frame.
     *   @param validation_frame Id of the validation data frame.
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or >= 2).
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
     *                         If you set weight = 0 for a row, the returned prediction frame at that row is zero and this
     *                         is incorrect. To get an accurate prediction, remove all rows with weight == 0.
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
     *   @param gainslift_bins Gains/Lift table number of bins. 0 means disabled.. Default value -1 means automatic
     *                         binning.
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     *   @param auc_type Set default multinomial AUC type.
     */
    @FormUrlEncoded
    @POST("/3/ModelBuilders/gam")
    Call<GAMV3> trainGam(@Field("seed") long seed, @Field("family") GLMFamily family,
            @Field("tweedie_variance_power") double tweedie_variance_power, @Field("tweedie_link_power") double tweedie_link_power,
            @Field("theta") double theta, @Field("solver") GLMSolver solver, @Field("alpha") double[] alpha,
            @Field("lambda") double[] lambda, @Field("startval") double[] startval, @Field("lambda_search") boolean lambda_search,
            @Field("early_stopping") boolean early_stopping, @Field("nlambdas") int nlambdas, @Field("standardize") boolean standardize,
            @Field("missing_values_handling") GLMMissingValuesHandling missing_values_handling, @Field("plug_values") String plug_values,
            @Field("non_negative") boolean non_negative, @Field("max_iterations") int max_iterations,
            @Field("beta_epsilon") double beta_epsilon, @Field("objective_epsilon") double objective_epsilon,
            @Field("gradient_epsilon") double gradient_epsilon, @Field("obj_reg") double obj_reg, @Field("link") GLMLink link,
            @Field("intercept") boolean intercept, @Field("prior") double prior, @Field("cold_start") boolean cold_start,
            @Field("lambda_min_ratio") double lambda_min_ratio, @Field("beta_constraints") String beta_constraints,
            @Field("max_active_predictors") int max_active_predictors, @Field("interactions") String[] interactions,
            @Field("interaction_pairs") StringPairV3[] interaction_pairs, @Field("balance_classes") boolean balance_classes,
            @Field("class_sampling_factors") float[] class_sampling_factors, @Field("max_after_balance_size") float max_after_balance_size,
            @Field("max_confusion_matrix_size") int max_confusion_matrix_size, @Field("compute_p_values") boolean compute_p_values,
            @Field("remove_collinear_columns") boolean remove_collinear_columns, @Field("num_knots") int[] num_knots,
            @Field("spline_orders") int[] spline_orders, @Field("gam_columns") String[][] gam_columns, @Field("scale") double[] scale,
            @Field("bs") int[] bs, @Field("keep_gam_cols") boolean keep_gam_cols,
            @Field("standardize_tp_gam_cols") boolean standardize_tp_gam_cols, @Field("scale_tp_penalty_mat") boolean scale_tp_penalty_mat,
            @Field("knot_ids") String[] knot_ids, @Field("model_id") String model_id, @Field("training_frame") String training_frame,
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
            @Field("stopping_tolerance") double stopping_tolerance, @Field("gainslift_bins") int gainslift_bins,
            @Field("custom_metric_func") String custom_metric_func, @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir, @Field("auc_type") MultinomialAucType auc_type);

    @FormUrlEncoded
    @POST("/3/ModelBuilders/gam")
    Call<GAMV3> trainGam(@Field("gam_columns") String[][] gam_columns);

    /**
     * Validate a set of GAM model builder parameters.
     *   @param seed Seed for pseudo random number generator (if applicable)
     *   @param family Family. Use binomial for classification with logistic regression, others are for regression
     *                 problems.
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
     *   @param startval double array to initialize coefficients for GAM.
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
     *   @param intercept Include constant term in the model
     *   @param prior Prior probability for y==1. To be used only for logistic regression iff the data has been sampled
     *                and the mean of response does not reflect reality.
     *   @param cold_start Only applicable to multiple alpha/lambda values when calling GLM from GAM.  If false, build the
     *                     next model for next set of alpha/lambda values starting from the values provided by current
     *                     model.  If true will start GLM model from scratch.
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
     *   @param compute_p_values Request p-values computation, p-values work only with IRLSM solver and no regularization
     *   @param remove_collinear_columns In case of linearly dependent columns, remove some of the dependent columns
     *   @param num_knots Number of knots for gam predictors
     *   @param spline_orders Order of I-splines used for gam predictors. If specified, must be the same size as
     *                        gam_columns.Values for bs=0 or 1 will be ignored.
     *   @param gam_columns Arrays of predictor column names for gam for smoothers using single or multiple predictors
     *                      like {{'c1'},{'c2','c3'},{'c4'},...}
     *   @param scale Smoothing parameter for gam predictors.  If specified, must be of the same length as gam_columns
     *   @param bs Basis function type for each gam predictors, 0 for cr, 1 for thin plate regression with knots, 2 for
     *             monotone splines.  If specified, must be the same size as gam_columns
     *   @param keep_gam_cols Save keys of model matrix
     *   @param standardize_tp_gam_cols standardize tp (thin plate) predictor columns
     *   @param scale_tp_penalty_mat Scale penalty matrix for tp (thin plate) smoothers as in R
     *   @param knot_ids Array storing frame keys of knots.  One for each gam column set specified in gam_columns
     *   @param model_id Destination id for this model; auto-generated if not specified.
     *   @param training_frame Id of the training data frame.
     *   @param validation_frame Id of the validation data frame.
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or >= 2).
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
     *                         If you set weight = 0 for a row, the returned prediction frame at that row is zero and this
     *                         is incorrect. To get an accurate prediction, remove all rows with weight == 0.
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
     *   @param gainslift_bins Gains/Lift table number of bins. 0 means disabled.. Default value -1 means automatic
     *                         binning.
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     *   @param auc_type Set default multinomial AUC type.
     */
    @FormUrlEncoded
    @POST("/3/ModelBuilders/gam/parameters")
    Call<GAMV3> validate_parametersGam(@Field("seed") long seed, @Field("family") GLMFamily family,
            @Field("tweedie_variance_power") double tweedie_variance_power, @Field("tweedie_link_power") double tweedie_link_power,
            @Field("theta") double theta, @Field("solver") GLMSolver solver, @Field("alpha") double[] alpha,
            @Field("lambda") double[] lambda, @Field("startval") double[] startval, @Field("lambda_search") boolean lambda_search,
            @Field("early_stopping") boolean early_stopping, @Field("nlambdas") int nlambdas, @Field("standardize") boolean standardize,
            @Field("missing_values_handling") GLMMissingValuesHandling missing_values_handling, @Field("plug_values") String plug_values,
            @Field("non_negative") boolean non_negative, @Field("max_iterations") int max_iterations,
            @Field("beta_epsilon") double beta_epsilon, @Field("objective_epsilon") double objective_epsilon,
            @Field("gradient_epsilon") double gradient_epsilon, @Field("obj_reg") double obj_reg, @Field("link") GLMLink link,
            @Field("intercept") boolean intercept, @Field("prior") double prior, @Field("cold_start") boolean cold_start,
            @Field("lambda_min_ratio") double lambda_min_ratio, @Field("beta_constraints") String beta_constraints,
            @Field("max_active_predictors") int max_active_predictors, @Field("interactions") String[] interactions,
            @Field("interaction_pairs") StringPairV3[] interaction_pairs, @Field("balance_classes") boolean balance_classes,
            @Field("class_sampling_factors") float[] class_sampling_factors, @Field("max_after_balance_size") float max_after_balance_size,
            @Field("max_confusion_matrix_size") int max_confusion_matrix_size, @Field("compute_p_values") boolean compute_p_values,
            @Field("remove_collinear_columns") boolean remove_collinear_columns, @Field("num_knots") int[] num_knots,
            @Field("spline_orders") int[] spline_orders, @Field("gam_columns") String[][] gam_columns, @Field("scale") double[] scale,
            @Field("bs") int[] bs, @Field("keep_gam_cols") boolean keep_gam_cols,
            @Field("standardize_tp_gam_cols") boolean standardize_tp_gam_cols, @Field("scale_tp_penalty_mat") boolean scale_tp_penalty_mat,
            @Field("knot_ids") String[] knot_ids, @Field("model_id") String model_id, @Field("training_frame") String training_frame,
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
            @Field("stopping_tolerance") double stopping_tolerance, @Field("gainslift_bins") int gainslift_bins,
            @Field("custom_metric_func") String custom_metric_func, @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir, @Field("auc_type") MultinomialAucType auc_type);

    @FormUrlEncoded
    @POST("/3/ModelBuilders/gam/parameters")
    Call<GAMV3> validate_parametersGam(@Field("gam_columns") String[][] gam_columns);

    /**
     * Train a ANOVAGLM model.
     *   @param seed Seed for pseudo random number generator (if applicable)
     *   @param standardize Standardize numeric columns to have zero mean and unit variance
     *   @param family Family. Use binomial for classification with logistic regression, others are for regression
     *                 problems.
     *   @param tweedie_variance_power Tweedie variance power
     *   @param tweedie_link_power Tweedie link power
     *   @param theta Theta
     *   @param alpha Distribution of regularization between the L1 (Lasso) and L2 (Ridge) penalties. A value of 1 for
     *                alpha represents Lasso regression, a value of 0 produces Ridge regression, and anything in between
     *                specifies the amount of mixing between the two. Default value of alpha is 0 when SOLVER = 'L-BFGS';
     *                0.5 otherwise.
     *   @param lambda Regularization strength
     *   @param lambda_search Use lambda search starting at lambda max, given lambda is then interpreted as lambda min
     *   @param solver AUTO will set the solver based on given data and the other parameters. IRLSM is fast on on problems
     *                 with small number of predictors and for lambda-search with L1 penalty, L_BFGS scales better for
     *                 datasets with many columns.
     *   @param missing_values_handling Handling of missing values. Either MeanImputation, Skip or PlugValues.
     *   @param plug_values Plug Values (a single row frame containing values that will be used to impute missing values
     *                      of the training/validation frame, use with conjunction missing_values_handling = PlugValues)
     *   @param non_negative Restrict coefficients (not intercept) to be non-negative
     *   @param compute_p_values Request p-values computation, p-values work only with IRLSM solver and no regularization
     *   @param max_iterations Maximum number of iterations
     *   @param link Link function.
     *   @param prior Prior probability for y==1. To be used only for logistic regression iff the data has been sampled
     *                and the mean of response does not reflect reality.
     *   @param balance_classes Balance training data class counts via over/under-sampling (for imbalanced data).
     *   @param class_sampling_factors Desired over/under-sampling ratios per class (in lexicographic order). If not
     *                                 specified, sampling factors will be automatically computed to obtain class balance
     *                                 during training. Requires balance_classes.
     *   @param max_after_balance_size Maximum relative size of the training data after balancing class counts (can be
     *                                 less than 1.0). Requires balance_classes.
     *   @param highest_interaction_term Limit the number of interaction terms, if 2 means interaction between 2 columns
     *                                   only, 3 for three columns and so on...  Default to 2.
     *   @param type Refer to the SS type 1, 2, 3, or 4.  We are currently only supporting 3
     *   @param early_stopping Stop early when there is no more relative improvement on train or validation (if provided).
     *   @param save_transformed_framekeys true to save the keys of transformed predictors and interaction column.
     *   @param nparallelism Number of models to build in parallel.  Default to 4.  Adjust according to your system.
     *   @param model_id Destination id for this model; auto-generated if not specified.
     *   @param training_frame Id of the training data frame.
     *   @param validation_frame Id of the validation data frame.
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or >= 2).
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
     *                         If you set weight = 0 for a row, the returned prediction frame at that row is zero and this
     *                         is incorrect. To get an accurate prediction, remove all rows with weight == 0.
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
     *   @param gainslift_bins Gains/Lift table number of bins. 0 means disabled.. Default value -1 means automatic
     *                         binning.
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     *   @param auc_type Set default multinomial AUC type.
     */
    @FormUrlEncoded
    @POST("/3/ModelBuilders/anovaglm")
    Call<ANOVAGLMV3> trainAnovaglm(@Field("seed") long seed, @Field("standardize") boolean standardize, @Field("family") GLMFamily family,
            @Field("tweedie_variance_power") double tweedie_variance_power, @Field("tweedie_link_power") double tweedie_link_power,
            @Field("theta") double theta, @Field("alpha") double[] alpha, @Field("lambda") double[] lambda,
            @Field("lambda_search") boolean lambda_search, @Field("solver") GLMSolver solver,
            @Field("missing_values_handling") GLMMissingValuesHandling missing_values_handling, @Field("plug_values") String plug_values,
            @Field("non_negative") boolean non_negative, @Field("compute_p_values") boolean compute_p_values,
            @Field("max_iterations") int max_iterations, @Field("link") GLMLink link, @Field("prior") double prior,
            @Field("balance_classes") boolean balance_classes, @Field("class_sampling_factors") float[] class_sampling_factors,
            @Field("max_after_balance_size") float max_after_balance_size, @Field("highest_interaction_term") int highest_interaction_term,
            @Field("type") int type, @Field("early_stopping") boolean early_stopping,
            @Field("save_transformed_framekeys") boolean save_transformed_framekeys, @Field("nparallelism") int nparallelism,
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
            @Field("stopping_tolerance") double stopping_tolerance, @Field("gainslift_bins") int gainslift_bins,
            @Field("custom_metric_func") String custom_metric_func, @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir, @Field("auc_type") MultinomialAucType auc_type);

    @FormUrlEncoded
    @POST("/3/ModelBuilders/anovaglm")
    Call<ANOVAGLMV3> trainAnovaglm();

    /**
     * Validate a set of ANOVAGLM model builder parameters.
     *   @param seed Seed for pseudo random number generator (if applicable)
     *   @param standardize Standardize numeric columns to have zero mean and unit variance
     *   @param family Family. Use binomial for classification with logistic regression, others are for regression
     *                 problems.
     *   @param tweedie_variance_power Tweedie variance power
     *   @param tweedie_link_power Tweedie link power
     *   @param theta Theta
     *   @param alpha Distribution of regularization between the L1 (Lasso) and L2 (Ridge) penalties. A value of 1 for
     *                alpha represents Lasso regression, a value of 0 produces Ridge regression, and anything in between
     *                specifies the amount of mixing between the two. Default value of alpha is 0 when SOLVER = 'L-BFGS';
     *                0.5 otherwise.
     *   @param lambda Regularization strength
     *   @param lambda_search Use lambda search starting at lambda max, given lambda is then interpreted as lambda min
     *   @param solver AUTO will set the solver based on given data and the other parameters. IRLSM is fast on on problems
     *                 with small number of predictors and for lambda-search with L1 penalty, L_BFGS scales better for
     *                 datasets with many columns.
     *   @param missing_values_handling Handling of missing values. Either MeanImputation, Skip or PlugValues.
     *   @param plug_values Plug Values (a single row frame containing values that will be used to impute missing values
     *                      of the training/validation frame, use with conjunction missing_values_handling = PlugValues)
     *   @param non_negative Restrict coefficients (not intercept) to be non-negative
     *   @param compute_p_values Request p-values computation, p-values work only with IRLSM solver and no regularization
     *   @param max_iterations Maximum number of iterations
     *   @param link Link function.
     *   @param prior Prior probability for y==1. To be used only for logistic regression iff the data has been sampled
     *                and the mean of response does not reflect reality.
     *   @param balance_classes Balance training data class counts via over/under-sampling (for imbalanced data).
     *   @param class_sampling_factors Desired over/under-sampling ratios per class (in lexicographic order). If not
     *                                 specified, sampling factors will be automatically computed to obtain class balance
     *                                 during training. Requires balance_classes.
     *   @param max_after_balance_size Maximum relative size of the training data after balancing class counts (can be
     *                                 less than 1.0). Requires balance_classes.
     *   @param highest_interaction_term Limit the number of interaction terms, if 2 means interaction between 2 columns
     *                                   only, 3 for three columns and so on...  Default to 2.
     *   @param type Refer to the SS type 1, 2, 3, or 4.  We are currently only supporting 3
     *   @param early_stopping Stop early when there is no more relative improvement on train or validation (if provided).
     *   @param save_transformed_framekeys true to save the keys of transformed predictors and interaction column.
     *   @param nparallelism Number of models to build in parallel.  Default to 4.  Adjust according to your system.
     *   @param model_id Destination id for this model; auto-generated if not specified.
     *   @param training_frame Id of the training data frame.
     *   @param validation_frame Id of the validation data frame.
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or >= 2).
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
     *                         If you set weight = 0 for a row, the returned prediction frame at that row is zero and this
     *                         is incorrect. To get an accurate prediction, remove all rows with weight == 0.
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
     *   @param gainslift_bins Gains/Lift table number of bins. 0 means disabled.. Default value -1 means automatic
     *                         binning.
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     *   @param auc_type Set default multinomial AUC type.
     */
    @FormUrlEncoded
    @POST("/3/ModelBuilders/anovaglm/parameters")
    Call<ANOVAGLMV3> validate_parametersAnovaglm(@Field("seed") long seed, @Field("standardize") boolean standardize,
            @Field("family") GLMFamily family, @Field("tweedie_variance_power") double tweedie_variance_power,
            @Field("tweedie_link_power") double tweedie_link_power, @Field("theta") double theta, @Field("alpha") double[] alpha,
            @Field("lambda") double[] lambda, @Field("lambda_search") boolean lambda_search, @Field("solver") GLMSolver solver,
            @Field("missing_values_handling") GLMMissingValuesHandling missing_values_handling, @Field("plug_values") String plug_values,
            @Field("non_negative") boolean non_negative, @Field("compute_p_values") boolean compute_p_values,
            @Field("max_iterations") int max_iterations, @Field("link") GLMLink link, @Field("prior") double prior,
            @Field("balance_classes") boolean balance_classes, @Field("class_sampling_factors") float[] class_sampling_factors,
            @Field("max_after_balance_size") float max_after_balance_size, @Field("highest_interaction_term") int highest_interaction_term,
            @Field("type") int type, @Field("early_stopping") boolean early_stopping,
            @Field("save_transformed_framekeys") boolean save_transformed_framekeys, @Field("nparallelism") int nparallelism,
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
            @Field("stopping_tolerance") double stopping_tolerance, @Field("gainslift_bins") int gainslift_bins,
            @Field("custom_metric_func") String custom_metric_func, @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir, @Field("auc_type") MultinomialAucType auc_type);

    @FormUrlEncoded
    @POST("/3/ModelBuilders/anovaglm/parameters")
    Call<ANOVAGLMV3> validate_parametersAnovaglm();

    /**
     * Train a PSVM model.
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
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or >= 2).
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
     *                         If you set weight = 0 for a row, the returned prediction frame at that row is zero and this
     *                         is incorrect. To get an accurate prediction, remove all rows with weight == 0.
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
     *   @param gainslift_bins Gains/Lift table number of bins. 0 means disabled.. Default value -1 means automatic
     *                         binning.
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     *   @param auc_type Set default multinomial AUC type.
     */
    @FormUrlEncoded
    @POST("/3/ModelBuilders/psvm")
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
            @Field("stopping_tolerance") double stopping_tolerance, @Field("gainslift_bins") int gainslift_bins,
            @Field("custom_metric_func") String custom_metric_func, @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir, @Field("auc_type") MultinomialAucType auc_type);

    @FormUrlEncoded
    @POST("/3/ModelBuilders/psvm")
    Call<PSVMV3> trainPsvm();

    /**
     * Validate a set of PSVM model builder parameters.
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
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or >= 2).
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
     *                         If you set weight = 0 for a row, the returned prediction frame at that row is zero and this
     *                         is incorrect. To get an accurate prediction, remove all rows with weight == 0.
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
     *   @param gainslift_bins Gains/Lift table number of bins. 0 means disabled.. Default value -1 means automatic
     *                         binning.
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     *   @param auc_type Set default multinomial AUC type.
     */
    @FormUrlEncoded
    @POST("/3/ModelBuilders/psvm/parameters")
    Call<PSVMV3> validate_parametersPsvm(@Field("hyper_param") double hyper_param,
            @Field("kernel_type") GenmodelalgospsvmKernelType kernel_type, @Field("gamma") double gamma,
            @Field("rank_ratio") double rank_ratio, @Field("positive_weight") double positive_weight,
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
            @Field("stopping_tolerance") double stopping_tolerance, @Field("gainslift_bins") int gainslift_bins,
            @Field("custom_metric_func") String custom_metric_func, @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir, @Field("auc_type") MultinomialAucType auc_type);

    @FormUrlEncoded
    @POST("/3/ModelBuilders/psvm/parameters")
    Call<PSVMV3> validate_parametersPsvm();

    /**
     * Train a RuleFit model.
     *   @param seed Seed for pseudo random number generator (if applicable).
     *   @param algorithm The algorithm to use to generate rules.
     *   @param min_rule_length Minimum length of rules. Defaults to 3.
     *   @param max_rule_length Maximum length of rules. Defaults to 3.
     *   @param max_num_rules The maximum number of rules to return. defaults to -1 which means the number of rules is
     *                        selected
     *                        by diminishing returns in model deviance.
     *   @param model_type Specifies type of base learners in the ensemble.
     *   @param rule_generation_ntrees Specifies the number of trees to build in the tree model. Defaults to 50.
     *   @param remove_duplicates Whether to remove rules which are identical to an earlier rule. Defaults to true.
     *   @param lambda Lambda for LASSO regressor.
     *   @param model_id Destination id for this model; auto-generated if not specified.
     *   @param training_frame Id of the training data frame.
     *   @param validation_frame Id of the validation data frame.
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or >= 2).
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
     *                         If you set weight = 0 for a row, the returned prediction frame at that row is zero and this
     *                         is incorrect. To get an accurate prediction, remove all rows with weight == 0.
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
     *   @param gainslift_bins Gains/Lift table number of bins. 0 means disabled.. Default value -1 means automatic
     *                         binning.
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     *   @param auc_type Set default multinomial AUC type.
     */
    @FormUrlEncoded
    @POST("/3/ModelBuilders/rulefit")
    Call<RuleFitV3> trainRulefit(@Field("seed") long seed, @Field("algorithm") RuleFitModelAlgorithm algorithm,
            @Field("min_rule_length") int min_rule_length, @Field("max_rule_length") int max_rule_length,
            @Field("max_num_rules") int max_num_rules, @Field("model_type") RuleFitModelModelType model_type,
            @Field("rule_generation_ntrees") int rule_generation_ntrees, @Field("remove_duplicates") boolean remove_duplicates,
            @Field("lambda") double[] lambda, @Field("model_id") String model_id, @Field("training_frame") String training_frame,
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
            @Field("stopping_tolerance") double stopping_tolerance, @Field("gainslift_bins") int gainslift_bins,
            @Field("custom_metric_func") String custom_metric_func, @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir, @Field("auc_type") MultinomialAucType auc_type);

    @FormUrlEncoded
    @POST("/3/ModelBuilders/rulefit")
    Call<RuleFitV3> trainRulefit();

    /**
     * Validate a set of RuleFit model builder parameters.
     *   @param seed Seed for pseudo random number generator (if applicable).
     *   @param algorithm The algorithm to use to generate rules.
     *   @param min_rule_length Minimum length of rules. Defaults to 3.
     *   @param max_rule_length Maximum length of rules. Defaults to 3.
     *   @param max_num_rules The maximum number of rules to return. defaults to -1 which means the number of rules is
     *                        selected
     *                        by diminishing returns in model deviance.
     *   @param model_type Specifies type of base learners in the ensemble.
     *   @param rule_generation_ntrees Specifies the number of trees to build in the tree model. Defaults to 50.
     *   @param remove_duplicates Whether to remove rules which are identical to an earlier rule. Defaults to true.
     *   @param lambda Lambda for LASSO regressor.
     *   @param model_id Destination id for this model; auto-generated if not specified.
     *   @param training_frame Id of the training data frame.
     *   @param validation_frame Id of the validation data frame.
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or >= 2).
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
     *                         If you set weight = 0 for a row, the returned prediction frame at that row is zero and this
     *                         is incorrect. To get an accurate prediction, remove all rows with weight == 0.
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
     *   @param gainslift_bins Gains/Lift table number of bins. 0 means disabled.. Default value -1 means automatic
     *                         binning.
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     *   @param auc_type Set default multinomial AUC type.
     */
    @FormUrlEncoded
    @POST("/3/ModelBuilders/rulefit/parameters")
    Call<RuleFitV3> validate_parametersRulefit(@Field("seed") long seed, @Field("algorithm") RuleFitModelAlgorithm algorithm,
            @Field("min_rule_length") int min_rule_length, @Field("max_rule_length") int max_rule_length,
            @Field("max_num_rules") int max_num_rules, @Field("model_type") RuleFitModelModelType model_type,
            @Field("rule_generation_ntrees") int rule_generation_ntrees, @Field("remove_duplicates") boolean remove_duplicates,
            @Field("lambda") double[] lambda, @Field("model_id") String model_id, @Field("training_frame") String training_frame,
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
            @Field("stopping_tolerance") double stopping_tolerance, @Field("gainslift_bins") int gainslift_bins,
            @Field("custom_metric_func") String custom_metric_func, @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir, @Field("auc_type") MultinomialAucType auc_type);

    @FormUrlEncoded
    @POST("/3/ModelBuilders/rulefit/parameters")
    Call<RuleFitV3> validate_parametersRulefit();

    /**
     * Train a UpliftDRF model.
     *   @param mtries Number of variables randomly sampled as candidates at each split. If set to -1, defaults to sqrt{p}
     *                 for classification and p/3 for regression (where p is the # of predictors
     *   @param sample_rate Row sample rate per tree (from 0.0 to 1.0)
     *   @param treatment_column Define the column which will be used for computing uplift gain to select best split for a
     *                           tree. The column has to divide the dataset into treatment (value 1) and control (value 0)
     *                           groups.
     *   @param uplift_metric Divergence metric used to find best split when building an uplift tree.
     *   @param auuc_type Metric used to calculate Area Under Uplift Curve.
     *   @param auuc_nbins Number of bins to calculate Area Under Uplift Curve.
     *   @param balance_classes Balance training data class counts via over/under-sampling (for imbalanced data).
     *   @param class_sampling_factors Desired over/under-sampling ratios per class (in lexicographic order). If not
     *                                 specified, sampling factors will be automatically computed to obtain class balance
     *                                 during training. Requires balance_classes.
     *   @param max_after_balance_size Maximum relative size of the training data after balancing class counts (can be
     *                                 less than 1.0). Requires balance_classes.
     *   @param max_confusion_matrix_size [Deprecated] Maximum size (# classes) for confusion matrices to be printed in
     *                                    the Logs
     *   @param ntrees Number of trees.
     *   @param max_depth Maximum tree depth (0 for unlimited).
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
     *   @param build_tree_one_node Run on one node only; no network overhead but fewer cpus used. Suitable for small
     *                              datasets.
     *   @param sample_rate_per_class A list of row sample rates per class (relative fraction for each class, from 0.0 to
     *                                1.0), for each tree
     *   @param col_sample_rate_per_tree Column sample rate per tree (from 0.0 to 1.0)
     *   @param col_sample_rate_change_per_level Relative change of the column sampling rate for every level (must be >
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
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or >= 2).
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
     *                         If you set weight = 0 for a row, the returned prediction frame at that row is zero and this
     *                         is incorrect. To get an accurate prediction, remove all rows with weight == 0.
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
     *   @param gainslift_bins Gains/Lift table number of bins. 0 means disabled.. Default value -1 means automatic
     *                         binning.
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     *   @param auc_type Set default multinomial AUC type.
     */
    @FormUrlEncoded
    @POST("/3/ModelBuilders/upliftdrf")
    Call<UpliftDRFV3> trainUpliftdrf(@Field("mtries") int mtries, @Field("sample_rate") double sample_rate,
            @Field("treatment_column") String treatment_column,
            @Field("uplift_metric") TreeupliftUpliftDRFModelUpliftDRFParametersUpliftMetricType uplift_metric,
            @Field("auuc_type") AUUCType auuc_type, @Field("auuc_nbins") int auuc_nbins, @Field("balance_classes") boolean balance_classes,
            @Field("class_sampling_factors") float[] class_sampling_factors, @Field("max_after_balance_size") float max_after_balance_size,
            @Field("max_confusion_matrix_size") int max_confusion_matrix_size, @Field("ntrees") int ntrees,
            @Field("max_depth") int max_depth, @Field("min_rows") double min_rows, @Field("nbins") int nbins,
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
            @Field("stopping_tolerance") double stopping_tolerance, @Field("gainslift_bins") int gainslift_bins,
            @Field("custom_metric_func") String custom_metric_func, @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir, @Field("auc_type") MultinomialAucType auc_type);

    @FormUrlEncoded
    @POST("/3/ModelBuilders/upliftdrf")
    Call<UpliftDRFV3> trainUpliftdrf(@Field("treatment_column") String treatment_column);

    /**
     * Validate a set of UpliftDRF model builder parameters.
     *   @param mtries Number of variables randomly sampled as candidates at each split. If set to -1, defaults to sqrt{p}
     *                 for classification and p/3 for regression (where p is the # of predictors
     *   @param sample_rate Row sample rate per tree (from 0.0 to 1.0)
     *   @param treatment_column Define the column which will be used for computing uplift gain to select best split for a
     *                           tree. The column has to divide the dataset into treatment (value 1) and control (value 0)
     *                           groups.
     *   @param uplift_metric Divergence metric used to find best split when building an uplift tree.
     *   @param auuc_type Metric used to calculate Area Under Uplift Curve.
     *   @param auuc_nbins Number of bins to calculate Area Under Uplift Curve.
     *   @param balance_classes Balance training data class counts via over/under-sampling (for imbalanced data).
     *   @param class_sampling_factors Desired over/under-sampling ratios per class (in lexicographic order). If not
     *                                 specified, sampling factors will be automatically computed to obtain class balance
     *                                 during training. Requires balance_classes.
     *   @param max_after_balance_size Maximum relative size of the training data after balancing class counts (can be
     *                                 less than 1.0). Requires balance_classes.
     *   @param max_confusion_matrix_size [Deprecated] Maximum size (# classes) for confusion matrices to be printed in
     *                                    the Logs
     *   @param ntrees Number of trees.
     *   @param max_depth Maximum tree depth (0 for unlimited).
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
     *   @param build_tree_one_node Run on one node only; no network overhead but fewer cpus used. Suitable for small
     *                              datasets.
     *   @param sample_rate_per_class A list of row sample rates per class (relative fraction for each class, from 0.0 to
     *                                1.0), for each tree
     *   @param col_sample_rate_per_tree Column sample rate per tree (from 0.0 to 1.0)
     *   @param col_sample_rate_change_per_level Relative change of the column sampling rate for every level (must be >
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
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or >= 2).
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
     *                         If you set weight = 0 for a row, the returned prediction frame at that row is zero and this
     *                         is incorrect. To get an accurate prediction, remove all rows with weight == 0.
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
     *   @param gainslift_bins Gains/Lift table number of bins. 0 means disabled.. Default value -1 means automatic
     *                         binning.
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     *   @param auc_type Set default multinomial AUC type.
     */
    @FormUrlEncoded
    @POST("/3/ModelBuilders/upliftdrf/parameters")
    Call<UpliftDRFV3> validate_parametersUpliftdrf(@Field("mtries") int mtries, @Field("sample_rate") double sample_rate,
            @Field("treatment_column") String treatment_column,
            @Field("uplift_metric") TreeupliftUpliftDRFModelUpliftDRFParametersUpliftMetricType uplift_metric,
            @Field("auuc_type") AUUCType auuc_type, @Field("auuc_nbins") int auuc_nbins, @Field("balance_classes") boolean balance_classes,
            @Field("class_sampling_factors") float[] class_sampling_factors, @Field("max_after_balance_size") float max_after_balance_size,
            @Field("max_confusion_matrix_size") int max_confusion_matrix_size, @Field("ntrees") int ntrees,
            @Field("max_depth") int max_depth, @Field("min_rows") double min_rows, @Field("nbins") int nbins,
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
            @Field("stopping_tolerance") double stopping_tolerance, @Field("gainslift_bins") int gainslift_bins,
            @Field("custom_metric_func") String custom_metric_func, @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir, @Field("auc_type") MultinomialAucType auc_type);

    @FormUrlEncoded
    @POST("/3/ModelBuilders/upliftdrf/parameters")
    Call<UpliftDRFV3> validate_parametersUpliftdrf(@Field("treatment_column") String treatment_column);

    /**
     * Train a ModelSelection model.
     *   @param seed Seed for pseudo random number generator (if applicable)
     *   @param family Family. For MaxR, only gaussian.  For backward, ordinal and multinomial families are not supported
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
     *   @param score_iteration_interval Perform scoring for every score_iteration_interval iterations
     *   @param standardize Standardize numeric columns to have zero mean and unit variance
     *   @param cold_start Only applicable to multiple alpha/lambda values.  If false, build the next model for next set
     *                     of alpha/lambda values starting from the values provided by current model.  If true will start
     *                     GLM model from scratch.
     *   @param missing_values_handling Handling of missing values. Either MeanImputation, Skip or PlugValues.
     *   @param plug_values Plug Values (a single row frame containing values that will be used to impute missing values
     *                      of the training/validation frame, use with conjunction missing_values_handling = PlugValues)
     *   @param non_negative Restrict coefficients (not intercept) to be non-negative
     *   @param max_iterations Maximum number of iterations
     *   @param beta_epsilon Converge if  beta changes less (using L-infinity norm) than beta esilon, ONLY applies to
     *                       IRLSM solver
     *   @param objective_epsilon Converge if  objective value changes less than this. Default (of -1.0) indicates: If
     *                            lambda_search is set to True the value of objective_epsilon is set to .0001. If the
     *                            lambda_search is set to False and lambda is equal to zero, the value of
     *                            objective_epsilon is set to .000001, for any other value of lambda the default value of
     *                            objective_epsilon is set to .0001.
     *   @param gradient_epsilon Converge if  objective changes less (using L-infinity norm) than this, ONLY applies to
     *                           L-BFGS solver. Default (of -1.0) indicates: If lambda_search is set to False and lambda
     *                           is equal to zero, the default value of gradient_epsilon is equal to .000001, otherwise
     *                           the default value is .0001. If lambda_search is set to True, the conditional values above
     *                           are 1E-8 and 1E-6 respectively.
     *   @param obj_reg Likelihood divider in objective value computation, default (of -1.0) will set it to 1/nobs
     *   @param link Link function.
     *   @param startval double array to initialize fixed and random coefficients for HGLM, coefficients for GLM.
     *   @param calc_like if true, will return likelihood function value for HGLM.
     *   @param mode Mode: Used to choose model selection algorithms to use.  Options include 'allsubsets' for all
     *               subsets, 'maxr' for MaxR, 'backward' for backward selection
     *   @param intercept Include constant term in the model
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
     *   @param balance_classes Balance training data class counts via over/under-sampling (for imbalanced data).
     *   @param class_sampling_factors Desired over/under-sampling ratios per class (in lexicographic order). If not
     *                                 specified, sampling factors will be automatically computed to obtain class balance
     *                                 during training. Requires balance_classes.
     *   @param max_after_balance_size Maximum relative size of the training data after balancing class counts (can be
     *                                 less than 1.0). Requires balance_classes.
     *   @param max_confusion_matrix_size [Deprecated] Maximum size (# classes) for confusion matrices to be printed in
     *                                    the Logs
     *   @param compute_p_values Request p-values computation, p-values work only with IRLSM solver and no regularization
     *   @param remove_collinear_columns In case of linearly dependent columns, remove some of the dependent columns
     *   @param max_predictor_number Maximum number of predictors to be considered when building GLM models.  Defaults to
     *                               1.
     *   @param min_predictor_number For mode = 'backward' only.  Minimum number of predictors to be considered when
     *                               building GLM models starting with all predictors to be included.  Defaults to 1.
     *   @param nparallelism number of models to build in parallel.  Defaults to 0.0 which is adaptive to the system
     *                       capability
     *   @param p_values_threshold For mode='backward' only.  If specified, will stop the model building process when all
     *                             coefficientsp-values drop below this threshold
     *   @param model_id Destination id for this model; auto-generated if not specified.
     *   @param training_frame Id of the training data frame.
     *   @param validation_frame Id of the validation data frame.
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or >= 2).
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
     *                         If you set weight = 0 for a row, the returned prediction frame at that row is zero and this
     *                         is incorrect. To get an accurate prediction, remove all rows with weight == 0.
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
     *   @param gainslift_bins Gains/Lift table number of bins. 0 means disabled.. Default value -1 means automatic
     *                         binning.
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     *   @param auc_type Set default multinomial AUC type.
     */
    @FormUrlEncoded
    @POST("/3/ModelBuilders/modelselection")
    Call<ModelSelectionV3> trainModelselection(@Field("seed") long seed, @Field("family") GLMFamily family,
            @Field("tweedie_variance_power") double tweedie_variance_power, @Field("tweedie_link_power") double tweedie_link_power,
            @Field("theta") double theta, @Field("solver") GLMSolver solver, @Field("alpha") double[] alpha,
            @Field("lambda") double[] lambda, @Field("lambda_search") boolean lambda_search,
            @Field("early_stopping") boolean early_stopping, @Field("nlambdas") int nlambdas,
            @Field("score_iteration_interval") int score_iteration_interval, @Field("standardize") boolean standardize,
            @Field("cold_start") boolean cold_start, @Field("missing_values_handling") GLMMissingValuesHandling missing_values_handling,
            @Field("plug_values") String plug_values, @Field("non_negative") boolean non_negative,
            @Field("max_iterations") int max_iterations, @Field("beta_epsilon") double beta_epsilon,
            @Field("objective_epsilon") double objective_epsilon, @Field("gradient_epsilon") double gradient_epsilon,
            @Field("obj_reg") double obj_reg, @Field("link") GLMLink link, @Field("startval") double[] startval,
            @Field("calc_like") boolean calc_like, @Field("mode") ModelSelectionMode mode, @Field("intercept") boolean intercept,
            @Field("prior") double prior, @Field("lambda_min_ratio") double lambda_min_ratio,
            @Field("beta_constraints") String beta_constraints, @Field("max_active_predictors") int max_active_predictors,
            @Field("balance_classes") boolean balance_classes, @Field("class_sampling_factors") float[] class_sampling_factors,
            @Field("max_after_balance_size") float max_after_balance_size,
            @Field("max_confusion_matrix_size") int max_confusion_matrix_size, @Field("compute_p_values") boolean compute_p_values,
            @Field("remove_collinear_columns") boolean remove_collinear_columns, @Field("max_predictor_number") int max_predictor_number,
            @Field("min_predictor_number") int min_predictor_number, @Field("nparallelism") int nparallelism,
            @Field("p_values_threshold") double p_values_threshold, @Field("model_id") String model_id,
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
            @Field("stopping_tolerance") double stopping_tolerance, @Field("gainslift_bins") int gainslift_bins,
            @Field("custom_metric_func") String custom_metric_func, @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir, @Field("auc_type") MultinomialAucType auc_type);

    @FormUrlEncoded
    @POST("/3/ModelBuilders/modelselection")
    Call<ModelSelectionV3> trainModelselection();

    /**
     * Validate a set of ModelSelection model builder parameters.
     *   @param seed Seed for pseudo random number generator (if applicable)
     *   @param family Family. For MaxR, only gaussian.  For backward, ordinal and multinomial families are not supported
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
     *   @param score_iteration_interval Perform scoring for every score_iteration_interval iterations
     *   @param standardize Standardize numeric columns to have zero mean and unit variance
     *   @param cold_start Only applicable to multiple alpha/lambda values.  If false, build the next model for next set
     *                     of alpha/lambda values starting from the values provided by current model.  If true will start
     *                     GLM model from scratch.
     *   @param missing_values_handling Handling of missing values. Either MeanImputation, Skip or PlugValues.
     *   @param plug_values Plug Values (a single row frame containing values that will be used to impute missing values
     *                      of the training/validation frame, use with conjunction missing_values_handling = PlugValues)
     *   @param non_negative Restrict coefficients (not intercept) to be non-negative
     *   @param max_iterations Maximum number of iterations
     *   @param beta_epsilon Converge if  beta changes less (using L-infinity norm) than beta esilon, ONLY applies to
     *                       IRLSM solver
     *   @param objective_epsilon Converge if  objective value changes less than this. Default (of -1.0) indicates: If
     *                            lambda_search is set to True the value of objective_epsilon is set to .0001. If the
     *                            lambda_search is set to False and lambda is equal to zero, the value of
     *                            objective_epsilon is set to .000001, for any other value of lambda the default value of
     *                            objective_epsilon is set to .0001.
     *   @param gradient_epsilon Converge if  objective changes less (using L-infinity norm) than this, ONLY applies to
     *                           L-BFGS solver. Default (of -1.0) indicates: If lambda_search is set to False and lambda
     *                           is equal to zero, the default value of gradient_epsilon is equal to .000001, otherwise
     *                           the default value is .0001. If lambda_search is set to True, the conditional values above
     *                           are 1E-8 and 1E-6 respectively.
     *   @param obj_reg Likelihood divider in objective value computation, default (of -1.0) will set it to 1/nobs
     *   @param link Link function.
     *   @param startval double array to initialize fixed and random coefficients for HGLM, coefficients for GLM.
     *   @param calc_like if true, will return likelihood function value for HGLM.
     *   @param mode Mode: Used to choose model selection algorithms to use.  Options include 'allsubsets' for all
     *               subsets, 'maxr' for MaxR, 'backward' for backward selection
     *   @param intercept Include constant term in the model
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
     *   @param balance_classes Balance training data class counts via over/under-sampling (for imbalanced data).
     *   @param class_sampling_factors Desired over/under-sampling ratios per class (in lexicographic order). If not
     *                                 specified, sampling factors will be automatically computed to obtain class balance
     *                                 during training. Requires balance_classes.
     *   @param max_after_balance_size Maximum relative size of the training data after balancing class counts (can be
     *                                 less than 1.0). Requires balance_classes.
     *   @param max_confusion_matrix_size [Deprecated] Maximum size (# classes) for confusion matrices to be printed in
     *                                    the Logs
     *   @param compute_p_values Request p-values computation, p-values work only with IRLSM solver and no regularization
     *   @param remove_collinear_columns In case of linearly dependent columns, remove some of the dependent columns
     *   @param max_predictor_number Maximum number of predictors to be considered when building GLM models.  Defaults to
     *                               1.
     *   @param min_predictor_number For mode = 'backward' only.  Minimum number of predictors to be considered when
     *                               building GLM models starting with all predictors to be included.  Defaults to 1.
     *   @param nparallelism number of models to build in parallel.  Defaults to 0.0 which is adaptive to the system
     *                       capability
     *   @param p_values_threshold For mode='backward' only.  If specified, will stop the model building process when all
     *                             coefficientsp-values drop below this threshold
     *   @param model_id Destination id for this model; auto-generated if not specified.
     *   @param training_frame Id of the training data frame.
     *   @param validation_frame Id of the validation data frame.
     *   @param nfolds Number of folds for K-fold cross-validation (0 to disable or >= 2).
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
     *                         If you set weight = 0 for a row, the returned prediction frame at that row is zero and this
     *                         is incorrect. To get an accurate prediction, remove all rows with weight == 0.
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
     *   @param gainslift_bins Gains/Lift table number of bins. 0 means disabled.. Default value -1 means automatic
     *                         binning.
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param custom_distribution_func Reference to custom distribution, format: `language:keyName=funcName`
     *   @param export_checkpoints_dir Automatically export generated models to this directory.
     *   @param auc_type Set default multinomial AUC type.
     */
    @FormUrlEncoded
    @POST("/3/ModelBuilders/modelselection/parameters")
    Call<ModelSelectionV3> validate_parametersModelselection(@Field("seed") long seed, @Field("family") GLMFamily family,
            @Field("tweedie_variance_power") double tweedie_variance_power, @Field("tweedie_link_power") double tweedie_link_power,
            @Field("theta") double theta, @Field("solver") GLMSolver solver, @Field("alpha") double[] alpha,
            @Field("lambda") double[] lambda, @Field("lambda_search") boolean lambda_search,
            @Field("early_stopping") boolean early_stopping, @Field("nlambdas") int nlambdas,
            @Field("score_iteration_interval") int score_iteration_interval, @Field("standardize") boolean standardize,
            @Field("cold_start") boolean cold_start, @Field("missing_values_handling") GLMMissingValuesHandling missing_values_handling,
            @Field("plug_values") String plug_values, @Field("non_negative") boolean non_negative,
            @Field("max_iterations") int max_iterations, @Field("beta_epsilon") double beta_epsilon,
            @Field("objective_epsilon") double objective_epsilon, @Field("gradient_epsilon") double gradient_epsilon,
            @Field("obj_reg") double obj_reg, @Field("link") GLMLink link, @Field("startval") double[] startval,
            @Field("calc_like") boolean calc_like, @Field("mode") ModelSelectionMode mode, @Field("intercept") boolean intercept,
            @Field("prior") double prior, @Field("lambda_min_ratio") double lambda_min_ratio,
            @Field("beta_constraints") String beta_constraints, @Field("max_active_predictors") int max_active_predictors,
            @Field("balance_classes") boolean balance_classes, @Field("class_sampling_factors") float[] class_sampling_factors,
            @Field("max_after_balance_size") float max_after_balance_size,
            @Field("max_confusion_matrix_size") int max_confusion_matrix_size, @Field("compute_p_values") boolean compute_p_values,
            @Field("remove_collinear_columns") boolean remove_collinear_columns, @Field("max_predictor_number") int max_predictor_number,
            @Field("min_predictor_number") int min_predictor_number, @Field("nparallelism") int nparallelism,
            @Field("p_values_threshold") double p_values_threshold, @Field("model_id") String model_id,
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
            @Field("stopping_tolerance") double stopping_tolerance, @Field("gainslift_bins") int gainslift_bins,
            @Field("custom_metric_func") String custom_metric_func, @Field("custom_distribution_func") String custom_distribution_func,
            @Field("export_checkpoints_dir") String export_checkpoints_dir, @Field("auc_type") MultinomialAucType auc_type);

    @FormUrlEncoded
    @POST("/3/ModelBuilders/modelselection/parameters")
    Call<ModelSelectionV3> validate_parametersModelselection();

    /**
     * Return a new unique model_id for the specified algorithm.
     *   @param algo Algo of ModelBuilder of interest
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @FormUrlEncoded
    @POST("/3/ModelBuilders/{algo}/model_id")
    Call<ModelIdV3> calcModelId(@Path("algo") String algo, @Field("_exclude_fields") String _exclude_fields);

    @FormUrlEncoded
    @POST("/3/ModelBuilders/{algo}/model_id")
    Call<ModelIdV3> calcModelId(@Path("algo") String algo);

    /**
     * Return the Model Builder metadata for the specified algorithm.
     *   @param algo Algo of ModelBuilder of interest
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @GET("/3/ModelBuilders/{algo}")
    Call<ModelBuildersV3> fetch(@Path("algo") String algo, @Query("_exclude_fields") String _exclude_fields);

    @GET("/3/ModelBuilders/{algo}")
    Call<ModelBuildersV3> fetch(@Path("algo") String algo);

    /**
     * Return the Model Builder metadata for all available algorithms.
     *   @param algo Algo of ModelBuilder of interest
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @GET("/3/ModelBuilders")
    Call<ModelBuildersV3> list(@Query("algo") String algo, @Query("_exclude_fields") String _exclude_fields);

    @GET("/3/ModelBuilders")
    Call<ModelBuildersV3> list();

    @SuppressWarnings("unused")
    class Helper {
        /**
         * Train a XGBoost model.
         */
        public static Call<XGBoostV3> trainXgboost(final ModelBuilders z, final XGBoostParametersV3 p) {
            return z.trainXgboost(p.ntrees, p.maxDepth, p.minRows, p.minChildWeight, p.learnRate, p.eta, p.sampleRate, p.subsample,
                    p.colSampleRate, p.colsampleBylevel, p.colSampleRatePerTree, p.colsampleBytree, p.colsampleBynode,
                    p.monotoneConstraints, p.maxAbsLeafnodePred, p.maxDeltaStep, p.scoreTreeInterval, p.seed, p.minSplitImprovement,
                    p.gamma, p.nthread, p.buildTreeOneNode, p.saveMatrixDirectory, p.calibrateModel,
                    (p.calibrationFrame == null ? null : p.calibrationFrame.name), p.maxBins, p.maxLeaves, p.treeMethod, p.growPolicy,
                    p.booster, p.regLambda, p.regAlpha, p.quietMode, p.sampleType, p.normalizeType, p.rateDrop, p.oneDrop, p.skipDrop,
                    p.dmatrixType, p.backend, p.gpuId, p.interactionConstraints, p.scalePosWeight,
                    (p.modelId == null ? null : p.modelId.name), (p.trainingFrame == null ? null : p.trainingFrame.name),
                    (p.validationFrame == null ? null : p.validationFrame.name), p.nfolds, p.keepCrossValidationModels,
                    p.keepCrossValidationPredictions, p.keepCrossValidationFoldAssignment, p.parallelizeCrossValidation, p.distribution,
                    p.tweediePower, p.quantileAlpha, p.huberAlpha, (p.responseColumn == null ? null : p.responseColumn.columnName),
                    (p.weightsColumn == null ? null : p.weightsColumn.columnName),
                    (p.offsetColumn == null ? null : p.offsetColumn.columnName), (p.foldColumn == null ? null : p.foldColumn.columnName),
                    p.foldAssignment, p.categoricalEncoding, p.maxCategoricalLevels, p.ignoredColumns, p.ignoreConstCols,
                    p.scoreEachIteration, (p.checkpoint == null ? null : p.checkpoint.name), p.stoppingRounds, p.maxRuntimeSecs,
                    p.stoppingMetric, p.stoppingTolerance, p.gainsliftBins, p.customMetricFunc, p.customDistributionFunc,
                    p.exportCheckpointsDir, p.aucType);
        }

        /**
         * Validate a set of XGBoost model builder parameters.
         */
        public static Call<XGBoostV3> validate_parametersXgboost(final ModelBuilders z, final XGBoostParametersV3 p) {
            return z.validate_parametersXgboost(p.ntrees, p.maxDepth, p.minRows, p.minChildWeight, p.learnRate, p.eta, p.sampleRate,
                    p.subsample, p.colSampleRate, p.colsampleBylevel, p.colSampleRatePerTree, p.colsampleBytree, p.colsampleBynode,
                    p.monotoneConstraints, p.maxAbsLeafnodePred, p.maxDeltaStep, p.scoreTreeInterval, p.seed, p.minSplitImprovement,
                    p.gamma, p.nthread, p.buildTreeOneNode, p.saveMatrixDirectory, p.calibrateModel,
                    (p.calibrationFrame == null ? null : p.calibrationFrame.name), p.maxBins, p.maxLeaves, p.treeMethod, p.growPolicy,
                    p.booster, p.regLambda, p.regAlpha, p.quietMode, p.sampleType, p.normalizeType, p.rateDrop, p.oneDrop, p.skipDrop,
                    p.dmatrixType, p.backend, p.gpuId, p.interactionConstraints, p.scalePosWeight,
                    (p.modelId == null ? null : p.modelId.name), (p.trainingFrame == null ? null : p.trainingFrame.name),
                    (p.validationFrame == null ? null : p.validationFrame.name), p.nfolds, p.keepCrossValidationModels,
                    p.keepCrossValidationPredictions, p.keepCrossValidationFoldAssignment, p.parallelizeCrossValidation, p.distribution,
                    p.tweediePower, p.quantileAlpha, p.huberAlpha, (p.responseColumn == null ? null : p.responseColumn.columnName),
                    (p.weightsColumn == null ? null : p.weightsColumn.columnName),
                    (p.offsetColumn == null ? null : p.offsetColumn.columnName), (p.foldColumn == null ? null : p.foldColumn.columnName),
                    p.foldAssignment, p.categoricalEncoding, p.maxCategoricalLevels, p.ignoredColumns, p.ignoreConstCols,
                    p.scoreEachIteration, (p.checkpoint == null ? null : p.checkpoint.name), p.stoppingRounds, p.maxRuntimeSecs,
                    p.stoppingMetric, p.stoppingTolerance, p.gainsliftBins, p.customMetricFunc, p.customDistributionFunc,
                    p.exportCheckpointsDir, p.aucType);
        }

        /**
         * Train a Infogram model.
         */
        public static Call<InfogramV3> trainInfogram(final ModelBuilders z, final InfogramParametersV3 p) {
            return z.trainInfogram(p.seed, p.standardize, (p.plugValues == null ? null : p.plugValues.name), p.maxIterations, p.prior,
                    p.balanceClasses, p.classSamplingFactors, p.maxAfterBalanceSize, p.algorithm, p.algorithmParams, p.protectedColumns,
                    p.totalInformationThreshold, p.netInformationThreshold, p.relevanceIndexThreshold, p.safetyIndexThreshold,
                    p.dataFraction, p.topNFeatures, (p.modelId == null ? null : p.modelId.name),
                    (p.trainingFrame == null ? null : p.trainingFrame.name), (p.validationFrame == null ? null : p.validationFrame.name),
                    p.nfolds, p.keepCrossValidationModels, p.keepCrossValidationPredictions, p.keepCrossValidationFoldAssignment,
                    p.parallelizeCrossValidation, p.distribution, p.tweediePower, p.quantileAlpha, p.huberAlpha,
                    (p.responseColumn == null ? null : p.responseColumn.columnName),
                    (p.weightsColumn == null ? null : p.weightsColumn.columnName),
                    (p.offsetColumn == null ? null : p.offsetColumn.columnName), (p.foldColumn == null ? null : p.foldColumn.columnName),
                    p.foldAssignment, p.categoricalEncoding, p.maxCategoricalLevels, p.ignoredColumns, p.ignoreConstCols,
                    p.scoreEachIteration, (p.checkpoint == null ? null : p.checkpoint.name), p.stoppingRounds, p.maxRuntimeSecs,
                    p.stoppingMetric, p.stoppingTolerance, p.gainsliftBins, p.customMetricFunc, p.customDistributionFunc,
                    p.exportCheckpointsDir, p.aucType);
        }

        /**
         * Validate a set of Infogram model builder parameters.
         */
        public static Call<InfogramV3> validate_parametersInfogram(final ModelBuilders z, final InfogramParametersV3 p) {
            return z.validate_parametersInfogram(p.seed, p.standardize, (p.plugValues == null ? null : p.plugValues.name), p.maxIterations,
                    p.prior, p.balanceClasses, p.classSamplingFactors, p.maxAfterBalanceSize, p.algorithm, p.algorithmParams,
                    p.protectedColumns, p.totalInformationThreshold, p.netInformationThreshold, p.relevanceIndexThreshold,
                    p.safetyIndexThreshold, p.dataFraction, p.topNFeatures, (p.modelId == null ? null : p.modelId.name),
                    (p.trainingFrame == null ? null : p.trainingFrame.name), (p.validationFrame == null ? null : p.validationFrame.name),
                    p.nfolds, p.keepCrossValidationModels, p.keepCrossValidationPredictions, p.keepCrossValidationFoldAssignment,
                    p.parallelizeCrossValidation, p.distribution, p.tweediePower, p.quantileAlpha, p.huberAlpha,
                    (p.responseColumn == null ? null : p.responseColumn.columnName),
                    (p.weightsColumn == null ? null : p.weightsColumn.columnName),
                    (p.offsetColumn == null ? null : p.offsetColumn.columnName), (p.foldColumn == null ? null : p.foldColumn.columnName),
                    p.foldAssignment, p.categoricalEncoding, p.maxCategoricalLevels, p.ignoredColumns, p.ignoreConstCols,
                    p.scoreEachIteration, (p.checkpoint == null ? null : p.checkpoint.name), p.stoppingRounds, p.maxRuntimeSecs,
                    p.stoppingMetric, p.stoppingTolerance, p.gainsliftBins, p.customMetricFunc, p.customDistributionFunc,
                    p.exportCheckpointsDir, p.aucType);
        }

        /**
         * Train a TargetEncoder model.
         */
        public static Call<TargetEncoderV3> trainTargetencoder(final ModelBuilders z, final TargetEncoderParametersV3 p) {
            return z.trainTargetencoder(p.columnsToEncode, p.keepOriginalCategoricalColumns, p.blending, p.inflectionPoint, p.smoothing,
                    p.dataLeakageHandling, p.noise, p.seed, (p.modelId == null ? null : p.modelId.name),
                    (p.trainingFrame == null ? null : p.trainingFrame.name), (p.validationFrame == null ? null : p.validationFrame.name),
                    p.nfolds, p.keepCrossValidationModels, p.keepCrossValidationPredictions, p.keepCrossValidationFoldAssignment,
                    p.parallelizeCrossValidation, p.distribution, p.tweediePower, p.quantileAlpha, p.huberAlpha,
                    (p.responseColumn == null ? null : p.responseColumn.columnName),
                    (p.weightsColumn == null ? null : p.weightsColumn.columnName),
                    (p.offsetColumn == null ? null : p.offsetColumn.columnName), (p.foldColumn == null ? null : p.foldColumn.columnName),
                    p.foldAssignment, p.categoricalEncoding, p.maxCategoricalLevels, p.ignoredColumns, p.ignoreConstCols,
                    p.scoreEachIteration, (p.checkpoint == null ? null : p.checkpoint.name), p.stoppingRounds, p.maxRuntimeSecs,
                    p.stoppingMetric, p.stoppingTolerance, p.gainsliftBins, p.customMetricFunc, p.customDistributionFunc,
                    p.exportCheckpointsDir, p.aucType);
        }

        /**
         * Validate a set of TargetEncoder model builder parameters.
         */
        public static Call<TargetEncoderV3> validate_parametersTargetencoder(final ModelBuilders z, final TargetEncoderParametersV3 p) {
            return z.validate_parametersTargetencoder(p.columnsToEncode, p.keepOriginalCategoricalColumns, p.blending, p.inflectionPoint,
                    p.smoothing, p.dataLeakageHandling, p.noise, p.seed, (p.modelId == null ? null : p.modelId.name),
                    (p.trainingFrame == null ? null : p.trainingFrame.name), (p.validationFrame == null ? null : p.validationFrame.name),
                    p.nfolds, p.keepCrossValidationModels, p.keepCrossValidationPredictions, p.keepCrossValidationFoldAssignment,
                    p.parallelizeCrossValidation, p.distribution, p.tweediePower, p.quantileAlpha, p.huberAlpha,
                    (p.responseColumn == null ? null : p.responseColumn.columnName),
                    (p.weightsColumn == null ? null : p.weightsColumn.columnName),
                    (p.offsetColumn == null ? null : p.offsetColumn.columnName), (p.foldColumn == null ? null : p.foldColumn.columnName),
                    p.foldAssignment, p.categoricalEncoding, p.maxCategoricalLevels, p.ignoredColumns, p.ignoreConstCols,
                    p.scoreEachIteration, (p.checkpoint == null ? null : p.checkpoint.name), p.stoppingRounds, p.maxRuntimeSecs,
                    p.stoppingMetric, p.stoppingTolerance, p.gainsliftBins, p.customMetricFunc, p.customDistributionFunc,
                    p.exportCheckpointsDir, p.aucType);
        }

        /**
         * Train a DeepLearning model.
         */
        public static Call<DeepLearningV3> trainDeeplearning(final ModelBuilders z, final DeepLearningParametersV3 p) {
            return z.trainDeeplearning(p.balanceClasses, p.classSamplingFactors, p.maxAfterBalanceSize, p.maxConfusionMatrixSize,
                    p.activation, p.hidden, p.epochs, p.trainSamplesPerIteration, p.targetRatioCommToComp, p.seed, p.adaptiveRate, p.rho,
                    p.epsilon, p.rate, p.rateAnnealing, p.rateDecay, p.momentumStart, p.momentumRamp, p.momentumStable,
                    p.nesterovAcceleratedGradient, p.inputDropoutRatio, p.hiddenDropoutRatios, p.l1, p.l2, p.maxW2,
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
                    p.stoppingMetric, p.stoppingTolerance, p.gainsliftBins, p.customMetricFunc, p.customDistributionFunc,
                    p.exportCheckpointsDir, p.aucType);
        }

        /**
         * Validate a set of DeepLearning model builder parameters.
         */
        public static Call<DeepLearningV3> validate_parametersDeeplearning(final ModelBuilders z, final DeepLearningParametersV3 p) {
            return z.validate_parametersDeeplearning(p.balanceClasses, p.classSamplingFactors, p.maxAfterBalanceSize,
                    p.maxConfusionMatrixSize, p.activation, p.hidden, p.epochs, p.trainSamplesPerIteration, p.targetRatioCommToComp, p.seed,
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
                    p.stoppingMetric, p.stoppingTolerance, p.gainsliftBins, p.customMetricFunc, p.customDistributionFunc,
                    p.exportCheckpointsDir, p.aucType);
        }

        /**
         * Train a GLM model.
         */
        public static Call<GLMV3> trainGlm(final ModelBuilders z, final GLMParametersV3 p) {
            return z.trainGlm(p.seed, p.family, p.randFamily, p.tweedieVariancePower, p.tweedieLinkPower, p.theta, p.solver, p.alpha,
                    p.lambda, p.lambdaSearch, p.earlyStopping, p.nlambdas, p.scoreIterationInterval, p.standardize, p.coldStart,
                    p.missingValuesHandling, (p.plugValues == null ? null : p.plugValues.name), p.nonNegative, p.maxIterations,
                    p.betaEpsilon, p.objectiveEpsilon, p.gradientEpsilon, p.objReg, p.link, p.randLink, p.startval, p.randomColumns,
                    p.calcLike, p.intercept, p.hglm, p.prior, p.lambdaMinRatio, (p.betaConstraints == null ? null : p.betaConstraints.name),
                    p.maxActivePredictors, p.interactions, p.interactionPairs, p.balanceClasses, p.classSamplingFactors,
                    p.maxAfterBalanceSize, p.maxConfusionMatrixSize, p.computePValues, p.removeCollinearColumns, p.generateScoringHistory,
                    (p.modelId == null ? null : p.modelId.name), (p.trainingFrame == null ? null : p.trainingFrame.name),
                    (p.validationFrame == null ? null : p.validationFrame.name), p.nfolds, p.keepCrossValidationModels,
                    p.keepCrossValidationPredictions, p.keepCrossValidationFoldAssignment, p.parallelizeCrossValidation, p.distribution,
                    p.tweediePower, p.quantileAlpha, p.huberAlpha, (p.responseColumn == null ? null : p.responseColumn.columnName),
                    (p.weightsColumn == null ? null : p.weightsColumn.columnName),
                    (p.offsetColumn == null ? null : p.offsetColumn.columnName), (p.foldColumn == null ? null : p.foldColumn.columnName),
                    p.foldAssignment, p.categoricalEncoding, p.maxCategoricalLevels, p.ignoredColumns, p.ignoreConstCols,
                    p.scoreEachIteration, (p.checkpoint == null ? null : p.checkpoint.name), p.stoppingRounds, p.maxRuntimeSecs,
                    p.stoppingMetric, p.stoppingTolerance, p.gainsliftBins, p.customMetricFunc, p.customDistributionFunc,
                    p.exportCheckpointsDir, p.aucType);
        }

        /**
         * Validate a set of GLM model builder parameters.
         */
        public static Call<GLMV3> validate_parametersGlm(final ModelBuilders z, final GLMParametersV3 p) {
            return z.validate_parametersGlm(p.seed, p.family, p.randFamily, p.tweedieVariancePower, p.tweedieLinkPower, p.theta, p.solver,
                    p.alpha, p.lambda, p.lambdaSearch, p.earlyStopping, p.nlambdas, p.scoreIterationInterval, p.standardize, p.coldStart,
                    p.missingValuesHandling, (p.plugValues == null ? null : p.plugValues.name), p.nonNegative, p.maxIterations,
                    p.betaEpsilon, p.objectiveEpsilon, p.gradientEpsilon, p.objReg, p.link, p.randLink, p.startval, p.randomColumns,
                    p.calcLike, p.intercept, p.hglm, p.prior, p.lambdaMinRatio, (p.betaConstraints == null ? null : p.betaConstraints.name),
                    p.maxActivePredictors, p.interactions, p.interactionPairs, p.balanceClasses, p.classSamplingFactors,
                    p.maxAfterBalanceSize, p.maxConfusionMatrixSize, p.computePValues, p.removeCollinearColumns, p.generateScoringHistory,
                    (p.modelId == null ? null : p.modelId.name), (p.trainingFrame == null ? null : p.trainingFrame.name),
                    (p.validationFrame == null ? null : p.validationFrame.name), p.nfolds, p.keepCrossValidationModels,
                    p.keepCrossValidationPredictions, p.keepCrossValidationFoldAssignment, p.parallelizeCrossValidation, p.distribution,
                    p.tweediePower, p.quantileAlpha, p.huberAlpha, (p.responseColumn == null ? null : p.responseColumn.columnName),
                    (p.weightsColumn == null ? null : p.weightsColumn.columnName),
                    (p.offsetColumn == null ? null : p.offsetColumn.columnName), (p.foldColumn == null ? null : p.foldColumn.columnName),
                    p.foldAssignment, p.categoricalEncoding, p.maxCategoricalLevels, p.ignoredColumns, p.ignoreConstCols,
                    p.scoreEachIteration, (p.checkpoint == null ? null : p.checkpoint.name), p.stoppingRounds, p.maxRuntimeSecs,
                    p.stoppingMetric, p.stoppingTolerance, p.gainsliftBins, p.customMetricFunc, p.customDistributionFunc,
                    p.exportCheckpointsDir, p.aucType);
        }

        /**
         * Train a GLRM model.
         */
        public static Call<GLRMV3> trainGlrm(final ModelBuilders z, final GLRMParametersV3 p) {
            return z.trainGlrm(p.transform, p.k, p.loss, p.multiLoss, p.lossByCol, p.lossByColIdx, p.period, p.regularizationX,
                    p.regularizationY, p.gammaX, p.gammaY, p.maxIterations, p.maxUpdates, p.initStepSize, p.minStepSize, p.seed, p.init,
                    p.svdMethod, (p.userY == null ? null : p.userY.name), (p.userX == null ? null : p.userX.name), p.loadingName,
                    p.representationName, p.expandUserY, p.imputeOriginal, p.recoverSvd, (p.modelId == null ? null : p.modelId.name),
                    (p.trainingFrame == null ? null : p.trainingFrame.name), (p.validationFrame == null ? null : p.validationFrame.name),
                    p.nfolds, p.keepCrossValidationModels, p.keepCrossValidationPredictions, p.keepCrossValidationFoldAssignment,
                    p.parallelizeCrossValidation, p.distribution, p.tweediePower, p.quantileAlpha, p.huberAlpha,
                    (p.responseColumn == null ? null : p.responseColumn.columnName),
                    (p.weightsColumn == null ? null : p.weightsColumn.columnName),
                    (p.offsetColumn == null ? null : p.offsetColumn.columnName), (p.foldColumn == null ? null : p.foldColumn.columnName),
                    p.foldAssignment, p.categoricalEncoding, p.maxCategoricalLevels, p.ignoredColumns, p.ignoreConstCols,
                    p.scoreEachIteration, (p.checkpoint == null ? null : p.checkpoint.name), p.stoppingRounds, p.maxRuntimeSecs,
                    p.stoppingMetric, p.stoppingTolerance, p.gainsliftBins, p.customMetricFunc, p.customDistributionFunc,
                    p.exportCheckpointsDir, p.aucType);
        }

        /**
         * Validate a set of GLRM model builder parameters.
         */
        public static Call<GLRMV3> validate_parametersGlrm(final ModelBuilders z, final GLRMParametersV3 p) {
            return z.validate_parametersGlrm(p.transform, p.k, p.loss, p.multiLoss, p.lossByCol, p.lossByColIdx, p.period,
                    p.regularizationX, p.regularizationY, p.gammaX, p.gammaY, p.maxIterations, p.maxUpdates, p.initStepSize, p.minStepSize,
                    p.seed, p.init, p.svdMethod, (p.userY == null ? null : p.userY.name), (p.userX == null ? null : p.userX.name),
                    p.loadingName, p.representationName, p.expandUserY, p.imputeOriginal, p.recoverSvd,
                    (p.modelId == null ? null : p.modelId.name), (p.trainingFrame == null ? null : p.trainingFrame.name),
                    (p.validationFrame == null ? null : p.validationFrame.name), p.nfolds, p.keepCrossValidationModels,
                    p.keepCrossValidationPredictions, p.keepCrossValidationFoldAssignment, p.parallelizeCrossValidation, p.distribution,
                    p.tweediePower, p.quantileAlpha, p.huberAlpha, (p.responseColumn == null ? null : p.responseColumn.columnName),
                    (p.weightsColumn == null ? null : p.weightsColumn.columnName),
                    (p.offsetColumn == null ? null : p.offsetColumn.columnName), (p.foldColumn == null ? null : p.foldColumn.columnName),
                    p.foldAssignment, p.categoricalEncoding, p.maxCategoricalLevels, p.ignoredColumns, p.ignoreConstCols,
                    p.scoreEachIteration, (p.checkpoint == null ? null : p.checkpoint.name), p.stoppingRounds, p.maxRuntimeSecs,
                    p.stoppingMetric, p.stoppingTolerance, p.gainsliftBins, p.customMetricFunc, p.customDistributionFunc,
                    p.exportCheckpointsDir, p.aucType);
        }

        /**
         * Train a KMeans model.
         */
        public static Call<KMeansV3> trainKmeans(final ModelBuilders z, final KMeansParametersV3 p) {
            return z.trainKmeans((p.userPoints == null ? null : p.userPoints.name), p.maxIterations, p.standardize, p.seed, p.init,
                    p.estimateK, p.clusterSizeConstraints, p.k, (p.modelId == null ? null : p.modelId.name),
                    (p.trainingFrame == null ? null : p.trainingFrame.name), (p.validationFrame == null ? null : p.validationFrame.name),
                    p.nfolds, p.keepCrossValidationModels, p.keepCrossValidationPredictions, p.keepCrossValidationFoldAssignment,
                    p.parallelizeCrossValidation, p.distribution, p.tweediePower, p.quantileAlpha, p.huberAlpha,
                    (p.responseColumn == null ? null : p.responseColumn.columnName),
                    (p.weightsColumn == null ? null : p.weightsColumn.columnName),
                    (p.offsetColumn == null ? null : p.offsetColumn.columnName), (p.foldColumn == null ? null : p.foldColumn.columnName),
                    p.foldAssignment, p.categoricalEncoding, p.maxCategoricalLevels, p.ignoredColumns, p.ignoreConstCols,
                    p.scoreEachIteration, (p.checkpoint == null ? null : p.checkpoint.name), p.stoppingRounds, p.maxRuntimeSecs,
                    p.stoppingMetric, p.stoppingTolerance, p.gainsliftBins, p.customMetricFunc, p.customDistributionFunc,
                    p.exportCheckpointsDir, p.aucType);
        }

        /**
         * Validate a set of KMeans model builder parameters.
         */
        public static Call<KMeansV3> validate_parametersKmeans(final ModelBuilders z, final KMeansParametersV3 p) {
            return z.validate_parametersKmeans((p.userPoints == null ? null : p.userPoints.name), p.maxIterations, p.standardize, p.seed,
                    p.init, p.estimateK, p.clusterSizeConstraints, p.k, (p.modelId == null ? null : p.modelId.name),
                    (p.trainingFrame == null ? null : p.trainingFrame.name), (p.validationFrame == null ? null : p.validationFrame.name),
                    p.nfolds, p.keepCrossValidationModels, p.keepCrossValidationPredictions, p.keepCrossValidationFoldAssignment,
                    p.parallelizeCrossValidation, p.distribution, p.tweediePower, p.quantileAlpha, p.huberAlpha,
                    (p.responseColumn == null ? null : p.responseColumn.columnName),
                    (p.weightsColumn == null ? null : p.weightsColumn.columnName),
                    (p.offsetColumn == null ? null : p.offsetColumn.columnName), (p.foldColumn == null ? null : p.foldColumn.columnName),
                    p.foldAssignment, p.categoricalEncoding, p.maxCategoricalLevels, p.ignoredColumns, p.ignoreConstCols,
                    p.scoreEachIteration, (p.checkpoint == null ? null : p.checkpoint.name), p.stoppingRounds, p.maxRuntimeSecs,
                    p.stoppingMetric, p.stoppingTolerance, p.gainsliftBins, p.customMetricFunc, p.customDistributionFunc,
                    p.exportCheckpointsDir, p.aucType);
        }

        /**
         * Train a NaiveBayes model.
         */
        public static Call<NaiveBayesV3> trainNaivebayes(final ModelBuilders z, final NaiveBayesParametersV3 p) {
            return z.trainNaivebayes(p.balanceClasses, p.classSamplingFactors, p.maxAfterBalanceSize, p.maxConfusionMatrixSize, p.laplace,
                    p.minSdev, p.epsSdev, p.minProb, p.epsProb, p.computeMetrics, p.seed, (p.modelId == null ? null : p.modelId.name),
                    (p.trainingFrame == null ? null : p.trainingFrame.name), (p.validationFrame == null ? null : p.validationFrame.name),
                    p.nfolds, p.keepCrossValidationModels, p.keepCrossValidationPredictions, p.keepCrossValidationFoldAssignment,
                    p.parallelizeCrossValidation, p.distribution, p.tweediePower, p.quantileAlpha, p.huberAlpha,
                    (p.responseColumn == null ? null : p.responseColumn.columnName),
                    (p.weightsColumn == null ? null : p.weightsColumn.columnName),
                    (p.offsetColumn == null ? null : p.offsetColumn.columnName), (p.foldColumn == null ? null : p.foldColumn.columnName),
                    p.foldAssignment, p.categoricalEncoding, p.maxCategoricalLevels, p.ignoredColumns, p.ignoreConstCols,
                    p.scoreEachIteration, (p.checkpoint == null ? null : p.checkpoint.name), p.stoppingRounds, p.maxRuntimeSecs,
                    p.stoppingMetric, p.stoppingTolerance, p.gainsliftBins, p.customMetricFunc, p.customDistributionFunc,
                    p.exportCheckpointsDir, p.aucType);
        }

        /**
         * Validate a set of NaiveBayes model builder parameters.
         */
        public static Call<NaiveBayesV3> validate_parametersNaivebayes(final ModelBuilders z, final NaiveBayesParametersV3 p) {
            return z.validate_parametersNaivebayes(p.balanceClasses, p.classSamplingFactors, p.maxAfterBalanceSize,
                    p.maxConfusionMatrixSize, p.laplace, p.minSdev, p.epsSdev, p.minProb, p.epsProb, p.computeMetrics, p.seed,
                    (p.modelId == null ? null : p.modelId.name), (p.trainingFrame == null ? null : p.trainingFrame.name),
                    (p.validationFrame == null ? null : p.validationFrame.name), p.nfolds, p.keepCrossValidationModels,
                    p.keepCrossValidationPredictions, p.keepCrossValidationFoldAssignment, p.parallelizeCrossValidation, p.distribution,
                    p.tweediePower, p.quantileAlpha, p.huberAlpha, (p.responseColumn == null ? null : p.responseColumn.columnName),
                    (p.weightsColumn == null ? null : p.weightsColumn.columnName),
                    (p.offsetColumn == null ? null : p.offsetColumn.columnName), (p.foldColumn == null ? null : p.foldColumn.columnName),
                    p.foldAssignment, p.categoricalEncoding, p.maxCategoricalLevels, p.ignoredColumns, p.ignoreConstCols,
                    p.scoreEachIteration, (p.checkpoint == null ? null : p.checkpoint.name), p.stoppingRounds, p.maxRuntimeSecs,
                    p.stoppingMetric, p.stoppingTolerance, p.gainsliftBins, p.customMetricFunc, p.customDistributionFunc,
                    p.exportCheckpointsDir, p.aucType);
        }

        /**
         * Train a PCA model.
         */
        public static Call<PCAV3> trainPca(final ModelBuilders z, final PCAParametersV3 p) {
            return z.trainPca(p.transform, p.pcaMethod, p.pcaImpl, p.k, p.maxIterations, p.seed, p.useAllFactorLevels, p.computeMetrics,
                    p.imputeMissing, (p.modelId == null ? null : p.modelId.name), (p.trainingFrame == null ? null : p.trainingFrame.name),
                    (p.validationFrame == null ? null : p.validationFrame.name), p.nfolds, p.keepCrossValidationModels,
                    p.keepCrossValidationPredictions, p.keepCrossValidationFoldAssignment, p.parallelizeCrossValidation, p.distribution,
                    p.tweediePower, p.quantileAlpha, p.huberAlpha, (p.responseColumn == null ? null : p.responseColumn.columnName),
                    (p.weightsColumn == null ? null : p.weightsColumn.columnName),
                    (p.offsetColumn == null ? null : p.offsetColumn.columnName), (p.foldColumn == null ? null : p.foldColumn.columnName),
                    p.foldAssignment, p.categoricalEncoding, p.maxCategoricalLevels, p.ignoredColumns, p.ignoreConstCols,
                    p.scoreEachIteration, (p.checkpoint == null ? null : p.checkpoint.name), p.stoppingRounds, p.maxRuntimeSecs,
                    p.stoppingMetric, p.stoppingTolerance, p.gainsliftBins, p.customMetricFunc, p.customDistributionFunc,
                    p.exportCheckpointsDir, p.aucType);
        }

        /**
         * Validate a set of PCA model builder parameters.
         */
        public static Call<PCAV3> validate_parametersPca(final ModelBuilders z, final PCAParametersV3 p) {
            return z.validate_parametersPca(p.transform, p.pcaMethod, p.pcaImpl, p.k, p.maxIterations, p.seed, p.useAllFactorLevels,
                    p.computeMetrics, p.imputeMissing, (p.modelId == null ? null : p.modelId.name),
                    (p.trainingFrame == null ? null : p.trainingFrame.name), (p.validationFrame == null ? null : p.validationFrame.name),
                    p.nfolds, p.keepCrossValidationModels, p.keepCrossValidationPredictions, p.keepCrossValidationFoldAssignment,
                    p.parallelizeCrossValidation, p.distribution, p.tweediePower, p.quantileAlpha, p.huberAlpha,
                    (p.responseColumn == null ? null : p.responseColumn.columnName),
                    (p.weightsColumn == null ? null : p.weightsColumn.columnName),
                    (p.offsetColumn == null ? null : p.offsetColumn.columnName), (p.foldColumn == null ? null : p.foldColumn.columnName),
                    p.foldAssignment, p.categoricalEncoding, p.maxCategoricalLevels, p.ignoredColumns, p.ignoreConstCols,
                    p.scoreEachIteration, (p.checkpoint == null ? null : p.checkpoint.name), p.stoppingRounds, p.maxRuntimeSecs,
                    p.stoppingMetric, p.stoppingTolerance, p.gainsliftBins, p.customMetricFunc, p.customDistributionFunc,
                    p.exportCheckpointsDir, p.aucType);
        }

        /**
         * Train a SVD model.
         */
        public static Call<SVDV99> trainSvd(final ModelBuilders z, final SVDParametersV99 p) {
            return z.trainSvd(p.transform, p.svdMethod, p.nv, p.maxIterations, p.seed, p.keepU, p.uName, p.useAllFactorLevels,
                    (p.modelId == null ? null : p.modelId.name), (p.trainingFrame == null ? null : p.trainingFrame.name),
                    (p.validationFrame == null ? null : p.validationFrame.name), p.nfolds, p.keepCrossValidationModels,
                    p.keepCrossValidationPredictions, p.keepCrossValidationFoldAssignment, p.parallelizeCrossValidation, p.distribution,
                    p.tweediePower, p.quantileAlpha, p.huberAlpha, (p.responseColumn == null ? null : p.responseColumn.columnName),
                    (p.weightsColumn == null ? null : p.weightsColumn.columnName),
                    (p.offsetColumn == null ? null : p.offsetColumn.columnName), (p.foldColumn == null ? null : p.foldColumn.columnName),
                    p.foldAssignment, p.categoricalEncoding, p.maxCategoricalLevels, p.ignoredColumns, p.ignoreConstCols,
                    p.scoreEachIteration, (p.checkpoint == null ? null : p.checkpoint.name), p.stoppingRounds, p.maxRuntimeSecs,
                    p.stoppingMetric, p.stoppingTolerance, p.gainsliftBins, p.customMetricFunc, p.customDistributionFunc,
                    p.exportCheckpointsDir, p.aucType);
        }

        /**
         * Validate a set of SVD model builder parameters.
         */
        public static Call<SVDV99> validate_parametersSvd(final ModelBuilders z, final SVDParametersV99 p) {
            return z.validate_parametersSvd(p.transform, p.svdMethod, p.nv, p.maxIterations, p.seed, p.keepU, p.uName, p.useAllFactorLevels,
                    (p.modelId == null ? null : p.modelId.name), (p.trainingFrame == null ? null : p.trainingFrame.name),
                    (p.validationFrame == null ? null : p.validationFrame.name), p.nfolds, p.keepCrossValidationModels,
                    p.keepCrossValidationPredictions, p.keepCrossValidationFoldAssignment, p.parallelizeCrossValidation, p.distribution,
                    p.tweediePower, p.quantileAlpha, p.huberAlpha, (p.responseColumn == null ? null : p.responseColumn.columnName),
                    (p.weightsColumn == null ? null : p.weightsColumn.columnName),
                    (p.offsetColumn == null ? null : p.offsetColumn.columnName), (p.foldColumn == null ? null : p.foldColumn.columnName),
                    p.foldAssignment, p.categoricalEncoding, p.maxCategoricalLevels, p.ignoredColumns, p.ignoreConstCols,
                    p.scoreEachIteration, (p.checkpoint == null ? null : p.checkpoint.name), p.stoppingRounds, p.maxRuntimeSecs,
                    p.stoppingMetric, p.stoppingTolerance, p.gainsliftBins, p.customMetricFunc, p.customDistributionFunc,
                    p.exportCheckpointsDir, p.aucType);
        }

        /**
         * Train a DRF model.
         */
        public static Call<DRFV3> trainDrf(final ModelBuilders z, final DRFParametersV3 p) {
            return z.trainDrf(p.mtries, p.binomialDoubleTrees, p.sampleRate, p.balanceClasses, p.classSamplingFactors,
                    p.maxAfterBalanceSize, p.maxConfusionMatrixSize, p.ntrees, p.maxDepth, p.minRows, p.nbins, p.nbinsTopLevel, p.nbinsCats,
                    p.r2Stopping, p.seed, p.buildTreeOneNode, p.sampleRatePerClass, p.colSampleRatePerTree, p.colSampleRateChangePerLevel,
                    p.scoreTreeInterval, p.minSplitImprovement, p.histogramType, p.calibrateModel,
                    (p.calibrationFrame == null ? null : p.calibrationFrame.name), p.checkConstantResponse,
                    (p.modelId == null ? null : p.modelId.name), (p.trainingFrame == null ? null : p.trainingFrame.name),
                    (p.validationFrame == null ? null : p.validationFrame.name), p.nfolds, p.keepCrossValidationModels,
                    p.keepCrossValidationPredictions, p.keepCrossValidationFoldAssignment, p.parallelizeCrossValidation, p.distribution,
                    p.tweediePower, p.quantileAlpha, p.huberAlpha, (p.responseColumn == null ? null : p.responseColumn.columnName),
                    (p.weightsColumn == null ? null : p.weightsColumn.columnName),
                    (p.offsetColumn == null ? null : p.offsetColumn.columnName), (p.foldColumn == null ? null : p.foldColumn.columnName),
                    p.foldAssignment, p.categoricalEncoding, p.maxCategoricalLevels, p.ignoredColumns, p.ignoreConstCols,
                    p.scoreEachIteration, (p.checkpoint == null ? null : p.checkpoint.name), p.stoppingRounds, p.maxRuntimeSecs,
                    p.stoppingMetric, p.stoppingTolerance, p.gainsliftBins, p.customMetricFunc, p.customDistributionFunc,
                    p.exportCheckpointsDir, p.aucType);
        }

        /**
         * Validate a set of DRF model builder parameters.
         */
        public static Call<DRFV3> validate_parametersDrf(final ModelBuilders z, final DRFParametersV3 p) {
            return z.validate_parametersDrf(p.mtries, p.binomialDoubleTrees, p.sampleRate, p.balanceClasses, p.classSamplingFactors,
                    p.maxAfterBalanceSize, p.maxConfusionMatrixSize, p.ntrees, p.maxDepth, p.minRows, p.nbins, p.nbinsTopLevel, p.nbinsCats,
                    p.r2Stopping, p.seed, p.buildTreeOneNode, p.sampleRatePerClass, p.colSampleRatePerTree, p.colSampleRateChangePerLevel,
                    p.scoreTreeInterval, p.minSplitImprovement, p.histogramType, p.calibrateModel,
                    (p.calibrationFrame == null ? null : p.calibrationFrame.name), p.checkConstantResponse,
                    (p.modelId == null ? null : p.modelId.name), (p.trainingFrame == null ? null : p.trainingFrame.name),
                    (p.validationFrame == null ? null : p.validationFrame.name), p.nfolds, p.keepCrossValidationModels,
                    p.keepCrossValidationPredictions, p.keepCrossValidationFoldAssignment, p.parallelizeCrossValidation, p.distribution,
                    p.tweediePower, p.quantileAlpha, p.huberAlpha, (p.responseColumn == null ? null : p.responseColumn.columnName),
                    (p.weightsColumn == null ? null : p.weightsColumn.columnName),
                    (p.offsetColumn == null ? null : p.offsetColumn.columnName), (p.foldColumn == null ? null : p.foldColumn.columnName),
                    p.foldAssignment, p.categoricalEncoding, p.maxCategoricalLevels, p.ignoredColumns, p.ignoreConstCols,
                    p.scoreEachIteration, (p.checkpoint == null ? null : p.checkpoint.name), p.stoppingRounds, p.maxRuntimeSecs,
                    p.stoppingMetric, p.stoppingTolerance, p.gainsliftBins, p.customMetricFunc, p.customDistributionFunc,
                    p.exportCheckpointsDir, p.aucType);
        }

        /**
         * Train a GBM model.
         */
        public static Call<GBMV3> trainGbm(final ModelBuilders z, final GBMParametersV3 p) {
            return z.trainGbm(p.learnRate, p.learnRateAnnealing, p.sampleRate, p.colSampleRate, p.monotoneConstraints, p.maxAbsLeafnodePred,
                    p.predNoiseBandwidth, p.interactionConstraints, p.balanceClasses, p.classSamplingFactors, p.maxAfterBalanceSize,
                    p.maxConfusionMatrixSize, p.ntrees, p.maxDepth, p.minRows, p.nbins, p.nbinsTopLevel, p.nbinsCats, p.r2Stopping, p.seed,
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
                    p.stoppingMetric, p.stoppingTolerance, p.gainsliftBins, p.customMetricFunc, p.customDistributionFunc,
                    p.exportCheckpointsDir, p.aucType);
        }

        /**
         * Validate a set of GBM model builder parameters.
         */
        public static Call<GBMV3> validate_parametersGbm(final ModelBuilders z, final GBMParametersV3 p) {
            return z.validate_parametersGbm(p.learnRate, p.learnRateAnnealing, p.sampleRate, p.colSampleRate, p.monotoneConstraints,
                    p.maxAbsLeafnodePred, p.predNoiseBandwidth, p.interactionConstraints, p.balanceClasses, p.classSamplingFactors,
                    p.maxAfterBalanceSize, p.maxConfusionMatrixSize, p.ntrees, p.maxDepth, p.minRows, p.nbins, p.nbinsTopLevel, p.nbinsCats,
                    p.r2Stopping, p.seed, p.buildTreeOneNode, p.sampleRatePerClass, p.colSampleRatePerTree, p.colSampleRateChangePerLevel,
                    p.scoreTreeInterval, p.minSplitImprovement, p.histogramType, p.calibrateModel,
                    (p.calibrationFrame == null ? null : p.calibrationFrame.name), p.checkConstantResponse,
                    (p.modelId == null ? null : p.modelId.name), (p.trainingFrame == null ? null : p.trainingFrame.name),
                    (p.validationFrame == null ? null : p.validationFrame.name), p.nfolds, p.keepCrossValidationModels,
                    p.keepCrossValidationPredictions, p.keepCrossValidationFoldAssignment, p.parallelizeCrossValidation, p.distribution,
                    p.tweediePower, p.quantileAlpha, p.huberAlpha, (p.responseColumn == null ? null : p.responseColumn.columnName),
                    (p.weightsColumn == null ? null : p.weightsColumn.columnName),
                    (p.offsetColumn == null ? null : p.offsetColumn.columnName), (p.foldColumn == null ? null : p.foldColumn.columnName),
                    p.foldAssignment, p.categoricalEncoding, p.maxCategoricalLevels, p.ignoredColumns, p.ignoreConstCols,
                    p.scoreEachIteration, (p.checkpoint == null ? null : p.checkpoint.name), p.stoppingRounds, p.maxRuntimeSecs,
                    p.stoppingMetric, p.stoppingTolerance, p.gainsliftBins, p.customMetricFunc, p.customDistributionFunc,
                    p.exportCheckpointsDir, p.aucType);
        }

        /**
         * Train a IsolationForest model.
         */
        public static Call<IsolationForestV3> trainIsolationforest(final ModelBuilders z, final IsolationForestParametersV3 p) {
            return z.trainIsolationforest(p.sampleSize, p.sampleRate, p.mtries, p.contamination,
                    (p.validationResponseColumn == null ? null : p.validationResponseColumn.columnName), p.balanceClasses,
                    p.classSamplingFactors, p.maxAfterBalanceSize, p.maxConfusionMatrixSize, p.ntrees, p.maxDepth, p.minRows, p.nbins,
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
                    p.stoppingMetric, p.stoppingTolerance, p.gainsliftBins, p.customMetricFunc, p.customDistributionFunc,
                    p.exportCheckpointsDir, p.aucType);
        }

        /**
         * Validate a set of IsolationForest model builder parameters.
         */
        public static Call<IsolationForestV3> validate_parametersIsolationforest(final ModelBuilders z,
                final IsolationForestParametersV3 p) {
            return z.validate_parametersIsolationforest(p.sampleSize, p.sampleRate, p.mtries, p.contamination,
                    (p.validationResponseColumn == null ? null : p.validationResponseColumn.columnName), p.balanceClasses,
                    p.classSamplingFactors, p.maxAfterBalanceSize, p.maxConfusionMatrixSize, p.ntrees, p.maxDepth, p.minRows, p.nbins,
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
                    p.stoppingMetric, p.stoppingTolerance, p.gainsliftBins, p.customMetricFunc, p.customDistributionFunc,
                    p.exportCheckpointsDir, p.aucType);
        }

        /**
         * Train a ExtendedIsolationForest model.
         */
        public static Call<ExtendedIsolationForestV3> trainExtendedisolationforest(final ModelBuilders z,
                final ExtendedIsolationForestParametersV3 p) {
            return z.trainExtendedisolationforest(p.ntrees, p.sampleSize, p.extensionLevel, p.seed,
                    (p.modelId == null ? null : p.modelId.name), (p.trainingFrame == null ? null : p.trainingFrame.name),
                    (p.validationFrame == null ? null : p.validationFrame.name), p.nfolds, p.keepCrossValidationModels,
                    p.keepCrossValidationPredictions, p.keepCrossValidationFoldAssignment, p.parallelizeCrossValidation, p.distribution,
                    p.tweediePower, p.quantileAlpha, p.huberAlpha, (p.responseColumn == null ? null : p.responseColumn.columnName),
                    (p.weightsColumn == null ? null : p.weightsColumn.columnName),
                    (p.offsetColumn == null ? null : p.offsetColumn.columnName), (p.foldColumn == null ? null : p.foldColumn.columnName),
                    p.foldAssignment, p.categoricalEncoding, p.maxCategoricalLevels, p.ignoredColumns, p.ignoreConstCols,
                    p.scoreEachIteration, (p.checkpoint == null ? null : p.checkpoint.name), p.stoppingRounds, p.maxRuntimeSecs,
                    p.stoppingMetric, p.stoppingTolerance, p.gainsliftBins, p.customMetricFunc, p.customDistributionFunc,
                    p.exportCheckpointsDir, p.aucType);
        }

        /**
         * Validate a set of ExtendedIsolationForest model builder parameters.
         */
        public static Call<ExtendedIsolationForestV3> validate_parametersExtendedisolationforest(final ModelBuilders z,
                final ExtendedIsolationForestParametersV3 p) {
            return z.validate_parametersExtendedisolationforest(p.ntrees, p.sampleSize, p.extensionLevel, p.seed,
                    (p.modelId == null ? null : p.modelId.name), (p.trainingFrame == null ? null : p.trainingFrame.name),
                    (p.validationFrame == null ? null : p.validationFrame.name), p.nfolds, p.keepCrossValidationModels,
                    p.keepCrossValidationPredictions, p.keepCrossValidationFoldAssignment, p.parallelizeCrossValidation, p.distribution,
                    p.tweediePower, p.quantileAlpha, p.huberAlpha, (p.responseColumn == null ? null : p.responseColumn.columnName),
                    (p.weightsColumn == null ? null : p.weightsColumn.columnName),
                    (p.offsetColumn == null ? null : p.offsetColumn.columnName), (p.foldColumn == null ? null : p.foldColumn.columnName),
                    p.foldAssignment, p.categoricalEncoding, p.maxCategoricalLevels, p.ignoredColumns, p.ignoreConstCols,
                    p.scoreEachIteration, (p.checkpoint == null ? null : p.checkpoint.name), p.stoppingRounds, p.maxRuntimeSecs,
                    p.stoppingMetric, p.stoppingTolerance, p.gainsliftBins, p.customMetricFunc, p.customDistributionFunc,
                    p.exportCheckpointsDir, p.aucType);
        }

        /**
         * Train a Aggregator model.
         */
        public static Call<AggregatorV99> trainAggregator(final ModelBuilders z, final AggregatorParametersV99 p) {
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
                    p.stoppingMetric, p.stoppingTolerance, p.gainsliftBins, p.customMetricFunc, p.customDistributionFunc,
                    p.exportCheckpointsDir, p.aucType);
        }

        /**
         * Validate a set of Aggregator model builder parameters.
         */
        public static Call<AggregatorV99> validate_parametersAggregator(final ModelBuilders z, final AggregatorParametersV99 p) {
            return z.validate_parametersAggregator(p.transform, p.pcaMethod, p.k, p.maxIterations, p.targetNumExemplars,
                    p.relTolNumExemplars, p.seed, p.useAllFactorLevels, p.saveMappingFrame, p.numIterationWithoutNewExemplar,
                    (p.modelId == null ? null : p.modelId.name), (p.trainingFrame == null ? null : p.trainingFrame.name),
                    (p.validationFrame == null ? null : p.validationFrame.name), p.nfolds, p.keepCrossValidationModels,
                    p.keepCrossValidationPredictions, p.keepCrossValidationFoldAssignment, p.parallelizeCrossValidation, p.distribution,
                    p.tweediePower, p.quantileAlpha, p.huberAlpha, (p.responseColumn == null ? null : p.responseColumn.columnName),
                    (p.weightsColumn == null ? null : p.weightsColumn.columnName),
                    (p.offsetColumn == null ? null : p.offsetColumn.columnName), (p.foldColumn == null ? null : p.foldColumn.columnName),
                    p.foldAssignment, p.categoricalEncoding, p.maxCategoricalLevels, p.ignoredColumns, p.ignoreConstCols,
                    p.scoreEachIteration, (p.checkpoint == null ? null : p.checkpoint.name), p.stoppingRounds, p.maxRuntimeSecs,
                    p.stoppingMetric, p.stoppingTolerance, p.gainsliftBins, p.customMetricFunc, p.customDistributionFunc,
                    p.exportCheckpointsDir, p.aucType);
        }

        /**
         * Train a Word2Vec model.
         */
        public static Call<Word2VecV3> trainWord2vec(final ModelBuilders z, final Word2VecParametersV3 p) {
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
                    p.stoppingMetric, p.stoppingTolerance, p.gainsliftBins, p.customMetricFunc, p.customDistributionFunc,
                    p.exportCheckpointsDir, p.aucType);
        }

        /**
         * Validate a set of Word2Vec model builder parameters.
         */
        public static Call<Word2VecV3> validate_parametersWord2vec(final ModelBuilders z, final Word2VecParametersV3 p) {
            return z.validate_parametersWord2vec(p.vecSize, p.windowSize, p.sentSampleRate, p.normModel, p.epochs, p.minWordFreq,
                    p.initLearningRate, p.wordModel, (p.preTrained == null ? null : p.preTrained.name),
                    (p.modelId == null ? null : p.modelId.name), (p.trainingFrame == null ? null : p.trainingFrame.name),
                    (p.validationFrame == null ? null : p.validationFrame.name), p.nfolds, p.keepCrossValidationModels,
                    p.keepCrossValidationPredictions, p.keepCrossValidationFoldAssignment, p.parallelizeCrossValidation, p.distribution,
                    p.tweediePower, p.quantileAlpha, p.huberAlpha, (p.responseColumn == null ? null : p.responseColumn.columnName),
                    (p.weightsColumn == null ? null : p.weightsColumn.columnName),
                    (p.offsetColumn == null ? null : p.offsetColumn.columnName), (p.foldColumn == null ? null : p.foldColumn.columnName),
                    p.foldAssignment, p.categoricalEncoding, p.maxCategoricalLevels, p.ignoredColumns, p.ignoreConstCols,
                    p.scoreEachIteration, (p.checkpoint == null ? null : p.checkpoint.name), p.stoppingRounds, p.maxRuntimeSecs,
                    p.stoppingMetric, p.stoppingTolerance, p.gainsliftBins, p.customMetricFunc, p.customDistributionFunc,
                    p.exportCheckpointsDir, p.aucType);
        }

        /**
         * Train a StackedEnsemble model.
         */
        public static Call<StackedEnsembleV99> trainStackedensemble(final ModelBuilders z, final StackedEnsembleParametersV99 p) {
            return z.trainStackedensemble((p.baseModels == null ? null : keyArrayToStringArray(p.baseModels)), p.metalearnerAlgorithm,
                    p.metalearnerNfolds, p.metalearnerFoldAssignment,
                    (p.metalearnerFoldColumn == null ? null : p.metalearnerFoldColumn.columnName), p.metalearnerTransform,
                    p.keepLeveloneFrame, p.metalearnerParams, (p.blendingFrame == null ? null : p.blendingFrame.name), p.seed,
                    p.scoreTrainingSamples, (p.modelId == null ? null : p.modelId.name),
                    (p.trainingFrame == null ? null : p.trainingFrame.name), (p.validationFrame == null ? null : p.validationFrame.name),
                    p.nfolds, p.keepCrossValidationModels, p.keepCrossValidationPredictions, p.keepCrossValidationFoldAssignment,
                    p.parallelizeCrossValidation, p.distribution, p.tweediePower, p.quantileAlpha, p.huberAlpha,
                    (p.responseColumn == null ? null : p.responseColumn.columnName),
                    (p.weightsColumn == null ? null : p.weightsColumn.columnName),
                    (p.offsetColumn == null ? null : p.offsetColumn.columnName), (p.foldColumn == null ? null : p.foldColumn.columnName),
                    p.foldAssignment, p.categoricalEncoding, p.maxCategoricalLevels, p.ignoredColumns, p.ignoreConstCols,
                    p.scoreEachIteration, (p.checkpoint == null ? null : p.checkpoint.name), p.stoppingRounds, p.maxRuntimeSecs,
                    p.stoppingMetric, p.stoppingTolerance, p.gainsliftBins, p.customMetricFunc, p.customDistributionFunc,
                    p.exportCheckpointsDir, p.aucType);
        }

        /**
         * Validate a set of StackedEnsemble model builder parameters.
         */
        public static Call<StackedEnsembleV99> validate_parametersStackedensemble(final ModelBuilders z,
                final StackedEnsembleParametersV99 p) {
            return z.validate_parametersStackedensemble((p.baseModels == null ? null : keyArrayToStringArray(p.baseModels)),
                    p.metalearnerAlgorithm, p.metalearnerNfolds, p.metalearnerFoldAssignment,
                    (p.metalearnerFoldColumn == null ? null : p.metalearnerFoldColumn.columnName), p.metalearnerTransform,
                    p.keepLeveloneFrame, p.metalearnerParams, (p.blendingFrame == null ? null : p.blendingFrame.name), p.seed,
                    p.scoreTrainingSamples, (p.modelId == null ? null : p.modelId.name),
                    (p.trainingFrame == null ? null : p.trainingFrame.name), (p.validationFrame == null ? null : p.validationFrame.name),
                    p.nfolds, p.keepCrossValidationModels, p.keepCrossValidationPredictions, p.keepCrossValidationFoldAssignment,
                    p.parallelizeCrossValidation, p.distribution, p.tweediePower, p.quantileAlpha, p.huberAlpha,
                    (p.responseColumn == null ? null : p.responseColumn.columnName),
                    (p.weightsColumn == null ? null : p.weightsColumn.columnName),
                    (p.offsetColumn == null ? null : p.offsetColumn.columnName), (p.foldColumn == null ? null : p.foldColumn.columnName),
                    p.foldAssignment, p.categoricalEncoding, p.maxCategoricalLevels, p.ignoredColumns, p.ignoreConstCols,
                    p.scoreEachIteration, (p.checkpoint == null ? null : p.checkpoint.name), p.stoppingRounds, p.maxRuntimeSecs,
                    p.stoppingMetric, p.stoppingTolerance, p.gainsliftBins, p.customMetricFunc, p.customDistributionFunc,
                    p.exportCheckpointsDir, p.aucType);
        }

        /**
         * Train a CoxPH model.
         */
        public static Call<CoxPHV3> trainCoxph(final ModelBuilders z, final CoxPHParametersV3 p) {
            return z.trainCoxph((p.startColumn == null ? null : p.startColumn.columnName),
                    (p.stopColumn == null ? null : p.stopColumn.columnName), p.stratifyBy, p.ties, p.init, p.lreMin, p.maxIterations,
                    p.interactionsOnly, p.interactions, p.interactionPairs, p.useAllFactorLevels, p.singleNodeMode,
                    (p.modelId == null ? null : p.modelId.name), (p.trainingFrame == null ? null : p.trainingFrame.name),
                    (p.validationFrame == null ? null : p.validationFrame.name), p.nfolds, p.keepCrossValidationModels,
                    p.keepCrossValidationPredictions, p.keepCrossValidationFoldAssignment, p.parallelizeCrossValidation, p.distribution,
                    p.tweediePower, p.quantileAlpha, p.huberAlpha, (p.responseColumn == null ? null : p.responseColumn.columnName),
                    (p.weightsColumn == null ? null : p.weightsColumn.columnName),
                    (p.offsetColumn == null ? null : p.offsetColumn.columnName), (p.foldColumn == null ? null : p.foldColumn.columnName),
                    p.foldAssignment, p.categoricalEncoding, p.maxCategoricalLevels, p.ignoredColumns, p.ignoreConstCols,
                    p.scoreEachIteration, (p.checkpoint == null ? null : p.checkpoint.name), p.stoppingRounds, p.maxRuntimeSecs,
                    p.stoppingMetric, p.stoppingTolerance, p.gainsliftBins, p.customMetricFunc, p.customDistributionFunc,
                    p.exportCheckpointsDir, p.aucType);
        }

        /**
         * Validate a set of CoxPH model builder parameters.
         */
        public static Call<CoxPHV3> validate_parametersCoxph(final ModelBuilders z, final CoxPHParametersV3 p) {
            return z.validate_parametersCoxph((p.startColumn == null ? null : p.startColumn.columnName),
                    (p.stopColumn == null ? null : p.stopColumn.columnName), p.stratifyBy, p.ties, p.init, p.lreMin, p.maxIterations,
                    p.interactionsOnly, p.interactions, p.interactionPairs, p.useAllFactorLevels, p.singleNodeMode,
                    (p.modelId == null ? null : p.modelId.name), (p.trainingFrame == null ? null : p.trainingFrame.name),
                    (p.validationFrame == null ? null : p.validationFrame.name), p.nfolds, p.keepCrossValidationModels,
                    p.keepCrossValidationPredictions, p.keepCrossValidationFoldAssignment, p.parallelizeCrossValidation, p.distribution,
                    p.tweediePower, p.quantileAlpha, p.huberAlpha, (p.responseColumn == null ? null : p.responseColumn.columnName),
                    (p.weightsColumn == null ? null : p.weightsColumn.columnName),
                    (p.offsetColumn == null ? null : p.offsetColumn.columnName), (p.foldColumn == null ? null : p.foldColumn.columnName),
                    p.foldAssignment, p.categoricalEncoding, p.maxCategoricalLevels, p.ignoredColumns, p.ignoreConstCols,
                    p.scoreEachIteration, (p.checkpoint == null ? null : p.checkpoint.name), p.stoppingRounds, p.maxRuntimeSecs,
                    p.stoppingMetric, p.stoppingTolerance, p.gainsliftBins, p.customMetricFunc, p.customDistributionFunc,
                    p.exportCheckpointsDir, p.aucType);
        }

        /**
         * Train a Generic model.
         */
        public static Call<GenericV3> trainGeneric(final ModelBuilders z, final GenericParametersV3 p) {
            return z.trainGeneric(p.path, (p.modelKey == null ? null : p.modelKey.name), (p.modelId == null ? null : p.modelId.name),
                    (p.trainingFrame == null ? null : p.trainingFrame.name), (p.validationFrame == null ? null : p.validationFrame.name),
                    p.nfolds, p.keepCrossValidationModels, p.keepCrossValidationPredictions, p.keepCrossValidationFoldAssignment,
                    p.parallelizeCrossValidation, p.distribution, p.tweediePower, p.quantileAlpha, p.huberAlpha,
                    (p.responseColumn == null ? null : p.responseColumn.columnName),
                    (p.weightsColumn == null ? null : p.weightsColumn.columnName),
                    (p.offsetColumn == null ? null : p.offsetColumn.columnName), (p.foldColumn == null ? null : p.foldColumn.columnName),
                    p.foldAssignment, p.categoricalEncoding, p.maxCategoricalLevels, p.ignoredColumns, p.ignoreConstCols,
                    p.scoreEachIteration, (p.checkpoint == null ? null : p.checkpoint.name), p.stoppingRounds, p.maxRuntimeSecs,
                    p.stoppingMetric, p.stoppingTolerance, p.gainsliftBins, p.customMetricFunc, p.customDistributionFunc,
                    p.exportCheckpointsDir, p.aucType);
        }

        /**
         * Validate a set of Generic model builder parameters.
         */
        public static Call<GenericV3> validate_parametersGeneric(final ModelBuilders z, final GenericParametersV3 p) {
            return z.validate_parametersGeneric(p.path, (p.modelKey == null ? null : p.modelKey.name),
                    (p.modelId == null ? null : p.modelId.name), (p.trainingFrame == null ? null : p.trainingFrame.name),
                    (p.validationFrame == null ? null : p.validationFrame.name), p.nfolds, p.keepCrossValidationModels,
                    p.keepCrossValidationPredictions, p.keepCrossValidationFoldAssignment, p.parallelizeCrossValidation, p.distribution,
                    p.tweediePower, p.quantileAlpha, p.huberAlpha, (p.responseColumn == null ? null : p.responseColumn.columnName),
                    (p.weightsColumn == null ? null : p.weightsColumn.columnName),
                    (p.offsetColumn == null ? null : p.offsetColumn.columnName), (p.foldColumn == null ? null : p.foldColumn.columnName),
                    p.foldAssignment, p.categoricalEncoding, p.maxCategoricalLevels, p.ignoredColumns, p.ignoreConstCols,
                    p.scoreEachIteration, (p.checkpoint == null ? null : p.checkpoint.name), p.stoppingRounds, p.maxRuntimeSecs,
                    p.stoppingMetric, p.stoppingTolerance, p.gainsliftBins, p.customMetricFunc, p.customDistributionFunc,
                    p.exportCheckpointsDir, p.aucType);
        }

        /**
         * Train a GAM model.
         */
        public static Call<GAMV3> trainGam(final ModelBuilders z, final GAMParametersV3 p) {
            return z.trainGam(p.seed, p.family, p.tweedieVariancePower, p.tweedieLinkPower, p.theta, p.solver, p.alpha, p.lambda,
                    p.startval, p.lambdaSearch, p.earlyStopping, p.nlambdas, p.standardize, p.missingValuesHandling,
                    (p.plugValues == null ? null : p.plugValues.name), p.nonNegative, p.maxIterations, p.betaEpsilon, p.objectiveEpsilon,
                    p.gradientEpsilon, p.objReg, p.link, p.intercept, p.prior, p.coldStart, p.lambdaMinRatio,
                    (p.betaConstraints == null ? null : p.betaConstraints.name), p.maxActivePredictors, p.interactions, p.interactionPairs,
                    p.balanceClasses, p.classSamplingFactors, p.maxAfterBalanceSize, p.maxConfusionMatrixSize, p.computePValues,
                    p.removeCollinearColumns, p.numKnots, p.splineOrders, p.gamColumns, p.scale, p.bs, p.keepGamCols,
                    p.standardizeTpGamCols, p.scaleTpPenaltyMat, p.knotIds, (p.modelId == null ? null : p.modelId.name),
                    (p.trainingFrame == null ? null : p.trainingFrame.name), (p.validationFrame == null ? null : p.validationFrame.name),
                    p.nfolds, p.keepCrossValidationModels, p.keepCrossValidationPredictions, p.keepCrossValidationFoldAssignment,
                    p.parallelizeCrossValidation, p.distribution, p.tweediePower, p.quantileAlpha, p.huberAlpha,
                    (p.responseColumn == null ? null : p.responseColumn.columnName),
                    (p.weightsColumn == null ? null : p.weightsColumn.columnName),
                    (p.offsetColumn == null ? null : p.offsetColumn.columnName), (p.foldColumn == null ? null : p.foldColumn.columnName),
                    p.foldAssignment, p.categoricalEncoding, p.maxCategoricalLevels, p.ignoredColumns, p.ignoreConstCols,
                    p.scoreEachIteration, (p.checkpoint == null ? null : p.checkpoint.name), p.stoppingRounds, p.maxRuntimeSecs,
                    p.stoppingMetric, p.stoppingTolerance, p.gainsliftBins, p.customMetricFunc, p.customDistributionFunc,
                    p.exportCheckpointsDir, p.aucType);
        }

        /**
         * Validate a set of GAM model builder parameters.
         */
        public static Call<GAMV3> validate_parametersGam(final ModelBuilders z, final GAMParametersV3 p) {
            return z.validate_parametersGam(p.seed, p.family, p.tweedieVariancePower, p.tweedieLinkPower, p.theta, p.solver, p.alpha,
                    p.lambda, p.startval, p.lambdaSearch, p.earlyStopping, p.nlambdas, p.standardize, p.missingValuesHandling,
                    (p.plugValues == null ? null : p.plugValues.name), p.nonNegative, p.maxIterations, p.betaEpsilon, p.objectiveEpsilon,
                    p.gradientEpsilon, p.objReg, p.link, p.intercept, p.prior, p.coldStart, p.lambdaMinRatio,
                    (p.betaConstraints == null ? null : p.betaConstraints.name), p.maxActivePredictors, p.interactions, p.interactionPairs,
                    p.balanceClasses, p.classSamplingFactors, p.maxAfterBalanceSize, p.maxConfusionMatrixSize, p.computePValues,
                    p.removeCollinearColumns, p.numKnots, p.splineOrders, p.gamColumns, p.scale, p.bs, p.keepGamCols,
                    p.standardizeTpGamCols, p.scaleTpPenaltyMat, p.knotIds, (p.modelId == null ? null : p.modelId.name),
                    (p.trainingFrame == null ? null : p.trainingFrame.name), (p.validationFrame == null ? null : p.validationFrame.name),
                    p.nfolds, p.keepCrossValidationModels, p.keepCrossValidationPredictions, p.keepCrossValidationFoldAssignment,
                    p.parallelizeCrossValidation, p.distribution, p.tweediePower, p.quantileAlpha, p.huberAlpha,
                    (p.responseColumn == null ? null : p.responseColumn.columnName),
                    (p.weightsColumn == null ? null : p.weightsColumn.columnName),
                    (p.offsetColumn == null ? null : p.offsetColumn.columnName), (p.foldColumn == null ? null : p.foldColumn.columnName),
                    p.foldAssignment, p.categoricalEncoding, p.maxCategoricalLevels, p.ignoredColumns, p.ignoreConstCols,
                    p.scoreEachIteration, (p.checkpoint == null ? null : p.checkpoint.name), p.stoppingRounds, p.maxRuntimeSecs,
                    p.stoppingMetric, p.stoppingTolerance, p.gainsliftBins, p.customMetricFunc, p.customDistributionFunc,
                    p.exportCheckpointsDir, p.aucType);
        }

        /**
         * Train a ANOVAGLM model.
         */
        public static Call<ANOVAGLMV3> trainAnovaglm(final ModelBuilders z, final ANOVAGLMParametersV3 p) {
            return z.trainAnovaglm(p.seed, p.standardize, p.family, p.tweedieVariancePower, p.tweedieLinkPower, p.theta, p.alpha, p.lambda,
                    p.lambdaSearch, p.solver, p.missingValuesHandling, (p.plugValues == null ? null : p.plugValues.name), p.nonNegative,
                    p.computePValues, p.maxIterations, p.link, p.prior, p.balanceClasses, p.classSamplingFactors, p.maxAfterBalanceSize,
                    p.highestInteractionTerm, p.type, p.earlyStopping, p.saveTransformedFramekeys, p.nparallelism,
                    (p.modelId == null ? null : p.modelId.name), (p.trainingFrame == null ? null : p.trainingFrame.name),
                    (p.validationFrame == null ? null : p.validationFrame.name), p.nfolds, p.keepCrossValidationModels,
                    p.keepCrossValidationPredictions, p.keepCrossValidationFoldAssignment, p.parallelizeCrossValidation, p.distribution,
                    p.tweediePower, p.quantileAlpha, p.huberAlpha, (p.responseColumn == null ? null : p.responseColumn.columnName),
                    (p.weightsColumn == null ? null : p.weightsColumn.columnName),
                    (p.offsetColumn == null ? null : p.offsetColumn.columnName), (p.foldColumn == null ? null : p.foldColumn.columnName),
                    p.foldAssignment, p.categoricalEncoding, p.maxCategoricalLevels, p.ignoredColumns, p.ignoreConstCols,
                    p.scoreEachIteration, (p.checkpoint == null ? null : p.checkpoint.name), p.stoppingRounds, p.maxRuntimeSecs,
                    p.stoppingMetric, p.stoppingTolerance, p.gainsliftBins, p.customMetricFunc, p.customDistributionFunc,
                    p.exportCheckpointsDir, p.aucType);
        }

        /**
         * Validate a set of ANOVAGLM model builder parameters.
         */
        public static Call<ANOVAGLMV3> validate_parametersAnovaglm(final ModelBuilders z, final ANOVAGLMParametersV3 p) {
            return z.validate_parametersAnovaglm(p.seed, p.standardize, p.family, p.tweedieVariancePower, p.tweedieLinkPower, p.theta,
                    p.alpha, p.lambda, p.lambdaSearch, p.solver, p.missingValuesHandling, (p.plugValues == null ? null : p.plugValues.name),
                    p.nonNegative, p.computePValues, p.maxIterations, p.link, p.prior, p.balanceClasses, p.classSamplingFactors,
                    p.maxAfterBalanceSize, p.highestInteractionTerm, p.type, p.earlyStopping, p.saveTransformedFramekeys, p.nparallelism,
                    (p.modelId == null ? null : p.modelId.name), (p.trainingFrame == null ? null : p.trainingFrame.name),
                    (p.validationFrame == null ? null : p.validationFrame.name), p.nfolds, p.keepCrossValidationModels,
                    p.keepCrossValidationPredictions, p.keepCrossValidationFoldAssignment, p.parallelizeCrossValidation, p.distribution,
                    p.tweediePower, p.quantileAlpha, p.huberAlpha, (p.responseColumn == null ? null : p.responseColumn.columnName),
                    (p.weightsColumn == null ? null : p.weightsColumn.columnName),
                    (p.offsetColumn == null ? null : p.offsetColumn.columnName), (p.foldColumn == null ? null : p.foldColumn.columnName),
                    p.foldAssignment, p.categoricalEncoding, p.maxCategoricalLevels, p.ignoredColumns, p.ignoreConstCols,
                    p.scoreEachIteration, (p.checkpoint == null ? null : p.checkpoint.name), p.stoppingRounds, p.maxRuntimeSecs,
                    p.stoppingMetric, p.stoppingTolerance, p.gainsliftBins, p.customMetricFunc, p.customDistributionFunc,
                    p.exportCheckpointsDir, p.aucType);
        }

        /**
         * Train a PSVM model.
         */
        public static Call<PSVMV3> trainPsvm(final ModelBuilders z, final PSVMParametersV3 p) {
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
                    p.stoppingMetric, p.stoppingTolerance, p.gainsliftBins, p.customMetricFunc, p.customDistributionFunc,
                    p.exportCheckpointsDir, p.aucType);
        }

        /**
         * Validate a set of PSVM model builder parameters.
         */
        public static Call<PSVMV3> validate_parametersPsvm(final ModelBuilders z, final PSVMParametersV3 p) {
            return z.validate_parametersPsvm(p.hyperParam, p.kernelType, p.gamma, p.rankRatio, p.positiveWeight, p.negativeWeight,
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
                    p.stoppingMetric, p.stoppingTolerance, p.gainsliftBins, p.customMetricFunc, p.customDistributionFunc,
                    p.exportCheckpointsDir, p.aucType);
        }

        /**
         * Train a RuleFit model.
         */
        public static Call<RuleFitV3> trainRulefit(final ModelBuilders z, final RuleFitParametersV3 p) {
            return z.trainRulefit(p.seed, p.algorithm, p.minRuleLength, p.maxRuleLength, p.maxNumRules, p.modelType, p.ruleGenerationNtrees,
                    p.removeDuplicates, p.lambda, (p.modelId == null ? null : p.modelId.name),
                    (p.trainingFrame == null ? null : p.trainingFrame.name), (p.validationFrame == null ? null : p.validationFrame.name),
                    p.nfolds, p.keepCrossValidationModels, p.keepCrossValidationPredictions, p.keepCrossValidationFoldAssignment,
                    p.parallelizeCrossValidation, p.distribution, p.tweediePower, p.quantileAlpha, p.huberAlpha,
                    (p.responseColumn == null ? null : p.responseColumn.columnName),
                    (p.weightsColumn == null ? null : p.weightsColumn.columnName),
                    (p.offsetColumn == null ? null : p.offsetColumn.columnName), (p.foldColumn == null ? null : p.foldColumn.columnName),
                    p.foldAssignment, p.categoricalEncoding, p.maxCategoricalLevels, p.ignoredColumns, p.ignoreConstCols,
                    p.scoreEachIteration, (p.checkpoint == null ? null : p.checkpoint.name), p.stoppingRounds, p.maxRuntimeSecs,
                    p.stoppingMetric, p.stoppingTolerance, p.gainsliftBins, p.customMetricFunc, p.customDistributionFunc,
                    p.exportCheckpointsDir, p.aucType);
        }

        /**
         * Validate a set of RuleFit model builder parameters.
         */
        public static Call<RuleFitV3> validate_parametersRulefit(final ModelBuilders z, final RuleFitParametersV3 p) {
            return z.validate_parametersRulefit(p.seed, p.algorithm, p.minRuleLength, p.maxRuleLength, p.maxNumRules, p.modelType,
                    p.ruleGenerationNtrees, p.removeDuplicates, p.lambda, (p.modelId == null ? null : p.modelId.name),
                    (p.trainingFrame == null ? null : p.trainingFrame.name), (p.validationFrame == null ? null : p.validationFrame.name),
                    p.nfolds, p.keepCrossValidationModels, p.keepCrossValidationPredictions, p.keepCrossValidationFoldAssignment,
                    p.parallelizeCrossValidation, p.distribution, p.tweediePower, p.quantileAlpha, p.huberAlpha,
                    (p.responseColumn == null ? null : p.responseColumn.columnName),
                    (p.weightsColumn == null ? null : p.weightsColumn.columnName),
                    (p.offsetColumn == null ? null : p.offsetColumn.columnName), (p.foldColumn == null ? null : p.foldColumn.columnName),
                    p.foldAssignment, p.categoricalEncoding, p.maxCategoricalLevels, p.ignoredColumns, p.ignoreConstCols,
                    p.scoreEachIteration, (p.checkpoint == null ? null : p.checkpoint.name), p.stoppingRounds, p.maxRuntimeSecs,
                    p.stoppingMetric, p.stoppingTolerance, p.gainsliftBins, p.customMetricFunc, p.customDistributionFunc,
                    p.exportCheckpointsDir, p.aucType);
        }

        /**
         * Train a UpliftDRF model.
         */
        public static Call<UpliftDRFV3> trainUpliftdrf(final ModelBuilders z, final UpliftDRFParametersV3 p) {
            return z.trainUpliftdrf(p.mtries, p.sampleRate, p.treatmentColumn, p.upliftMetric, p.auucType, p.auucNbins, p.balanceClasses,
                    p.classSamplingFactors, p.maxAfterBalanceSize, p.maxConfusionMatrixSize, p.ntrees, p.maxDepth, p.minRows, p.nbins,
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
                    p.stoppingMetric, p.stoppingTolerance, p.gainsliftBins, p.customMetricFunc, p.customDistributionFunc,
                    p.exportCheckpointsDir, p.aucType);
        }

        /**
         * Validate a set of UpliftDRF model builder parameters.
         */
        public static Call<UpliftDRFV3> validate_parametersUpliftdrf(final ModelBuilders z, final UpliftDRFParametersV3 p) {
            return z.validate_parametersUpliftdrf(p.mtries, p.sampleRate, p.treatmentColumn, p.upliftMetric, p.auucType, p.auucNbins,
                    p.balanceClasses, p.classSamplingFactors, p.maxAfterBalanceSize, p.maxConfusionMatrixSize, p.ntrees, p.maxDepth,
                    p.minRows, p.nbins, p.nbinsTopLevel, p.nbinsCats, p.r2Stopping, p.seed, p.buildTreeOneNode, p.sampleRatePerClass,
                    p.colSampleRatePerTree, p.colSampleRateChangePerLevel, p.scoreTreeInterval, p.minSplitImprovement, p.histogramType,
                    p.calibrateModel, (p.calibrationFrame == null ? null : p.calibrationFrame.name), p.checkConstantResponse,
                    (p.modelId == null ? null : p.modelId.name), (p.trainingFrame == null ? null : p.trainingFrame.name),
                    (p.validationFrame == null ? null : p.validationFrame.name), p.nfolds, p.keepCrossValidationModels,
                    p.keepCrossValidationPredictions, p.keepCrossValidationFoldAssignment, p.parallelizeCrossValidation, p.distribution,
                    p.tweediePower, p.quantileAlpha, p.huberAlpha, (p.responseColumn == null ? null : p.responseColumn.columnName),
                    (p.weightsColumn == null ? null : p.weightsColumn.columnName),
                    (p.offsetColumn == null ? null : p.offsetColumn.columnName), (p.foldColumn == null ? null : p.foldColumn.columnName),
                    p.foldAssignment, p.categoricalEncoding, p.maxCategoricalLevels, p.ignoredColumns, p.ignoreConstCols,
                    p.scoreEachIteration, (p.checkpoint == null ? null : p.checkpoint.name), p.stoppingRounds, p.maxRuntimeSecs,
                    p.stoppingMetric, p.stoppingTolerance, p.gainsliftBins, p.customMetricFunc, p.customDistributionFunc,
                    p.exportCheckpointsDir, p.aucType);
        }

        /**
         * Train a ModelSelection model.
         */
        public static Call<ModelSelectionV3> trainModelselection(final ModelBuilders z, final ModelSelectionParametersV3 p) {
            return z.trainModelselection(p.seed, p.family, p.tweedieVariancePower, p.tweedieLinkPower, p.theta, p.solver, p.alpha, p.lambda,
                    p.lambdaSearch, p.earlyStopping, p.nlambdas, p.scoreIterationInterval, p.standardize, p.coldStart,
                    p.missingValuesHandling, (p.plugValues == null ? null : p.plugValues.name), p.nonNegative, p.maxIterations,
                    p.betaEpsilon, p.objectiveEpsilon, p.gradientEpsilon, p.objReg, p.link, p.startval, p.calcLike, p.mode, p.intercept,
                    p.prior, p.lambdaMinRatio, (p.betaConstraints == null ? null : p.betaConstraints.name), p.maxActivePredictors,
                    p.balanceClasses, p.classSamplingFactors, p.maxAfterBalanceSize, p.maxConfusionMatrixSize, p.computePValues,
                    p.removeCollinearColumns, p.maxPredictorNumber, p.minPredictorNumber, p.nparallelism, p.pValuesThreshold,
                    (p.modelId == null ? null : p.modelId.name), (p.trainingFrame == null ? null : p.trainingFrame.name),
                    (p.validationFrame == null ? null : p.validationFrame.name), p.nfolds, p.keepCrossValidationModels,
                    p.keepCrossValidationPredictions, p.keepCrossValidationFoldAssignment, p.parallelizeCrossValidation, p.distribution,
                    p.tweediePower, p.quantileAlpha, p.huberAlpha, (p.responseColumn == null ? null : p.responseColumn.columnName),
                    (p.weightsColumn == null ? null : p.weightsColumn.columnName),
                    (p.offsetColumn == null ? null : p.offsetColumn.columnName), (p.foldColumn == null ? null : p.foldColumn.columnName),
                    p.foldAssignment, p.categoricalEncoding, p.maxCategoricalLevels, p.ignoredColumns, p.ignoreConstCols,
                    p.scoreEachIteration, (p.checkpoint == null ? null : p.checkpoint.name), p.stoppingRounds, p.maxRuntimeSecs,
                    p.stoppingMetric, p.stoppingTolerance, p.gainsliftBins, p.customMetricFunc, p.customDistributionFunc,
                    p.exportCheckpointsDir, p.aucType);
        }

        /**
         * Validate a set of ModelSelection model builder parameters.
         */
        public static Call<ModelSelectionV3> validate_parametersModelselection(final ModelBuilders z, final ModelSelectionParametersV3 p) {
            return z.validate_parametersModelselection(p.seed, p.family, p.tweedieVariancePower, p.tweedieLinkPower, p.theta, p.solver,
                    p.alpha, p.lambda, p.lambdaSearch, p.earlyStopping, p.nlambdas, p.scoreIterationInterval, p.standardize, p.coldStart,
                    p.missingValuesHandling, (p.plugValues == null ? null : p.plugValues.name), p.nonNegative, p.maxIterations,
                    p.betaEpsilon, p.objectiveEpsilon, p.gradientEpsilon, p.objReg, p.link, p.startval, p.calcLike, p.mode, p.intercept,
                    p.prior, p.lambdaMinRatio, (p.betaConstraints == null ? null : p.betaConstraints.name), p.maxActivePredictors,
                    p.balanceClasses, p.classSamplingFactors, p.maxAfterBalanceSize, p.maxConfusionMatrixSize, p.computePValues,
                    p.removeCollinearColumns, p.maxPredictorNumber, p.minPredictorNumber, p.nparallelism, p.pValuesThreshold,
                    (p.modelId == null ? null : p.modelId.name), (p.trainingFrame == null ? null : p.trainingFrame.name),
                    (p.validationFrame == null ? null : p.validationFrame.name), p.nfolds, p.keepCrossValidationModels,
                    p.keepCrossValidationPredictions, p.keepCrossValidationFoldAssignment, p.parallelizeCrossValidation, p.distribution,
                    p.tweediePower, p.quantileAlpha, p.huberAlpha, (p.responseColumn == null ? null : p.responseColumn.columnName),
                    (p.weightsColumn == null ? null : p.weightsColumn.columnName),
                    (p.offsetColumn == null ? null : p.offsetColumn.columnName), (p.foldColumn == null ? null : p.foldColumn.columnName),
                    p.foldAssignment, p.categoricalEncoding, p.maxCategoricalLevels, p.ignoredColumns, p.ignoreConstCols,
                    p.scoreEachIteration, (p.checkpoint == null ? null : p.checkpoint.name), p.stoppingRounds, p.maxRuntimeSecs,
                    p.stoppingMetric, p.stoppingTolerance, p.gainsliftBins, p.customMetricFunc, p.customDistributionFunc,
                    p.exportCheckpointsDir, p.aucType);
        }

        /**
         * Return an array of Strings for an array of keys.
         */
        public static String[] keyArrayToStringArray(final KeyV3[] keys) {
            if (keys == null) {
                return null;
            }
            final String[] ids = new String[keys.length];
            int i = 0;
            for (final KeyV3 key : keys) {
                ids[i] = key.name;
                i++;
            }
            return ids;
        }
    }

}
