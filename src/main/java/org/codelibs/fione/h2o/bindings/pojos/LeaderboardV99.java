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

import org.codelibs.core.lang.StringUtil;

import com.google.gson.GsonBuilder;
import com.google.gson.annotations.SerializedName;

public class LeaderboardV99 extends SchemaV3 {

    /**
     * Identifier for models that should be grouped together in the leaderboard
     */
    @SerializedName("project_name")
    public String projectName;

    /**
     * List of models for this leaderboard, sorted by metric so that the best is first
     */
    public ModelKeyV3[] models;

    /**
     * Frame for this leaderboard
     */
    @SerializedName("leaderboard_frame")
    public FrameKeyV3 leaderboardFrame;

    /**
     * Checksum for the Frame for this leaderboard
     */
    @SerializedName("leaderboard_frame_checksum")
    public long leaderboardFrameChecksum;

    /**
     * Sort metrics for the models in this leaderboard, in the same order as the models
     */
    @SerializedName("sort_metrics")
    public double[] sortMetrics;

    /**
     * Metric used to sort this leaderboard
     */
    @SerializedName("sort_metric")
    public String sortMetric;

    /**
     * Metric direction used in the sort
     */
    @SerializedName("sort_decreasing")
    public boolean sortDecreasing;

    /**
     * A table representation of this leaderboard, for easy rendering
     */
    public TwoDimTableV3 table;

    /**
     * Public constructor
     */
    public LeaderboardV99() {
        projectName = "<default>";
        leaderboardFrameChecksum = 0L;
        sortMetric = "";
        sortDecreasing = false;
    }

    /**
     * Return the contents of this object as a JSON String.
     */
    @Override
    public String toString() {
        return new GsonBuilder().serializeSpecialFloatingPointValues().create().toJson(this);
    }

    public String[] getColumnNames() {
        return Arrays.stream(table.columns).filter(c -> StringUtil.isNotBlank(c.name)).map(c -> c.name).toArray(n -> new String[n]);
    }

    public List<List<String>> getDataRows() {
        final List<List<String>> dataList = new ArrayList<>(100);
        for (int index = 0; index < models.length; index++) {
            final List<String> list = new ArrayList<>();
            for (int i = 0; i < table.columns.length; i++) {
                final ColumnSpecsBase column = table.columns[i];
                if (StringUtil.isBlank(column.name)) {
                    continue;
                }
                final Object value = table.data[i][index];
                try {
                    final String formattedValue = String.format(column.format, value);
                    list.add(formattedValue);
                } catch (final Exception e) {
                    if (value != null) {
                        list.add(value.toString());
                    } else {
                        list.add(StringUtil.EMPTY);
                    }
                }
            }
            dataList.add(list);
        }
        return dataList;
    }
}
