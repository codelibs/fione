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

public class FramesV3 extends RequestSchemaV3 {

    /**
     * Name of Frame of interest
     */
    @SerializedName("frame_id")
    public FrameKeyV3 frameId;

    /**
     * Name of column of interest
     */
    public String column;

    /**
     * Row offset to return
     */
    @SerializedName("row_offset")
    public long rowOffset;

    /**
     * Number of rows to return
     */
    @SerializedName("row_count")
    public int rowCount;

    /**
     * Column offset to return
     */
    @SerializedName("column_offset")
    public int columnOffset;

    /**
     * Number of full columns to return. The columns between full_column_count and column_count will be returned without
     * the data
     */
    @SerializedName("full_column_count")
    public int fullColumnCount;

    /**
     * Number of columns to return
     */
    @SerializedName("column_count")
    public int columnCount;

    /**
     * Find and return compatible models?
     */
    @SerializedName("find_compatible_models")
    public boolean findCompatibleModels;

    /**
     * File output path
     */
    public String path;

    /**
     * Overwrite existing file
     */
    public boolean force;

    /**
     * Number of part files to use (1=single file,-1=automatic)
     */
    @SerializedName("num_parts")
    public int numParts;

    /**
     * Compression method (default none; gzip, bzip2 and snappy available depending on runtime environment)
     */
    public String compression;

    /**
     * Field separator (default ',')
     */
    public byte separator;

    /**
     * Job for export file
     */
    public JobV3 job;

    /**
     * Frames
     */
    public FrameV3[] frames;

    /**
     * Compatible models
     */
    @SerializedName("compatible_models")
    public ModelSchemaV3[] compatibleModels;

    /**
     * Domains
     */
    public String[][] domain;

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
    public FramesV3() {
        column = "";
        rowOffset = 0L;
        rowCount = -1;
        columnOffset = 0;
        fullColumnCount = -1;
        columnCount = -1;
        findCompatibleModels = false;
        path = "";
        force = false;
        numParts = 1;
        compression = "";
        separator = 44;
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
