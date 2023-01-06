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

public class GridExportV3 extends SchemaV3 {

    /**
     * ID of the Grid to load from the directory
     */
    @SerializedName("grid_id")
    public String gridId;

    /**
     * Path to the directory with saved Grid search
     */
    @SerializedName("grid_directory")
    public String gridDirectory;

    /**
     * True if objects referenced by params should also be saved.
     */
    @SerializedName("save_params_references")
    public boolean saveParamsReferences;

    /**
     * Flag indicating whether the exported model artifacts should also include CV Holdout Frame predictions
     */
    @SerializedName("export_cross_validation_predictions")
    public boolean exportCrossValidationPredictions;

    /**
     * Public constructor
     */
    public GridExportV3() {
        gridId = "";
        gridDirectory = "";
        saveParamsReferences = false;
        exportCrossValidationPredictions = false;
    }

    /**
     * Return the contents of this object as a JSON String.
     */
    @Override
    public String toString() {
        return new GsonBuilder().serializeSpecialFloatingPointValues().create().toJson(this);
    }

}
