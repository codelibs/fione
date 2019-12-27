/*
 * Copyright 2012-2019 CodeLibs Project and the Others.
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

public class CreateFrameOriginalIV4 extends InputSchemaV4 {

    /**
     * destination key
     */
    public FrameKeyV3 dest;

    /**
     * Number of rows
     */
    public int rows;

    /**
     * Number of data columns (in addition to the first response column)
     */
    public int cols;

    /**
     * Random number seed that determines the random values
     */
    public long seed;

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
    public double realRange;

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
    public int integerRange;

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
     * Number of factor levels of the first column (1=real, 2=binomial, N=multinomial)
     */
    @SerializedName("response_factors")
    public int responseFactors;

    /**
     * For real-valued response variable: Whether the response should be positive only.
     */
    @SerializedName("positive_response")
    public boolean positiveResponse;

    /*------------------------------------------------------------------------------------------------------------------
    //                                                  INHERITED
    //------------------------------------------------------------------------------------------------------------------

    // Filter on the set of output fields: if you set _fields="foo,bar,baz", then only those fields will be included in
    // the output; or you can specify _fields="-goo,gee" to include all fields except goo and gee. If the result
    // contains nested data structures, then you can refer to the fields within those structures as well. For example if
    // you specify _fields="foo(oof),bar(-rab)", then only fields foo and bar will be included, and within foo there
    // will be only field oof, whereas within bar all fields except rab will be reported.
    public String _fields;

    */

    /**
     * Public constructor
     */
    public CreateFrameOriginalIV4() {
        rows = 10000;
        cols = 10;
        seed = -1L;
        randomize = true;
        value = 0L;
        realRange = 100.0;
        categoricalFraction = 0.2;
        factors = 100;
        integerFraction = 0.2;
        integerRange = 100;
        binaryFraction = 0.1;
        binaryOnesFraction = 0.02;
        timeFraction = 0.0;
        stringFraction = 0.0;
        missingFraction = 0.01;
        hasResponse = false;
        responseFactors = 2;
        positiveResponse = false;
        _fields = "";
    }

    /**
     * Return the contents of this object as a JSON String.
     */
    @Override
    public String toString() {
        return new GsonBuilder().serializeSpecialFloatingPointValues().create().toJson(this);
    }

}
