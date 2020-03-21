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

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

import org.apache.commons.lang3.ArrayUtils;
import org.codelibs.fione.entity.ChartData;

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

    private ChartData histogramChart;

    private ChartData labelListChart;

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

    public boolean isAvailableCharts() {
        return getHistogramChart() != null || getLabelListChart() != null;
    }

    public ChartData getHistogramChart() {
        if (histogramChart != null) {
            return histogramChart;
        }
        if (histogramBins != null) {
            if ("real".equals(type) || "int".equals(type)) {
                histogramChart = new ChartData();
                final String yName = "count";
                final int range = histogramBins.length / 50 + 1;
                double pos = histogramBase;
                final List<Double> xList = new ArrayList<>();
                final List<Long> yList = new ArrayList<>();
                long sum = 0;
                for (int i = 0; i < histogramBins.length; i++) {
                    if (i % range == 0) {
                        xList.add(pos);
                        if (i != 0) {
                            yList.add(sum);
                            sum = 0;
                        }
                    }
                    pos += histogramStride;
                    sum += histogramBins[i];
                }
                yList.add(sum);
                histogramChart.addColumn(label, xList.toArray(n -> new Double[n]));
                histogramChart.addColumn(yName, yList.toArray(n -> new Long[n]));
                histogramChart.setAxisName(label);
                histogramChart.addAxisLabel("x", label);
                histogramChart.addAxisLabel("y", yName);
                return histogramChart;

            }
        }
        return null;
    }

    public ChartData getLabelListChart() {
        if (labelListChart != null) {
            return labelListChart;
        }
        if (histogramBins != null && domain != null) {
            if ("enum".equals(type)) {
                final String xName = "label";
                final String yName = "count";
                labelListChart = new ChartData();
                String[] domains = Arrays.copyOf(domain, domain.length);
                ArrayUtils.reverse(domains);
                labelListChart.addColumn(xName, domains);
                Long[] bins = Arrays.stream(histogramBins).mapToObj(Long::valueOf).toArray(n -> new Long[n]);
                bins = Arrays.copyOf(bins, bins.length);
                ArrayUtils.reverse(bins);
                labelListChart.addColumn(yName, bins, "bar");
                labelListChart.setAxisName(xName);
                labelListChart.addAxisLabel("x", xName);
                labelListChart.addAxisType("x", "category");
                labelListChart.addAxisLabel("y", yName);
                labelListChart.setAxisRotated(true);
                int height = domain.length * 30;
                if (height < 200) {
                    height = 200;
                }
                labelListChart.setHeight(height);
                return labelListChart;
            }
        }
        return null;
    }
}
