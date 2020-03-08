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

public class GramV3 {

    /**
     * source data
     */
    @SerializedName("X")
    public FrameKeyV3 x;

    /**
     * weight vector
     */
    @SerializedName("W")
    public ColSpecifierV3 w;

    /**
     * use all factor levels when doing 1-hot encoding
     */
    @SerializedName("use_all_factor_levels")
    public boolean useAllFactorLevels;

    /**
     * standardize data
     */
    public boolean standardize;

    /**
     * skip missing values
     */
    @SerializedName("skip_missing")
    public boolean skipMissing;

    /**
     * Destination key for the resulting matrix.
     */
    @SerializedName("destination_frame")
    public FrameKeyV3 destinationFrame;

    /**
     * Public constructor
     */
    public GramV3() {
        useAllFactorLevels = false;
        standardize = false;
        skipMissing = false;
    }

    /**
     * Return the contents of this object as a JSON String.
     */
    @Override
    public String toString() {
        return new GsonBuilder().serializeSpecialFloatingPointValues().create().toJson(this);
    }

}
