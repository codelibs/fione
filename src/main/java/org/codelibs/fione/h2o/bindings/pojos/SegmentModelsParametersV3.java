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

public class SegmentModelsParametersV3 extends SchemaV3 {

    /**
     * Uniquely identifies the collection of the segment models
     */
    @SerializedName("segment_models_id")
    public SegmentModelsKeyV3 segmentModelsId;

    /**
     * Enumeration of all segments for which to build models for
     */
    public FrameKeyV3 segments;

    /**
     * List of columns to segment-by, models will be built for all segments in the data
     */
    @SerializedName("segment_columns")
    public String[] segmentColumns;

    /**
     * Level of parallelism of bulk model building, it is the maximum number of models each H2O node will be building in
     * parallel
     */
    public int parallelism;

    /**
     * Public constructor
     */
    public SegmentModelsParametersV3() {
        parallelism = 1;
    }

    /**
     * Return the contents of this object as a JSON String.
     */
    @Override
    public String toString() {
        return new GsonBuilder().serializeSpecialFloatingPointValues().create().toJson(this);
    }

}
