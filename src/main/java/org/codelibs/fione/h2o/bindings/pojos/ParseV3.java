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

import org.codelibs.core.lang.StringUtil;

import com.google.gson.GsonBuilder;
import com.google.gson.annotations.SerializedName;

public class ParseV3 extends RequestSchemaV3 {

    /**
     * Final frame name
     */
    @SerializedName("destination_frame")
    public FrameKeyV3 destinationFrame;

    /**
     * Source frames
     */
    @SerializedName("source_frames")
    public FrameKeyV3[] sourceFrames;

    /**
     * Parser type
     */
    @SerializedName("parse_type")
    public ApiParseTypeValuesProvider parseType;

    /**
     * Field separator
     */
    public byte separator;

    /**
     * Single Quotes
     */
    @SerializedName("single_quotes")
    public boolean singleQuotes;

    /**
     * Check header: 0 means guess, +1 means 1st line is header not data, -1 means 1st line is data not header
     */
    @SerializedName("check_header")
    public int checkHeader;

    /**
     * Number of columns
     */
    @SerializedName("number_columns")
    public int numberColumns;

    /**
     * Column names
     */
    @SerializedName("column_names")
    public String[] columnNames;

    /**
     * Value types for columns
     */
    @SerializedName("column_types")
    public String[] columnTypes;

    /**
     * Skipped columns indices
     */
    @SerializedName("skipped_columns")
    public int[] skippedColumns;

    /**
     * Domains for categorical columns
     */
    public String[][] domains;

    /**
     * NA strings for columns
     */
    @SerializedName("na_strings")
    public String[][] naStrings;

    /**
     * Size of individual parse tasks
     */
    @SerializedName("chunk_size")
    public int chunkSize;

    /**
     * Delete input key after parse
     */
    @SerializedName("delete_on_done")
    public boolean deleteOnDone;

    /**
     * Block until the parse completes (as opposed to returning early and requiring polling
     */
    public boolean blocking;

    /**
     * Key-reference to an initialized instance of a Decryption Tool
     */
    @SerializedName("decrypt_tool")
    public DecryptionToolKeyV3 decryptTool;

    /**
     * Custom characters to be treated as non-data line markers
     */
    @SerializedName("custom_non_data_line_markers")
    public String customNonDataLineMarkers;

    /**
     * Parse job
     */
    public JobV3 job;

    /**
     * Rows
     */
    public long rows;

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
    public ParseV3() {
        separator = 0;
        singleQuotes = false;
        checkHeader = 0;
        numberColumns = 0;
        chunkSize = 0;
        deleteOnDone = false;
        blocking = false;
        customNonDataLineMarkers = "";
        rows = 0L;
        _excludeFields = "";
    }

    /**
     * Return the contents of this object as a JSON String.
     */
    @Override
    public String toString() {
        return new GsonBuilder().serializeSpecialFloatingPointValues().create().toJson(this);
    }

    public String[] getAvailableColumnNames() {
        if (columnNames != null) {
            return columnNames;
        }
        if (columnTypes != null) {
            final String[] names = new String[columnTypes.length];
            for (int i = 0; i < columnTypes.length; i++) {
                names[i] = "C" + (i + 1);
            }
            return names;
        }
        return StringUtil.EMPTY_STRINGS;
    }
}
