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

public class TabulateV3 extends SchemaV3 {

    /**
     * Dataset
     */
    public FrameKeyV3 dataset;

    /**
     * Predictor
     */
    public ColSpecifierV3 predictor;

    /**
     * Response
     */
    public ColSpecifierV3 response;

    /**
     * Observation weights (optional)
     */
    public ColSpecifierV3 weight;

    /**
     * Number of bins for predictor column
     */
    @SerializedName("nbins_predictor")
    public int nbinsPredictor;

    /**
     * Number of bins for response column
     */
    @SerializedName("nbins_response")
    public int nbinsResponse;

    /**
     * Counts table
     */
    @SerializedName("count_table")
    public TwoDimTableV3 countTable;

    /**
     * Response table
     */
    @SerializedName("response_table")
    public TwoDimTableV3 responseTable;

    /**
     * Public constructor
     */
    public TabulateV3() {
        nbinsPredictor = 20;
        nbinsResponse = 10;
    }

    /**
     * Return the contents of this object as a JSON String.
     */
    @Override
    public String toString() {
        return new GsonBuilder().serializeSpecialFloatingPointValues().create().toJson(this);
    }

}
