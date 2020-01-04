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

public class AutoMLBuildControlV99 extends SchemaV3 {

    /**
     * Optional project name used to group models from multiple AutoML runs into a single Leaderboard; derived from the
     * training data name if not specified.
     */
    @SerializedName("project_name")
    public String projectName;

    /**
     * Model performance based stopping criteria for the AutoML run.
     */
    @SerializedName("stopping_criteria")
    public AutoMLStoppingCriteriaV99 stoppingCriteria;

    /**
     * Number of folds for k-fold cross-validation (defaults to 5, must be &gt;=2 or use 0 to disable). Disabling prevents
     * Stacked Ensembles from being built.
     */
    public int nfolds;

    /**
     * Balance training data class counts via over/under-sampling (for imbalanced data).
     */
    @SerializedName("balance_classes")
    public boolean balanceClasses;

    /**
     * Desired over/under-sampling ratios per class (in lexicographic order). If not specified, sampling factors will be
     * automatically computed to obtain class balance during training. Requires balance_classes.
     */
    @SerializedName("class_sampling_factors")
    public float[] classSamplingFactors;

    /**
     * Maximum relative size of the training data after balancing class counts (defaults to 5.0 and can be less than
     * 1.0). Requires balance_classes.
     */
    @SerializedName("max_after_balance_size")
    public float maxAfterBalanceSize;

    /**
     * Whether to keep the predictions of the cross-validation predictions. This needs to be set to TRUE if running the
     * same AutoML object for repeated runs because CV predictions are required to build additional Stacked Ensemble
     * models in AutoML.
     */
    @SerializedName("keep_cross_validation_predictions")
    public boolean keepCrossValidationPredictions;

    /**
     * Whether to keep the cross-validated models. Keeping cross-validation models may consume significantly more memory
     * in the H2O cluster.
     */
    @SerializedName("keep_cross_validation_models")
    public boolean keepCrossValidationModels;

    /**
     * Whether to keep cross-validation assignments.
     */
    @SerializedName("keep_cross_validation_fold_assignment")
    public boolean keepCrossValidationFoldAssignment;

    /**
     * Path to a directory where every generated model will be stored.
     */
    @SerializedName("export_checkpoints_dir")
    public String exportCheckpointsDir;

    /**
     * Public constructor
     */
    public AutoMLBuildControlV99() {
        projectName = "";
        stoppingCriteria = new AutoMLStoppingCriteriaV99();
        nfolds = 5;
        balanceClasses = false;
        maxAfterBalanceSize = 5.0f;
        keepCrossValidationPredictions = false;
        keepCrossValidationModels = false;
        keepCrossValidationFoldAssignment = false;
        exportCheckpointsDir = "";
    }

    /**
     * Return the contents of this object as a JSON String.
     */
    @Override
    public String toString() {
        return new GsonBuilder().serializeSpecialFloatingPointValues().create().toJson(this);
    }

}
