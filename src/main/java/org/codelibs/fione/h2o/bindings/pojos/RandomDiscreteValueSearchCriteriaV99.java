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
package org.codelibs.fione.h2o.bindings.pojos;

import com.google.gson.GsonBuilder;
import com.google.gson.annotations.SerializedName;

public class RandomDiscreteValueSearchCriteriaV99 extends HyperSpaceSearchCriteriaV99 {

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
     * Maximum time to spend building models (optional).
     */
    @SerializedName("max_runtime_secs")
    public double maxRuntimeSecs;

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

    /*------------------------------------------------------------------------------------------------------------------
    //                                                  INHERITED
    //------------------------------------------------------------------------------------------------------------------

    // Hyperparameter space search strategy.
    public GridHyperSpaceSearchCriteriaStrategy strategy;

    */

    /**
     * Public constructor
     */
    public RandomDiscreteValueSearchCriteriaV99() {
        seed = -1L;
        maxModels = 0;
        maxRuntimeSecs = 0.0;
        stoppingRounds = 0;
        stoppingMetric = ScoreKeeperStoppingMetric.AUTO;
        stoppingTolerance = 0.001;
        strategy = GridHyperSpaceSearchCriteriaStrategy.RandomDiscrete;
    }

    /**
     * Return the contents of this object as a JSON String.
     */
    @Override
    public String toString() {
        return new GsonBuilder().serializeSpecialFloatingPointValues().create().toJson(this);
    }

}
