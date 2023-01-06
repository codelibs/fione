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

public class ModelMetricsListSchemaV3 extends RequestSchemaV3 {

    /**
     * Key of Model of interest (optional)
     */
    public ModelKeyV3 model;

    /**
     * Key of Frame of interest (optional)
     */
    public FrameKeyV3 frame;

    /**
     * Key of predictions frame, if predictions are requested (optional)
     */
    @SerializedName("predictions_frame")
    public FrameKeyV3 predictionsFrame;

    /**
     * Key for the frame containing per-observation deviances (optional)
     */
    @SerializedName("deviances_frame")
    public FrameKeyV3 deviancesFrame;

    /**
     * Compute reconstruction error (optional, only for Deep Learning AutoEncoder models)
     */
    @SerializedName("reconstruction_error")
    public boolean reconstructionError;

    /**
     * Compute reconstruction error per feature (optional, only for Deep Learning AutoEncoder models)
     */
    @SerializedName("reconstruction_error_per_feature")
    public boolean reconstructionErrorPerFeature;

    /**
     * Extract Deep Features for given hidden layer (optional, only for Deep Learning models)
     */
    @SerializedName("deep_features_hidden_layer")
    public int deepFeaturesHiddenLayer;

    /**
     * Extract Deep Features for given hidden layer by name (optional, only for Deep Water models)
     */
    @SerializedName("deep_features_hidden_layer_name")
    public String deepFeaturesHiddenLayerName;

    /**
     * Reconstruct original training frame (optional, only for GLRM models)
     */
    @SerializedName("reconstruct_train")
    public boolean reconstructTrain;

    /**
     * Project GLRM archetypes back into original feature space (optional, only for GLRM models)
     */
    @SerializedName("project_archetypes")
    public boolean projectArchetypes;

    /**
     * Reverse transformation applied during training to model output (optional, only for GLRM models)
     */
    @SerializedName("reverse_transform")
    public boolean reverseTransform;

    /**
     * Return the leaf node assignment (optional, only for DRF/GBM models)
     */
    @SerializedName("leaf_node_assignment")
    public boolean leafNodeAssignment;

    /**
     * Type of the leaf node assignment (optional, only for DRF/GBM models)
     */
    @SerializedName("leaf_node_assignment_type")
    public ModelLeafNodeAssignmentLeafNodeAssignmentType leafNodeAssignmentType;

    /**
     * Predict the class probabilities at each stage (optional, only for GBM models)
     */
    @SerializedName("predict_staged_proba")
    public boolean predictStagedProba;

    /**
     * Predict the feature contributions - Shapley values (optional, only for DRF, GBM and XGBoost models)
     */
    @SerializedName("predict_contributions")
    public boolean predictContributions;

    /**
     * Specify how to output feature contributions in XGBoost - XGBoost by default outputs contributions for 1-hot
     * encoded features, specifying a Compact output format will produce a per-feature contribution
     */
    @SerializedName("predict_contributions_output_format")
    public ModelContributionsContributionsOutputFormat predictContributionsOutputFormat;

    /**
     * Only for predict_contributions function - sort Shapley values and return top_n highest (optional)
     */
    @SerializedName("top_n")
    public int topN;

    /**
     * Only for predict_contributions function - sort Shapley values and return bottom_n lowest (optional)
     */
    @SerializedName("bottom_n")
    public int bottomN;

    /**
     * Only for predict_contributions function - sort absolute Shapley values (optional)
     */
    @SerializedName("compare_abs")
    public boolean compareAbs;

    /**
     * Retrieve the feature frequencies on paths in trees in tree-based models (optional, only for GBM, DRF and
     * Isolation Forest)
     */
    @SerializedName("feature_frequencies")
    public boolean featureFrequencies;

    /**
     * Retrieve all members for a given exemplar (optional, only for Aggregator models)
     */
    @SerializedName("exemplar_index")
    public int exemplarIndex;

    /**
     * Compute the deviances per row (optional, only for classification or regression models)
     */
    public boolean deviances;

    /**
     * Reference to custom evaluation function, format: `language:keyName=funcName`
     */
    @SerializedName("custom_metric_func")
    public String customMetricFunc;

    /**
     * Set default multinomial AUC type. Must be one of: "AUTO", "NONE", "MACRO_OVR", "WEIGHTED_OVR", "MACRO_OVO",
     * "WEIGHTED_OVO". Default is "NONE" (optional, only for multinomial classification).
     */
    @SerializedName("auc_type")
    public String aucType;

    /**
     * Set default AUUC type for uplift binomial classification. Must be one of: "AUTO", "qini", "lift", "gain". Default
     * is "AUTO" (optional, only for uplift binomial classification).
     */
    @SerializedName("auuc_type")
    public String auucType;

    /**
     * Set number of bins to calculate AUUC. Must be -1 or higher than 0. Default is -1 which means 1000 (optional, only
     * for uplift binomial classification).
     */
    @SerializedName("auuc_nbins")
    public int auucNbins;

    /**
     * ModelMetrics
     */
    @SerializedName("model_metrics")
    public ModelMetricsBaseV3[] modelMetrics;

    /*------------------------------------------------------------------------------------------------------------------
    //                                                  INHERITED
    //------------------------------------------------------------------------------------------------------------------

    // Comma-separated list of JSON field paths to exclude from the result, used like:
    // "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
    public String _excludeFields;

    */

    /**
     * Public constructor
     */
    public ModelMetricsListSchemaV3() {
        reconstructionError = false;
        reconstructionErrorPerFeature = false;
        deepFeaturesHiddenLayer = -1;
        deepFeaturesHiddenLayerName = "";
        reconstructTrain = false;
        projectArchetypes = false;
        reverseTransform = false;
        leafNodeAssignment = false;
        predictStagedProba = false;
        predictContributions = false;
        topN = 0;
        bottomN = 0;
        compareAbs = false;
        featureFrequencies = false;
        exemplarIndex = -1;
        deviances = false;
        customMetricFunc = "";
        aucType = "";
        auucType = "";
        auucNbins = 0;
        modelMetrics = new ModelMetricsBaseV3[] {};
        _excludeFields = "";
    }

    /**
     * Return the contents of this object as a JSON String.
     */
    @Override
    public String toString() {
        return new GsonBuilder().serializeSpecialFloatingPointValues().create().toJson(this);
    }

}
