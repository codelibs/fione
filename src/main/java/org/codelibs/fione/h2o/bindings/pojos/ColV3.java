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

public class ColV3 extends SchemaV3 {

    /**
     * label
     */
    public String label;

    /**
     * missing
     */
    @SerializedName("missing_count")
    public long missingCount;

    /**
     * zeros
     */
    @SerializedName("zero_count")
    public long zeroCount;

    /**
     * positive infinities
     */
    @SerializedName("positive_infinity_count")
    public long positiveInfinityCount;

    /**
     * negative infinities
     */
    @SerializedName("negative_infinity_count")
    public long negativeInfinityCount;

    /**
     * mins
     */
    public double[] mins;

    /**
     * maxs
     */
    public double[] maxs;

    /**
     * mean
     */
    public double mean;

    /**
     * sigma
     */
    public double sigma;

    /**
     * datatype: {enum, string, int, real, time, uuid}
     */
    public String type;

    /**
     * domain; not-null for categorical columns only
     */
    public String[] domain;

    /**
     * cardinality of this column's domain; not-null for categorical columns only
     */
    @SerializedName("domain_cardinality")
    public int domainCardinality;

    /**
     * data
     */
    public double[] data;

    /**
     * string data
     */
    @SerializedName("string_data")
    public String[] stringData;

    /**
     * decimal precision, -1 for all digits
     */
    public byte precision;

    /**
     * Histogram bins; null if not computed
     */
    @SerializedName("histogram_bins")
    public long[] histogramBins;

    /**
     * Start of histogram bin zero
     */
    @SerializedName("histogram_base")
    public double histogramBase;

    /**
     * Stride per bin
     */
    @SerializedName("histogram_stride")
    public double histogramStride;

    /**
     * Percentile values, matching the default percentiles
     */
    public double[] percentiles;

    /**
     * Public constructor
     */
    public ColV3() {
        label = "";
        missingCount = 0L;
        zeroCount = 0L;
        positiveInfinityCount = 0L;
        negativeInfinityCount = 0L;
        mean = 0.0;
        sigma = 0.0;
        type = "";
        domainCardinality = 0;
        precision = 0;
        histogramBase = 0.0;
        histogramStride = 0.0;
    }

    /**
     * Return the contents of this object as a JSON String.
     */
    @Override
    public String toString() {
        return new GsonBuilder().serializeSpecialFloatingPointValues().create().toJson(this);
    }

}
