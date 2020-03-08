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

public class CreateFrameSimpleIV4 extends InputSchemaV4 {

    /**
     * Id for the frame to be created.
     */
    public FrameKeyV3 dest;

    /**
     * Random number seed that determines the random values.
     */
    public long seed;

    /**
     * Number of rows.
     */
    public int nrows;

    /**
     * Number of real-valued columns. Values in these columns will be uniformly distributed between real_lb and real_ub.
     */
    @SerializedName("ncols_real")
    public int ncolsReal;

    /**
     * Number of integer columns.
     */
    @SerializedName("ncols_int")
    public int ncolsInt;

    /**
     * Number of enum (categorical) columns.
     */
    @SerializedName("ncols_enum")
    public int ncolsEnum;

    /**
     * Number of boolean (binary) columns.
     */
    @SerializedName("ncols_bool")
    public int ncolsBool;

    /**
     * Number of string columns.
     */
    @SerializedName("ncols_str")
    public int ncolsStr;

    /**
     * Number of time columns.
     */
    @SerializedName("ncols_time")
    public int ncolsTime;

    /**
     * Lower bound for the range of the real-valued columns.
     */
    @SerializedName("real_lb")
    public double realLb;

    /**
     * Upper bound for the range of the real-valued columns.
     */
    @SerializedName("real_ub")
    public double realUb;

    /**
     * Lower bound for the range of integer columns.
     */
    @SerializedName("int_lb")
    public int intLb;

    /**
     * Upper bound for the range of integer columns.
     */
    @SerializedName("int_ub")
    public int intUb;

    /**
     * Number of levels (categories) for the enum columns.
     */
    @SerializedName("enum_nlevels")
    public int enumNlevels;

    /**
     * Fraction of ones in each boolean (binary) column.
     */
    @SerializedName("bool_p")
    public double boolP;

    /**
     * Lower bound for the range of time columns (in ms since the epoch).
     */
    @SerializedName("time_lb")
    public long timeLb;

    /**
     * Upper bound for the range of time columns (in ms since the epoch).
     */
    @SerializedName("time_ub")
    public long timeUb;

    /**
     * Length of generated strings in string columns.
     */
    @SerializedName("str_length")
    public int strLength;

    /**
     * Fraction of missing values.
     */
    @SerializedName("missing_fraction")
    public double missingFraction;

    /**
     * Type of the response column to add.
     */
    @SerializedName("response_type")
    public SimpleRecipeResponseType responseType;

    /**
     * Lower bound for the response variable (real/int/time types).
     */
    @SerializedName("response_lb")
    public double responseLb;

    /**
     * Upper bound for the response variable (real/int/time types).
     */
    @SerializedName("response_ub")
    public double responseUb;

    /**
     * Frequency of 1s for the bool (binary) response column.
     */
    @SerializedName("response_p")
    public double responseP;

    /**
     * Number of categorical levels for the enum response column.
     */
    @SerializedName("response_nlevels")
    public int responseNlevels;

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
    public CreateFrameSimpleIV4() {
        seed = -1L;
        nrows = 100;
        ncolsReal = 0;
        ncolsInt = 0;
        ncolsEnum = 0;
        ncolsBool = 0;
        ncolsStr = 0;
        ncolsTime = 0;
        realLb = -100.0;
        realUb = 100.0;
        intLb = -100;
        intUb = 100;
        enumNlevels = 10;
        boolP = 0.3;
        timeLb = 946080000000L;
        timeUb = 1576800000000L;
        strLength = 8;
        missingFraction = 0.0;
        responseType = SimpleRecipeResponseType.NONE;
        responseLb = 0.0;
        responseUb = 10.0;
        responseP = 0.6;
        responseNlevels = 25;
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
