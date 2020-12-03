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

import java.util.Arrays;
import java.util.Objects;

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

    @Override
    public int hashCode() {
        final var prime = 31;
        var result = 1;
        result = prime * result + ((column == null) ? 0 : column.hashCode());
        result = prime * result + columnCount;
        result = prime * result + columnOffset;
        result = prime * result + Arrays.hashCode(compatibleModels);
        result = prime * result + ((compression == null) ? 0 : compression.hashCode());
        result = prime * result + Arrays.deepHashCode(domain);
        result = prime * result + (findCompatibleModels ? 1231 : 1237);
        result = prime * result + (force ? 1231 : 1237);
        result = prime * result + ((frameId == null) ? 0 : frameId.hashCode());
        result = prime * result + Arrays.hashCode(frames);
        result = prime * result + fullColumnCount;
        result = prime * result + ((job == null) ? 0 : job.hashCode());
        result = prime * result + numParts;
        result = prime * result + ((path == null) ? 0 : path.hashCode());
        result = prime * result + rowCount;
        result = prime * result + (int) (rowOffset ^ (rowOffset >>> 32));
        result = prime * result + separator;
        return result;
    }

    @Override
    public boolean equals(final Object obj) {
        if (this == obj) {
            return true;
        }
        if (obj == null) {
            return false;
        }
        if (getClass() != obj.getClass()) {
            return false;
        }
        final var other = (FramesV3) obj;
        if (!Objects.equals(column, other.column)) {
            return false;
        }
        if (columnCount != other.columnCount) {
            return false;
        }
        if (columnOffset != other.columnOffset) {
            return false;
        }
        if (!Arrays.equals(compatibleModels, other.compatibleModels)) {
            return false;
        }
        if (!Objects.equals(compression, other.compression)) {
            return false;
        }
        if (!Arrays.deepEquals(domain, other.domain)) {
            return false;
        }
        if (findCompatibleModels != other.findCompatibleModels) {
            return false;
        }
        if (force != other.force) {
            return false;
        }
        if (!Objects.equals(frameId, other.frameId)) {
            return false;
        }
        if (!Arrays.equals(frames, other.frames)) {
            return false;
        }
        if (fullColumnCount != other.fullColumnCount) {
            return false;
        }
        if (!Objects.equals(job, other.job)) {
            return false;
        }
        if (numParts != other.numParts) {
            return false;
        }
        if (!Objects.equals(path, other.path)) {
            return false;
        }
        if (rowCount != other.rowCount) {
            return false;
        }
        if (rowOffset != other.rowOffset) {
            return false;
        }
        if (separator != other.separator) {
            return false;
        }
        return true;
    }

}
