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

public class AutoMLStoppingCriteriaV99 extends SchemaV3 {

    /**
     * Seed for random number generator; set to a value other than -1 for reproducibility.
     */
    public long seed;

    /**
     * Maximum number of models to build (optional).
     */
    @SerializedName("max_models")
    public int maxModels;

    /**
     * This argument specifies the maximum time that the AutoML process will run for, prior to training the final
     * Stacked Ensemble models. If neither max_runtime_secs nor max_models are specified by the user, then
     * max_runtime_secs defaults to 3600 seconds (1 hour).
     */
    @SerializedName("max_runtime_secs")
    public double maxRuntimeSecs;

    /**
     * Maximum time to spend on each individual model (optional).
     */
    @SerializedName("max_runtime_secs_per_model")
    public double maxRuntimeSecsPerModel;

    /**
     * Early stopping based on convergence of stopping_metric. Stop if simple moving average of length k of the
     * stopping_metric does not improve for k:=stopping_rounds scoring events (0 to disable)
     */
    @SerializedName("stopping_rounds")
    public int stoppingRounds;

    /**
     * Metric to use for early stopping (AUTO: logloss for classification, deviance for regression)
     */
    @SerializedName("stopping_metric")
    public ScoreKeeperStoppingMetric stoppingMetric;

    /**
     * Relative tolerance for metric-based stopping criterion (stop if relative improvement is not at least this much)
     */
    @SerializedName("stopping_tolerance")
    public double stoppingTolerance;

    /**
     * Public constructor
     */
    public AutoMLStoppingCriteriaV99() {
        seed = -1L;
        maxModels = 0;
        maxRuntimeSecs = 3600.0;
        maxRuntimeSecsPerModel = 0.0;
        stoppingRounds = 3;
        stoppingMetric = ScoreKeeperStoppingMetric.AUTO;
        stoppingTolerance = 0.001;
    }

    /**
     * Return the contents of this object as a JSON String.
     */
    @Override
    public String toString() {
        return new GsonBuilder().serializeSpecialFloatingPointValues().create().toJson(this);
    }

}
