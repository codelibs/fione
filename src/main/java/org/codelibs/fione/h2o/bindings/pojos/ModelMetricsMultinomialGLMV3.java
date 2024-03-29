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

public class ModelMetricsMultinomialGLMV3 extends ModelMetricsMultinomialV3 {

    /**
     * residual deviance
     */
    @SerializedName("residual_deviance")
    public double residualDeviance;

    /**
     * null deviance
     */
    @SerializedName("null_deviance")
    public double nullDeviance;

    /**
     * AIC
     */
    @SerializedName("AIC")
    public double aic;

    /**
     * null DOF
     */
    @SerializedName("null_degrees_of_freedom")
    public long nullDegreesOfFreedom;

    /**
     * residual DOF
     */
    @SerializedName("residual_degrees_of_freedom")
    public long residualDegreesOfFreedom;

    /*------------------------------------------------------------------------------------------------------------------
    //                                                  INHERITED
    //------------------------------------------------------------------------------------------------------------------

    // The R^2 for this scoring run.
    public double r2;

    // The hit ratio table for this scoring run.
    public TwoDimTableV3 hitRatioTable;

    // The ConfusionMatrix object for this scoring run.
    public ConfusionMatrixV3 cm;

    // The logarithmic loss for this scoring run.
    public double logloss;

    // The mean misclassification error per class.
    public double meanPerClassError;

    // The average AUC for this scoring run.
    public double auc;

    // The average precision-recall AUC for this scoring run.
    public double prAuc;

    // The multinomial AUC values.
    public TwoDimTableV3 multinomialAucTable;

    // The multinomial PR AUC values.
    public TwoDimTableV3 multinomialAucprTable;

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
    public ModelMetricsMultinomialGLMV3() {
        residualDeviance = 0.0;
        nullDeviance = 0.0;
        aic = 0.0;
        nullDegreesOfFreedom = 0L;
        residualDegreesOfFreedom = 0L;
        r2 = 0.0;
        logloss = 0.0;
        meanPerClassError = 0.0;
        auc = 0.0;
        prAuc = 0.0;
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
