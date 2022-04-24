/*
 * Copyright 2012-2022 CodeLibs Project and the Others.
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

public class ParseSetupV3 extends RequestSchemaV3 {

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
     * Single quotes
     */
    @SerializedName("single_quotes")
    public boolean singleQuotes;

    /**
     * Check header: 0 means guess, +1 means 1st line is header not data, -1 means 1st line is data not header
     */
    @SerializedName("check_header")
    public int checkHeader;

    /**
     * Column names
     */
    @SerializedName("column_names")
    public String[] columnNames;

    /**
     * Skipped columns indices
     */
    @SerializedName("skipped_columns")
    public int[] skippedColumns;

    /**
     * Value types for columns
     */
    @SerializedName("column_types")
    public String[] columnTypes;

    /**
     * NA strings for columns
     */
    @SerializedName("na_strings")
    public String[][] naStrings;

    /**
     * Regex for names of columns to return
     */
    @SerializedName("column_name_filter")
    public String columnNameFilter;

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
     * Suggested name
     */
    @SerializedName("destination_frame")
    public String destinationFrame;

    /**
     * Number of header lines found
     */
    @SerializedName("header_lines")
    public long headerLines;

    /**
     * Number of columns
     */
    @SerializedName("number_columns")
    public int numberColumns;

    /**
     * Sample data
     */
    public String[][] data;

    /**
     * Warnings
     */
    public String[] warnings;

    /**
     * Size of individual parse tasks
     */
    @SerializedName("chunk_size")
    public int chunkSize;

    /**
     * Total number of columns we would return with no column pagination
     */
    @SerializedName("total_filtered_column_count")
    public int totalFilteredColumnCount;

    /**
     * Custom characters to be treated as non-data line markers
     */
    @SerializedName("custom_non_data_line_markers")
    public String customNonDataLineMarkers;

    /**
     * Key-reference to an initialized instance of a Decryption Tool
     */
    @SerializedName("decrypt_tool")
    public DecryptionToolKeyV3 decryptTool;

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
    public ParseSetupV3() {
        parseType = ApiParseTypeValuesProvider.GUESS;
        separator = 0;
        singleQuotes = false;
        checkHeader = 0;
        columnNameFilter = "";
        columnOffset = 0;
        columnCount = 0;
        destinationFrame = "";
        headerLines = 0L;
        numberColumns = -1;
        chunkSize = 4194304; // 1 << 22
        totalFilteredColumnCount = 0;
        customNonDataLineMarkers = "";
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
