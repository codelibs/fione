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

import org.codelibs.fione.h2o.bindings.pojos.JobV3;
import org.codelibs.fione.h2o.bindings.pojos.ModelContributionsContributionsOutputFormat;
import org.codelibs.fione.h2o.bindings.pojos.ModelLeafNodeAssignmentLeafNodeAssignmentType;
import org.codelibs.fione.h2o.bindings.pojos.ModelMetricsListSchemaV3;

import retrofit2.Call;
import retrofit2.http.Field;
import retrofit2.http.FormUrlEncoded;
import retrofit2.http.POST;
import retrofit2.http.Path;

public interface Predictions {

    /**
     * Score (generate predictions) for the specified Frame with the specified Model.  Both the Frame of predictions and
     * the metrics will be returned.
     *   @param model Key of Model of interest (optional)
     *   @param frame Key of Frame of interest (optional)
     *   @param predictions_frame Key of predictions frame, if predictions are requested (optional)
     *   @param deviances_frame Key for the frame containing per-observation deviances (optional)
     *   @param reconstruction_error Compute reconstruction error (optional, only for Deep Learning AutoEncoder models)
     *   @param reconstruction_error_per_feature Compute reconstruction error per feature (optional, only for Deep
     *                                           Learning AutoEncoder models)
     *   @param deep_features_hidden_layer Extract Deep Features for given hidden layer (optional, only for Deep Learning
     *                                     models)
     *   @param deep_features_hidden_layer_name Extract Deep Features for given hidden layer by name (optional, only for
     *                                          Deep Water models)
     *   @param reconstruct_train Reconstruct original training frame (optional, only for GLRM models)
     *   @param project_archetypes Project GLRM archetypes back into original feature space (optional, only for GLRM
     *                             models)
     *   @param reverse_transform Reverse transformation applied during training to model output (optional, only for GLRM
     *                            models)
     *   @param leaf_node_assignment Return the leaf node assignment (optional, only for DRF/GBM models)
     *   @param leaf_node_assignment_type Type of the leaf node assignment (optional, only for DRF/GBM models)
     *   @param predict_staged_proba Predict the class probabilities at each stage (optional, only for GBM models)
     *   @param predict_contributions Predict the feature contributions - Shapley values (optional, only for DRF, GBM and
     *                                XGBoost models)
     *   @param predict_contributions_output_format Specify how to output feature contributions in XGBoost - XGBoost by
     *                                              default outputs contributions for 1-hot encoded features, specifying a
     *                                              Compact output format will produce a per-feature contribution
     *   @param top_n Only for predict_contributions function - sort Shapley values and return top_n highest (optional)
     *   @param bottom_n Only for predict_contributions function - sort Shapley values and return bottom_n lowest
     *                   (optional)
     *   @param compare_abs Only for predict_contributions function - sort absolute Shapley values (optional)
     *   @param feature_frequencies Retrieve the feature frequencies on paths in trees in tree-based models (optional,
     *                              only for GBM, DRF and Isolation Forest)
     *   @param exemplar_index Retrieve all members for a given exemplar (optional, only for Aggregator models)
     *   @param deviances Compute the deviances per row (optional, only for classification or regression models)
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param auc_type Set default multinomial AUC type. Must be one of: "AUTO", "NONE", "MACRO_OVR", "WEIGHTED_OVR",
     *                   "MACRO_OVO", "WEIGHTED_OVO". Default is "NONE" (optional, only for multinomial classification).
     *   @param auuc_type Set default AUUC type for uplift binomial classification. Must be one of: "AUTO", "qini",
     *                    "lift", "gain". Default is "AUTO" (optional, only for uplift binomial classification).
     *   @param auuc_nbins Set number of bins to calculate AUUC. Must be -1 or higher than 0. Default is -1 which means
     *                     1000 (optional, only for uplift binomial classification).
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @FormUrlEncoded
    @POST("/3/Predictions/models/{model}/frames/{frame}")
    Call<ModelMetricsListSchemaV3> predict(@Path("model") String model, @Path("frame") String frame,
            @Field("predictions_frame") String predictions_frame, @Field("deviances_frame") String deviances_frame,
            @Field("reconstruction_error") boolean reconstruction_error,
            @Field("reconstruction_error_per_feature") boolean reconstruction_error_per_feature,
            @Field("deep_features_hidden_layer") int deep_features_hidden_layer,
            @Field("deep_features_hidden_layer_name") String deep_features_hidden_layer_name,
            @Field("reconstruct_train") boolean reconstruct_train, @Field("project_archetypes") boolean project_archetypes,
            @Field("reverse_transform") boolean reverse_transform, @Field("leaf_node_assignment") boolean leaf_node_assignment,
            @Field("leaf_node_assignment_type") ModelLeafNodeAssignmentLeafNodeAssignmentType leaf_node_assignment_type,
            @Field("predict_staged_proba") boolean predict_staged_proba, @Field("predict_contributions") boolean predict_contributions,
            @Field("predict_contributions_output_format") ModelContributionsContributionsOutputFormat predict_contributions_output_format,
            @Field("top_n") int top_n, @Field("bottom_n") int bottom_n, @Field("compare_abs") boolean compare_abs,
            @Field("feature_frequencies") boolean feature_frequencies, @Field("exemplar_index") int exemplar_index,
            @Field("deviances") boolean deviances, @Field("custom_metric_func") String custom_metric_func,
            @Field("auc_type") String auc_type, @Field("auuc_type") String auuc_type, @Field("auuc_nbins") int auuc_nbins,
            @Field("_exclude_fields") String _exclude_fields);

    @FormUrlEncoded
    @POST("/3/Predictions/models/{model}/frames/{frame}")
    Call<ModelMetricsListSchemaV3> predict(@Path("model") String model, @Path("frame") String frame,
            @Field("_exclude_fields") String _exclude_fields);

    /**
     * Score (generate predictions) for the specified Frame with the specified Model.  Both the Frame of predictions and
     * the metrics will be returned.
     *   @param model Key of Model of interest (optional)
     *   @param frame Key of Frame of interest (optional)
     *   @param predictions_frame Key of predictions frame, if predictions are requested (optional)
     *   @param deviances_frame Key for the frame containing per-observation deviances (optional)
     *   @param reconstruction_error Compute reconstruction error (optional, only for Deep Learning AutoEncoder models)
     *   @param reconstruction_error_per_feature Compute reconstruction error per feature (optional, only for Deep
     *                                           Learning AutoEncoder models)
     *   @param deep_features_hidden_layer Extract Deep Features for given hidden layer (optional, only for Deep Learning
     *                                     models)
     *   @param deep_features_hidden_layer_name Extract Deep Features for given hidden layer by name (optional, only for
     *                                          Deep Water models)
     *   @param reconstruct_train Reconstruct original training frame (optional, only for GLRM models)
     *   @param project_archetypes Project GLRM archetypes back into original feature space (optional, only for GLRM
     *                             models)
     *   @param reverse_transform Reverse transformation applied during training to model output (optional, only for GLRM
     *                            models)
     *   @param leaf_node_assignment Return the leaf node assignment (optional, only for DRF/GBM models)
     *   @param leaf_node_assignment_type Type of the leaf node assignment (optional, only for DRF/GBM models)
     *   @param predict_staged_proba Predict the class probabilities at each stage (optional, only for GBM models)
     *   @param predict_contributions Predict the feature contributions - Shapley values (optional, only for DRF, GBM and
     *                                XGBoost models)
     *   @param predict_contributions_output_format Specify how to output feature contributions in XGBoost - XGBoost by
     *                                              default outputs contributions for 1-hot encoded features, specifying a
     *                                              Compact output format will produce a per-feature contribution
     *   @param top_n Only for predict_contributions function - sort Shapley values and return top_n highest (optional)
     *   @param bottom_n Only for predict_contributions function - sort Shapley values and return bottom_n lowest
     *                   (optional)
     *   @param compare_abs Only for predict_contributions function - sort absolute Shapley values (optional)
     *   @param feature_frequencies Retrieve the feature frequencies on paths in trees in tree-based models (optional,
     *                              only for GBM, DRF and Isolation Forest)
     *   @param exemplar_index Retrieve all members for a given exemplar (optional, only for Aggregator models)
     *   @param deviances Compute the deviances per row (optional, only for classification or regression models)
     *   @param custom_metric_func Reference to custom evaluation function, format: `language:keyName=funcName`
     *   @param auc_type Set default multinomial AUC type. Must be one of: "AUTO", "NONE", "MACRO_OVR", "WEIGHTED_OVR",
     *                   "MACRO_OVO", "WEIGHTED_OVO". Default is "NONE" (optional, only for multinomial classification).
     *   @param auuc_type Set default AUUC type for uplift binomial classification. Must be one of: "AUTO", "qini",
     *                    "lift", "gain". Default is "AUTO" (optional, only for uplift binomial classification).
     *   @param auuc_nbins Set number of bins to calculate AUUC. Must be -1 or higher than 0. Default is -1 which means
     *                     1000 (optional, only for uplift binomial classification).
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @FormUrlEncoded
    @POST("/4/Predictions/models/{model}/frames/{frame}")
    Call<JobV3> predictAsync(@Path("model") String model, @Path("frame") String frame, @Field("predictions_frame") String predictions_frame,
            @Field("deviances_frame") String deviances_frame, @Field("reconstruction_error") boolean reconstruction_error,
            @Field("reconstruction_error_per_feature") boolean reconstruction_error_per_feature,
            @Field("deep_features_hidden_layer") int deep_features_hidden_layer,
            @Field("deep_features_hidden_layer_name") String deep_features_hidden_layer_name,
            @Field("reconstruct_train") boolean reconstruct_train, @Field("project_archetypes") boolean project_archetypes,
            @Field("reverse_transform") boolean reverse_transform, @Field("leaf_node_assignment") boolean leaf_node_assignment,
            @Field("leaf_node_assignment_type") ModelLeafNodeAssignmentLeafNodeAssignmentType leaf_node_assignment_type,
            @Field("predict_staged_proba") boolean predict_staged_proba, @Field("predict_contributions") boolean predict_contributions,
            @Field("predict_contributions_output_format") ModelContributionsContributionsOutputFormat predict_contributions_output_format,
            @Field("top_n") int top_n, @Field("bottom_n") int bottom_n, @Field("compare_abs") boolean compare_abs,
            @Field("feature_frequencies") boolean feature_frequencies, @Field("exemplar_index") int exemplar_index,
            @Field("deviances") boolean deviances, @Field("custom_metric_func") String custom_metric_func,
            @Field("auc_type") String auc_type, @Field("auuc_type") String auuc_type, @Field("auuc_nbins") int auuc_nbins,
            @Field("_exclude_fields") String _exclude_fields);

    @FormUrlEncoded
    @POST("/4/Predictions/models/{model}/frames/{frame}")
    Call<JobV3> predictAsync(@Path("model") String model, @Path("frame") String frame);

}
