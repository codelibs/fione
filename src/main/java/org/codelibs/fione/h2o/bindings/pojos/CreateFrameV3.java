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

public class CreateFrameV3 extends RequestSchemaV3 {

    /**
     * destination key
     */
    public FrameKeyV3 dest;

    /**
     * Number of rows
     */
    public long rows;

    /**
     * Number of data columns (in addition to the first response column)
     */
    public int cols;

    /**
     * Random number seed that determines the random values
     */
    public long seed;

    /**
     * Random number seed for setting the column types
     */
    @SerializedName("seed_for_column_types")
    public long seedForColumnTypes;

    /**
     * Whether frame should be randomized
     */
    public boolean randomize;

    /**
     * Constant value (for randomize=false)
     */
    public long value;

    /**
     * Range for real variables (-range ... range)
     */
    @SerializedName("real_range")
    public long realRange;

    /**
     * Fraction of categorical columns (for randomize=true)
     */
    @SerializedName("categorical_fraction")
    public double categoricalFraction;

    /**
     * Factor levels for categorical variables
     */
    public int factors;

    /**
     * Fraction of integer columns (for randomize=true)
     */
    @SerializedName("integer_fraction")
    public double integerFraction;

    /**
     * Range for integer variables (-range ... range)
     */
    @SerializedName("integer_range")
    public long integerRange;

    /**
     * Fraction of binary columns (for randomize=true)
     */
    @SerializedName("binary_fraction")
    public double binaryFraction;

    /**
     * Fraction of 1's in binary columns
     */
    @SerializedName("binary_ones_fraction")
    public double binaryOnesFraction;

    /**
     * Fraction of date/time columns (for randomize=true)
     */
    @SerializedName("time_fraction")
    public double timeFraction;

    /**
     * Fraction of string columns (for randomize=true)
     */
    @SerializedName("string_fraction")
    public double stringFraction;

    /**
     * Fraction of missing values
     */
    @SerializedName("missing_fraction")
    public double missingFraction;

    /**
     * Whether an additional response column should be generated
     */
    @SerializedName("has_response")
    public boolean hasResponse;

    /**
     * Number of factor levels of the first column (1=real, 2=binomial, N=multinomial or ordinal)
     */
    @SerializedName("response_factors")
    public int responseFactors;

    /**
     * For real-valued response variable: Whether the response should be positive only.
     */
    @SerializedName("positive_response")
    public boolean positiveResponse;

    /**
     * Job Key
     */
    public JobKeyV3 key;

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
    public CreateFrameV3() {
        rows = 10000L;
        cols = 10;
        seed = -1L;
        seedForColumnTypes = -1L;
        randomize = true;
        value = 0L;
        realRange = 100L;
        categoricalFraction = 0.2;
        factors = 100;
        integerFraction = 0.2;
        integerRange = 100L;
        binaryFraction = 0.1;
        binaryOnesFraction = 0.02;
        timeFraction = 0.0;
        stringFraction = 0.0;
        missingFraction = 0.01;
        hasResponse = false;
        responseFactors = 2;
        positiveResponse = false;
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
