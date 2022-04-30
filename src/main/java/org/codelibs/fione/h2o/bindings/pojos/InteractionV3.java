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

public class InteractionV3 extends RequestSchemaV3 {

    /**
     * destination key
     */
    public FrameKeyV3 dest;

    /**
     * Input data frame
     */
    @SerializedName("source_frame")
    public FrameKeyV3 sourceFrame;

    /**
     * Factor columns
     */
    @SerializedName("factor_columns")
    public String[] factorColumns;

    /**
     * Whether to create pairwise quadratic interactions between factors (otherwise create one higher-order
     * interaction). Only applicable if there are 3 or more factors.
     */
    public boolean pairwise;

    /**
     * Max. number of factor levels in pair-wise interaction terms (if enforced, one extra catch-all factor will be
     * made)
     */
    @SerializedName("max_factors")
    public int maxFactors;

    /**
     * Min. occurrence threshold for factor levels in pair-wise interaction terms
     */
    @SerializedName("min_occurrence")
    public int minOccurrence;

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
    public InteractionV3() {
        pairwise = false;
        maxFactors = 100;
        minOccurrence = 1;
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
