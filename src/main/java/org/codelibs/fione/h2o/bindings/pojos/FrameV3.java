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

public class FrameV3 extends FrameBaseV3 {

    /**
     * Row offset to display
     */
    @SerializedName("row_offset")
    public long rowOffset;

    /**
     * Number of rows to display
     */
    @SerializedName("row_count")
    public int rowCount;

    /**
     * Column offset to return
     */
    @SerializedName("column_offset")
    public int columnOffset;

    /**
     * Number of columns to return
     */
    @SerializedName("column_count")
    public int columnCount;

    /**
     * Number of full columns to return. The columns between full_column_count and column_count will be returned without
     * the data
     */
    @SerializedName("full_column_count")
    public int fullColumnCount;

    /**
     * Total number of columns in the Frame
     */
    @SerializedName("total_column_count")
    public int totalColumnCount;

    /**
     * checksum
     */
    public long checksum;

    /**
     * Number of rows in the Frame
     */
    public long rows;

    /**
     * Number of columns in the Frame
     */
    @SerializedName("num_columns")
    public long numColumns;

    /**
     * Default percentiles, from 0 to 1
     */
    @SerializedName("default_percentiles")
    public double[] defaultPercentiles;

    /**
     * Columns in the Frame
     */
    public ColV3[] columns;

    /**
     * Compatible models, if requested
     */
    @SerializedName("compatible_models")
    public String[] compatibleModels;

    /**
     * Chunk summary
     */
    @SerializedName("chunk_summary")
    public TwoDimTableV3 chunkSummary;

    /**
     * Distribution summary
     */
    @SerializedName("distribution_summary")
    public TwoDimTableV3 distributionSummary;

    /*------------------------------------------------------------------------------------------------------------------
    //                                                  INHERITED
    //------------------------------------------------------------------------------------------------------------------

    // Frame ID
    public FrameKeyV3 frameId;

    // Total data size in bytes
    public long byteSize;

    // Is this Frame raw unparsed data?
    public boolean isText;

    // Comma-separated list of JSON field paths to exclude from the result, used like:
    // "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
    public String _excludeFields;

    */

    /**
     * Public constructor
     */
    public FrameV3() {
        rowOffset = 0L;
        rowCount = 0;
        columnOffset = 0;
        columnCount = 0;
        fullColumnCount = 0;
        totalColumnCount = 0;
        checksum = 0L;
        rows = 0L;
        numColumns = 0L;
        byteSize = 0L;
        isText = false;
        _excludeFields = "";
    }

    /**
     * Return the contents of this object as a JSON String.
     */
    @Override
    public String toString() {
        return new GsonBuilder().serializeSpecialFloatingPointValues().create().toJson(this);
    }

    public String[] getColumnNames() {
        return Arrays.stream(columns).map(c -> c.label).toArray(n -> new String[n]);
    }

    public int getRowSize() {
        if (columns != null && columns.length > 0) {
            if (columns[0].data != null) {
                return columns[0].data.length;
            }
            if (columns[0].stringData != null) {
                return columns[0].stringData.length;
            }
        }
        return 0;
    }

    public List<List<String>> getDataRows() {
        final List<List<String>> dataList = new ArrayList<>(20);
        final int rowSize = getRowSize();
        for (int i = 0; i < rowSize; i++) {
            final List<String> list = new ArrayList<>();
            for (final ColV3 column : columns) {
                if (column.data != null) {
                    list.add(Double.toString(column.data[i]));
                } else if (column.stringData != null) {
                    list.add(column.stringData[i]);
                } else {
                    list.add(StringUtil.EMPTY);
                }
            }
            dataList.add(list);
        }
        return dataList;
    }
}
