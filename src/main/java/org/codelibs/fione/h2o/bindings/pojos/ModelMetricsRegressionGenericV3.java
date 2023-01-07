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

import com.google.gson.GsonBuilder;
import com.google.gson.annotations.SerializedName;

public class ModelMetricsRegressionGenericV3 extends ModelMetricsBaseV3 {

    /**
     * The mean residual deviance for this scoring run.
     */
    @SerializedName("mean_residual_deviance")
    public double meanResidualDeviance;

    /**
     * The mean absolute error for this scoring run.
     */
    public double mae;

    /**
     * The root mean squared log error for this scoring run.
     */
    public double rmsle;

    /*------------------------------------------------------------------------------------------------------------------
    //                                                  INHERITED
    //------------------------------------------------------------------------------------------------------------------

    // The model used for this scoring run.
    public ModelKeyV3 model;

    // The checksum for the model used for this scoring run.
    public long modelChecksum;

    // The frame used for this scoring run.
    public FrameKeyV3 frame;

    // The checksum for the frame used for this scoring run.
    public long frameChecksum;

    // Optional description for this scoring run (to note out-of-bag, sampled data, etc.)
    public String description;

    // The category (e.g., Clustering) for the model used for this scoring run.
    public ModelCategory modelCategory;

    // The time in mS since the epoch for the start of this scoring run.
    public long scoringTime;

    // Predictions Frame.
    public FrameV3 predictions;

    // The Mean Squared Error of the prediction for this scoring run.
    public double mse;

    // The Root Mean Squared Error of the prediction for this scoring run.
    public double rmse;

    // Number of observations.
    public long nobs;

    // Name of custom metric
    public String customMetricName;

    // Value of custom metric
    public double customMetricValue;

    */

    /**
     * Public constructor
     */
    public ModelMetricsRegressionGenericV3() {
        meanResidualDeviance = 0.0;
        mae = 0.0;
        rmsle = 0.0;
        modelChecksum = 0L;
        frameChecksum = 0L;
        description = "";
        scoringTime = 0L;
        mse = 0.0;
        rmse = 0.0;
        nobs = 0L;
        customMetricName = "";
        customMetricValue = 0.0;
    }

    /**
     * Return the contents of this object as a JSON String.
     */
    @Override
    public String toString() {
        return new GsonBuilder().serializeSpecialFloatingPointValues().create().toJson(this);
    }

}
