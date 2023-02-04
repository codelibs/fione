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

public class AutoMLInputV99 extends SchemaV3 {

    /**
     * ID of the training data frame.
     */
    @SerializedName("training_frame")
    public FrameKeyV3 trainingFrame;

    /**
     * Response column
     */
    @SerializedName("response_column")
    public ColSpecifierV3 responseColumn;

    /**
     * ID of the validation data frame (used for early stopping in grid searches and for early stopping of the AutoML
     * process itself).
     */
    @SerializedName("validation_frame")
    public FrameKeyV3 validationFrame;

    /**
     * ID of the H2OFrame used to train the the metalearning algorithm in Stacked Ensembles (instead of relying on
     * cross-validated predicted values). When provided, it is also recommended to disable cross validation by setting
     * `nfolds=0` and to provide a leaderboard frame for scoring purposes.
     */
    @SerializedName("blending_frame")
    public FrameKeyV3 blendingFrame;

    /**
     * ID of the leaderboard data frame (used to score models and rank them on the AutoML Leaderboard).
     */
    @SerializedName("leaderboard_frame")
    public FrameKeyV3 leaderboardFrame;

    /**
     * Fold column (contains fold IDs) in the training frame. These assignments are used to create the folds for cross-
     * validation of the models.
     */
    @SerializedName("fold_column")
    public ColSpecifierV3 foldColumn;

    /**
     * Weights column in the training frame, which specifies the row weights used in model training.
     */
    @SerializedName("weights_column")
    public ColSpecifierV3 weightsColumn;

    /**
     * Names of columns to ignore in the training frame when building models.
     */
    @SerializedName("ignored_columns")
    public String[] ignoredColumns;

    /**
     * Metric used to sort leaderboard
     */
    @SerializedName("sort_metric")
    public Automlapischemas3AutoMLBuildSpecAutoMLMetricProvider sortMetric;

    /**
     * Public constructor
     */
    public AutoMLInputV99() {
        sortMetric = Automlapischemas3AutoMLBuildSpecAutoMLMetricProvider.AUTO;
    }

    /**
     * Return the contents of this object as a JSON String.
     */
    @Override
    public String toString() {
        return new GsonBuilder().serializeSpecialFloatingPointValues().create().toJson(this);
    }

}
