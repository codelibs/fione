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

public class PartialDependenceV3 extends SchemaV3 {

    /**
     * Model
     */
    @SerializedName("model_id")
    public ModelKeyV3 modelId;

    /**
     * Frame
     */
    @SerializedName("frame_id")
    public FrameKeyV3 frameId;

    /**
     * Row Index
     */
    @SerializedName("row_index")
    public long rowIndex;

    /**
     * Column(s)
     */
    public String[] cols;

    /**
     * weight_column_index
     */
    @SerializedName("weight_column_index")
    public int weightColumnIndex;

    /**
     * add_missing_na
     */
    @SerializedName("add_missing_na")
    public boolean addMissingNa;

    /**
     * Number of bins
     */
    public int nbins;

    /**
     * User define split points
     */
    @SerializedName("user_splits")
    public double[] userSplits;

    /**
     * Column(s) of user defined splits
     */
    @SerializedName("user_cols")
    public String[] userCols;

    /**
     * Number of user defined splits per column
     */
    @SerializedName("num_user_splits")
    public int[] numUserSplits;

    /**
     * Partial Dependence Data
     */
    @SerializedName("partial_dependence_data")
    public TwoDimTableV3[] partialDependenceData;

    /**
     * lists of column name pairs to plot 2D pdp for
     */
    @SerializedName("col_pairs_2dpdp")
    public String[][] colPairs2dpdp;

    /**
     * Key to store the destination
     */
    @SerializedName("destination_key")
    public PartialDependenceKeyV3 destinationKey;

    /**
     * Target classes for multinomial classification
     */
    public String[] targets;

    /**
     * Public constructor
     */
    public PartialDependenceV3() {
        rowIndex = 0L;
        weightColumnIndex = 0;
        addMissingNa = false;
        nbins = 0;
    }

    /**
     * Return the contents of this object as a JSON String.
     */
    @Override
    public String toString() {
        return new GsonBuilder().serializeSpecialFloatingPointValues().create().toJson(this);
    }

}
