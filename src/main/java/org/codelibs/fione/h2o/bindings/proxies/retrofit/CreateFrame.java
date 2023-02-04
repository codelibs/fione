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

import org.codelibs.fione.h2o.bindings.pojos.JobV3;

import retrofit2.Call;
import retrofit2.http.Field;
import retrofit2.http.FormUrlEncoded;
import retrofit2.http.POST;

public interface CreateFrame {

    /**
     * Create a synthetic H2O Frame with random data. You can specify the number of rows/columns, as well as column types:
     * integer, real, boolean, time, string, categorical. The frame may also have a dedicated "response" column, and some
     * of the entries in the dataset may be created as missing.
     *   @param dest destination key
     *   @param rows Number of rows
     *   @param cols Number of data columns (in addition to the first response column)
     *   @param seed Random number seed that determines the random values
     *   @param seed_for_column_types Random number seed for setting the column types
     *   @param randomize Whether frame should be randomized
     *   @param value Constant value (for randomize=false)
     *   @param real_range Range for real variables (-range ... range)
     *   @param categorical_fraction Fraction of categorical columns (for randomize=true)
     *   @param factors Factor levels for categorical variables
     *   @param integer_fraction Fraction of integer columns (for randomize=true)
     *   @param integer_range Range for integer variables (-range ... range)
     *   @param binary_fraction Fraction of binary columns (for randomize=true)
     *   @param binary_ones_fraction Fraction of 1's in binary columns
     *   @param time_fraction Fraction of date/time columns (for randomize=true)
     *   @param string_fraction Fraction of string columns (for randomize=true)
     *   @param missing_fraction Fraction of missing values
     *   @param has_response Whether an additional response column should be generated
     *   @param response_factors Number of factor levels of the first column (1=real, 2=binomial, N=multinomial or
     *                           ordinal)
     *   @param positive_response For real-valued response variable: Whether the response should be positive only.
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @FormUrlEncoded
    @POST("/3/CreateFrame")
    Call<JobV3> run(@Field("dest") String dest, @Field("rows") long rows, @Field("cols") int cols, @Field("seed") long seed,
            @Field("seed_for_column_types") long seed_for_column_types, @Field("randomize") boolean randomize, @Field("value") long value,
            @Field("real_range") long real_range, @Field("categorical_fraction") double categorical_fraction, @Field("factors") int factors,
            @Field("integer_fraction") double integer_fraction, @Field("integer_range") long integer_range,
            @Field("binary_fraction") double binary_fraction, @Field("binary_ones_fraction") double binary_ones_fraction,
            @Field("time_fraction") double time_fraction, @Field("string_fraction") double string_fraction,
            @Field("missing_fraction") double missing_fraction, @Field("has_response") boolean has_response,
            @Field("response_factors") int response_factors, @Field("positive_response") boolean positive_response,
            @Field("_exclude_fields") String _exclude_fields);

    @FormUrlEncoded
    @POST("/3/CreateFrame")
    Call<JobV3> run();

}
