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
package org.codelibs.fione.h2o.bindings.proxies.retrofit;

import org.codelibs.fione.h2o.bindings.pojos.ApiParseTypeValuesProvider;
import org.codelibs.fione.h2o.bindings.pojos.ParseSetupV3;

import retrofit2.Call;
import retrofit2.http.Field;
import retrofit2.http.FormUrlEncoded;
import retrofit2.http.POST;

public interface ParseSetup {

    /**
     * Guess the parameters for parsing raw byte-oriented data into an H2O Frame.
     *   @param source_frames Source frames
     *   @param parse_type Parser type
     *   @param separator Field separator
     *   @param single_quotes Single quotes
     *   @param check_header Check header: 0 means guess, +1 means 1st line is header not data, -1 means 1st line is data
     *                       not header
     *   @param column_names Column names
     *   @param skipped_columns Skipped columns indices
     *   @param column_types Value types for columns
     *   @param na_strings NA strings for columns
     *   @param column_name_filter Regex for names of columns to return
     *   @param column_offset Column offset to return
     *   @param column_count Number of columns to return
     *   @param total_filtered_column_count Total number of columns we would return with no column pagination
     *   @param custom_non_data_line_markers Custom characters to be treated as non-data line markers
     *   @param decrypt_tool Key-reference to an initialized instance of a Decryption Tool
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @FormUrlEncoded
    @POST("/3/ParseSetup")
    Call<ParseSetupV3> guessSetup(@Field("source_frames") String[] source_frames,
            @Field("parse_type") ApiParseTypeValuesProvider parse_type, @Field("separator") byte separator,
            @Field("single_quotes") boolean single_quotes, @Field("check_header") int check_header,
            @Field("column_names") String[] column_names, @Field("skipped_columns") int[] skipped_columns,
            @Field("column_types") String[] column_types, @Field("na_strings") String[][] na_strings,
            @Field("column_name_filter") String column_name_filter, @Field("column_offset") int column_offset,
            @Field("column_count") int column_count, @Field("total_filtered_column_count") int total_filtered_column_count,
            @Field("custom_non_data_line_markers") String custom_non_data_line_markers, @Field("decrypt_tool") String decrypt_tool,
            @Field("_exclude_fields") String _exclude_fields);

    @FormUrlEncoded
    @POST("/3/ParseSetup")
    Call<ParseSetupV3> guessSetup(@Field("source_frames") String[] source_frames);

}
