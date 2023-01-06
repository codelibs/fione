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

public class ModelsV3 extends RequestSchemaV3 {

    /**
     * Name of Model of interest
     */
    @SerializedName("model_id")
    public ModelKeyV3 modelId;

    /**
     * Return potentially abridged model suitable for viewing in a browser
     */
    public boolean preview;

    /**
     * Find and return compatible frames?
     */
    @SerializedName("find_compatible_frames")
    public boolean findCompatibleFrames;

    /**
     * Models
     */
    public ModelSchemaBaseV3[] models;

    /**
     * Compatible frames
     */
    @SerializedName("compatible_frames")
    public FrameV3[] compatibleFrames;

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
    public ModelsV3() {
        preview = false;
        findCompatibleFrames = false;
        exportCrossValidationPredictions = false;
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
