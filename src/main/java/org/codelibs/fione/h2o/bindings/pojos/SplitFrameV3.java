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

public class SplitFrameV3 extends SchemaV3 {

    /**
     * Job Key
     */
    public JobKeyV3 key;

    /**
     * Dataset
     */
    public FrameKeyV3 dataset;

    /**
     * Split ratios - resulting number of split is ratios.length+1
     */
    public double[] ratios;

    /**
     * Destination keys for each output frame split.
     */
    @SerializedName("destination_frames")
    public FrameKeyV3[] destinationFrames;

    /**
     * Public constructor
     */
    public SplitFrameV3() {
    }

    /**
     * Return the contents of this object as a JSON String.
     */
    @Override
    public String toString() {
        return new GsonBuilder().serializeSpecialFloatingPointValues().create().toJson(this);
    }

}
