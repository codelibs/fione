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

import com.google.gson.Gson;
import com.google.gson.annotations.SerializedName;

public class ModelExportV3 extends RequestSchemaV3 {

    /**
     * Name of Model of interest
     */
    @SerializedName("model_id")
    public ModelKeyV3 modelId;

    /**
     * Destination file (hdfs, s3, local)
     */
    public String dir;

    /**
     * Overwrite destination file in case it exists or throw exception if set to false.
     */
    public boolean force;

    /**
     * Flag indicating whether the exported model artifact should also include CV Holdout Frame predictions
     */
    @SerializedName("export_cross_validation_predictions")
    public boolean exportCrossValidationPredictions;

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
    public ModelExportV3() {
        dir = "";
        force = true;
        exportCrossValidationPredictions = false;
        _excludeFields = "";
    }

    /**
     * Return the contents of this object as a JSON String.
     */
    @Override
    public String toString() {
        return new Gson().toJson(this);
    }

}
