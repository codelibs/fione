/*
 * Copyright 2012-2023 CodeLibs Project and the Others.
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
import org.codelibs.fione.h2o.bindings.pojos.ParseV3;

import retrofit2.Call;
import retrofit2.http.Field;
import retrofit2.http.FormUrlEncoded;
import retrofit2.http.POST;

public interface Parse {

    /**
     * Parse a raw byte-oriented Frame into a useful columnar data Frame.
     *   @param destination_frame Final frame name
     *   @param source_frames Source frames
     *   @param parse_type Parser type
     *   @param separator Field separator
     *   @param single_quotes Single Quotes
     *   @param check_header Check header: 0 means guess, +1 means 1st line is header not data, -1 means 1st line is data
     *                       not header
     *   @param number_columns Number of columns
     *   @param column_names Column names
     *   @param column_types Value types for columns
     *   @param skipped_columns Skipped columns indices
     *   @param domains Domains for categorical columns
     *   @param na_strings NA strings for columns
     *   @param chunk_size Size of individual parse tasks
     *   @param delete_on_done Delete input key after parse
     *   @param blocking Block until the parse completes (as opposed to returning early and requiring polling
     *   @param decrypt_tool Key-reference to an initialized instance of a Decryption Tool
     *   @param custom_non_data_line_markers Custom characters to be treated as non-data line markers
     *   @param partition_by Name of the column the persisted dataset has been partitioned by.
     *   @param escapechar One ASCII character used to escape other characters.
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @FormUrlEncoded
    @POST("/3/Parse")
    Call<ParseV3> parse(@Field("destination_frame") String destination_frame, @Field("source_frames") String[] source_frames,
            @Field("parse_type") ApiParseTypeValuesProvider parse_type, @Field("separator") byte separator,
            @Field("single_quotes") boolean single_quotes, @Field("check_header") int check_header,
            @Field("number_columns") int number_columns, @Field("column_names") String[] column_names,
            @Field("column_types") String[] column_types, @Field("skipped_columns") int[] skipped_columns,
            @Field("domains") String[][] domains, @Field("na_strings") String[][] na_strings, @Field("chunk_size") int chunk_size,
            @Field("delete_on_done") boolean delete_on_done, @Field("blocking") boolean blocking,
            @Field("decrypt_tool") String decrypt_tool, @Field("custom_non_data_line_markers") String custom_non_data_line_markers,
            @Field("partition_by") String[] partition_by, @Field("escapechar") byte escapechar,
            @Field("_exclude_fields") String _exclude_fields);

    @FormUrlEncoded
    @POST("/3/Parse")
    Call<ParseV3> parse(@Field("destination_frame") String destination_frame, @Field("source_frames") String[] source_frames);

}
