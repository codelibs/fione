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

public class ModelMetricsMakerSchemaV3 extends SchemaV3 {

    /**
     * Predictions Frame.
     */
    @SerializedName("predictions_frame")
    public String predictionsFrame;

    /**
     * Actuals Frame.
     */
    @SerializedName("actuals_frame")
    public String actualsFrame;

    /**
     * Weights Frame.
     */
    @SerializedName("weights_frame")
    public String weightsFrame;

    /**
     * Treatment Frame.
     */
    @SerializedName("treatment_frame")
    public String treatmentFrame;

    /**
     * Domain (for classification).
     */
    public String[] domain;

    /**
     * Distribution (for regression).
     */
    public GenmodelutilsDistributionFamily distribution;

    /**
     * Default AUC type (for multinomial classification).
     */
    @SerializedName("auc_type")
    public MultinomialAucType aucType;

    /**
     * Default AUUC type (for uplift binomial classification).
     */
    @SerializedName("auuc_type")
    public AUUCType auucType;

    /**
     * Number of bins to calculate AUUC (for uplift binomial classification).
     */
    @SerializedName("auuc_nbins")
    public int auucNbins;

    /**
     * Model Metrics.
     */
    @SerializedName("model_metrics")
    public ModelMetricsBaseV3 modelMetrics;

    /**
     * Public constructor
     */
    public ModelMetricsMakerSchemaV3() {
        predictionsFrame = "";
        actualsFrame = "";
        weightsFrame = "";
        treatmentFrame = "";
        auucNbins = 0;
    }

    /**
     * Return the contents of this object as a JSON String.
     */
    @Override
    public String toString() {
        return new GsonBuilder().serializeSpecialFloatingPointValues().create().toJson(this);
    }

}
