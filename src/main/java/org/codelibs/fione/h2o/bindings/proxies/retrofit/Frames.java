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

import org.codelibs.fione.h2o.bindings.pojos.FramesListV3;
import org.codelibs.fione.h2o.bindings.pojos.FramesV3;
import org.codelibs.fione.h2o.bindings.pojos.JobV4;
import org.codelibs.fione.h2o.bindings.pojos.SimpleRecipeResponseType;

import retrofit2.Call;
import retrofit2.http.DELETE;
import retrofit2.http.Field;
import retrofit2.http.FormUrlEncoded;
import retrofit2.http.GET;
import retrofit2.http.POST;
import retrofit2.http.Path;
import retrofit2.http.Query;

public interface Frames {

    /**
     * Export a Frame to the given path with optional overwrite.
     *   @param frame_id Name of Frame of interest
     *   @param column Name of column of interest
     *   @param row_offset Row offset to return
     *   @param row_count Number of rows to return
     *   @param column_offset Column offset to return
     *   @param full_column_count Number of full columns to return. The columns between full_column_count and column_count
     *                            will be returned without the data
     *   @param column_count Number of columns to return
     *   @param find_compatible_models Find and return compatible models?
     *   @param path File output path
     *   @param force Overwrite existing file
     *   @param num_parts Number of part files to use (1=single file,-1=automatic)
     *   @param compression Compression method (default none; gzip, bzip2 and snappy available depending on runtime
     *                      environment)
     *   @param separator Field separator (default ',')
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @FormUrlEncoded
    @POST("/3/Frames/{frame_id}/export")
    Call<FramesV3> export(@Path("frame_id") String frame_id, @Field("column") String column, @Field("row_offset") long row_offset,
            @Field("row_count") int row_count, @Field("column_offset") int column_offset,
            @Field("full_column_count") int full_column_count, @Field("column_count") int column_count,
            @Field("find_compatible_models") boolean find_compatible_models, @Field("path") String path, @Field("force") boolean force,
            @Field("num_parts") int num_parts, @Field("compression") String compression, @Field("separator") byte separator,
            @Field("_exclude_fields") String _exclude_fields);

    @FormUrlEncoded
    @POST("/3/Frames/{frame_id}/export")
    Call<FramesV3> export(@Path("frame_id") String frame_id);

    /**
     * Return the summary metrics for a column, e.g. min, max, mean, sigma, percentiles, etc.
     *   @param frame_id Name of Frame of interest
     *   @param column Name of column of interest
     *   @param row_offset Row offset to return
     *   @param row_count Number of rows to return
     *   @param column_offset Column offset to return
     *   @param full_column_count Number of full columns to return. The columns between full_column_count and column_count
     *                            will be returned without the data
     *   @param column_count Number of columns to return
     *   @param find_compatible_models Find and return compatible models?
     *   @param path File output path
     *   @param force Overwrite existing file
     *   @param num_parts Number of part files to use (1=single file,-1=automatic)
     *   @param compression Compression method (default none; gzip, bzip2 and snappy available depending on runtime
     *                      environment)
     *   @param separator Field separator (default ',')
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @GET("/3/Frames/{frame_id}/columns/{column}/summary")
    Call<FramesV3> columnSummary(@Path("frame_id") String frame_id, @Path("column") String column, @Query("row_offset") long row_offset,
            @Query("row_count") int row_count, @Query("column_offset") int column_offset,
            @Query("full_column_count") int full_column_count, @Query("column_count") int column_count,
            @Query("find_compatible_models") boolean find_compatible_models, @Query("path") String path, @Query("force") boolean force,
            @Query("num_parts") int num_parts, @Query("compression") String compression, @Query("separator") byte separator,
            @Query("_exclude_fields") String _exclude_fields);

    @GET("/3/Frames/{frame_id}/columns/{column}/summary")
    Call<FramesV3> columnSummary(@Path("frame_id") String frame_id, @Path("column") String column);

    /**
     * Return the domains for the specified categorical column ("null" if the column is not a categorical).
     *   @param frame_id Name of Frame of interest
     *   @param column Name of column of interest
     *   @param row_offset Row offset to return
     *   @param row_count Number of rows to return
     *   @param column_offset Column offset to return
     *   @param full_column_count Number of full columns to return. The columns between full_column_count and column_count
     *                            will be returned without the data
     *   @param column_count Number of columns to return
     *   @param find_compatible_models Find and return compatible models?
     *   @param path File output path
     *   @param force Overwrite existing file
     *   @param num_parts Number of part files to use (1=single file,-1=automatic)
     *   @param compression Compression method (default none; gzip, bzip2 and snappy available depending on runtime
     *                      environment)
     *   @param separator Field separator (default ',')
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @GET("/3/Frames/{frame_id}/columns/{column}/domain")
    Call<FramesV3> columnDomain(@Path("frame_id") String frame_id, @Path("column") String column, @Query("row_offset") long row_offset,
            @Query("row_count") int row_count, @Query("column_offset") int column_offset,
            @Query("full_column_count") int full_column_count, @Query("column_count") int column_count,
            @Query("find_compatible_models") boolean find_compatible_models, @Query("path") String path, @Query("force") boolean force,
            @Query("num_parts") int num_parts, @Query("compression") String compression, @Query("separator") byte separator,
            @Query("_exclude_fields") String _exclude_fields);

    @GET("/3/Frames/{frame_id}/columns/{column}/domain")
    Call<FramesV3> columnDomain(@Path("frame_id") String frame_id, @Path("column") String column);

    /**
     * Return the specified column from a Frame.
     *   @param frame_id Name of Frame of interest
     *   @param column Name of column of interest
     *   @param row_offset Row offset to return
     *   @param row_count Number of rows to return
     *   @param column_offset Column offset to return
     *   @param full_column_count Number of full columns to return. The columns between full_column_count and column_count
     *                            will be returned without the data
     *   @param column_count Number of columns to return
     *   @param find_compatible_models Find and return compatible models?
     *   @param path File output path
     *   @param force Overwrite existing file
     *   @param num_parts Number of part files to use (1=single file,-1=automatic)
     *   @param compression Compression method (default none; gzip, bzip2 and snappy available depending on runtime
     *                      environment)
     *   @param separator Field separator (default ',')
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @GET("/3/Frames/{frame_id}/columns/{column}")
    Call<FramesV3> column(@Path("frame_id") String frame_id, @Path("column") String column, @Query("row_offset") long row_offset,
            @Query("row_count") int row_count, @Query("column_offset") int column_offset,
            @Query("full_column_count") int full_column_count, @Query("column_count") int column_count,
            @Query("find_compatible_models") boolean find_compatible_models, @Query("path") String path, @Query("force") boolean force,
            @Query("num_parts") int num_parts, @Query("compression") String compression, @Query("separator") byte separator,
            @Query("_exclude_fields") String _exclude_fields);

    @GET("/3/Frames/{frame_id}/columns/{column}")
    Call<FramesV3> column(@Path("frame_id") String frame_id, @Path("column") String column);

    /**
     * Return all the columns from a Frame.
     *   @param frame_id Name of Frame of interest
     *   @param column Name of column of interest
     *   @param row_offset Row offset to return
     *   @param row_count Number of rows to return
     *   @param column_offset Column offset to return
     *   @param full_column_count Number of full columns to return. The columns between full_column_count and column_count
     *                            will be returned without the data
     *   @param column_count Number of columns to return
     *   @param find_compatible_models Find and return compatible models?
     *   @param path File output path
     *   @param force Overwrite existing file
     *   @param num_parts Number of part files to use (1=single file,-1=automatic)
     *   @param compression Compression method (default none; gzip, bzip2 and snappy available depending on runtime
     *                      environment)
     *   @param separator Field separator (default ',')
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @GET("/3/Frames/{frame_id}/columns")
    Call<FramesV3> columns(@Path("frame_id") String frame_id, @Query("column") String column, @Query("row_offset") long row_offset,
            @Query("row_count") int row_count, @Query("column_offset") int column_offset,
            @Query("full_column_count") int full_column_count, @Query("column_count") int column_count,
            @Query("find_compatible_models") boolean find_compatible_models, @Query("path") String path, @Query("force") boolean force,
            @Query("num_parts") int num_parts, @Query("compression") String compression, @Query("separator") byte separator,
            @Query("_exclude_fields") String _exclude_fields);

    @GET("/3/Frames/{frame_id}/columns")
    Call<FramesV3> columns(@Path("frame_id") String frame_id);

    /**
     * Return a Frame, including the histograms, after forcing computation of rollups.
     *   @param frame_id Name of Frame of interest
     *   @param column Name of column of interest
     *   @param row_offset Row offset to return
     *   @param row_count Number of rows to return
     *   @param column_offset Column offset to return
     *   @param full_column_count Number of full columns to return. The columns between full_column_count and column_count
     *                            will be returned without the data
     *   @param column_count Number of columns to return
     *   @param find_compatible_models Find and return compatible models?
     *   @param path File output path
     *   @param force Overwrite existing file
     *   @param num_parts Number of part files to use (1=single file,-1=automatic)
     *   @param compression Compression method (default none; gzip, bzip2 and snappy available depending on runtime
     *                      environment)
     *   @param separator Field separator (default ',')
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @GET("/3/Frames/{frame_id}/summary")
    Call<FramesV3> summary(@Path("frame_id") String frame_id, @Query("column") String column, @Query("row_offset") long row_offset,
            @Query("row_count") int row_count, @Query("column_offset") int column_offset,
            @Query("full_column_count") int full_column_count, @Query("column_count") int column_count,
            @Query("find_compatible_models") boolean find_compatible_models, @Query("path") String path, @Query("force") boolean force,
            @Query("num_parts") int num_parts, @Query("compression") String compression, @Query("separator") byte separator,
            @Query("_exclude_fields") String _exclude_fields);

    @GET("/3/Frames/{frame_id}/summary")
    Call<FramesV3> summary(@Path("frame_id") String frame_id);

    /**
     * Return a basic info about Frame to fill client Rapid expression cache.
     *   @param frame_id Name of Frame of interest
     *   @param column Name of column of interest
     *   @param row_offset Row offset to return
     *   @param row_count Number of rows to return
     *   @param column_offset Column offset to return
     *   @param full_column_count Number of full columns to return. The columns between full_column_count and column_count
     *                            will be returned without the data
     *   @param column_count Number of columns to return
     *   @param find_compatible_models Find and return compatible models?
     *   @param path File output path
     *   @param force Overwrite existing file
     *   @param num_parts Number of part files to use (1=single file,-1=automatic)
     *   @param compression Compression method (default none; gzip, bzip2 and snappy available depending on runtime
     *                      environment)
     *   @param separator Field separator (default ',')
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @GET("/3/Frames/{frame_id}/light")
    Call<FramesV3> fetchLight(@Path("frame_id") String frame_id, @Query("column") String column, @Query("row_offset") long row_offset,
            @Query("row_count") int row_count, @Query("column_offset") int column_offset,
            @Query("full_column_count") int full_column_count, @Query("column_count") int column_count,
            @Query("find_compatible_models") boolean find_compatible_models, @Query("path") String path, @Query("force") boolean force,
            @Query("num_parts") int num_parts, @Query("compression") String compression, @Query("separator") byte separator,
            @Query("_exclude_fields") String _exclude_fields);

    @GET("/3/Frames/{frame_id}/light")
    Call<FramesV3> fetchLight(@Path("frame_id") String frame_id);

    /**
     * Return the specified Frame.
     *   @param frame_id Name of Frame of interest
     *   @param column Name of column of interest
     *   @param row_offset Row offset to return
     *   @param row_count Number of rows to return
     *   @param column_offset Column offset to return
     *   @param full_column_count Number of full columns to return. The columns between full_column_count and column_count
     *                            will be returned without the data
     *   @param column_count Number of columns to return
     *   @param find_compatible_models Find and return compatible models?
     *   @param path File output path
     *   @param force Overwrite existing file
     *   @param num_parts Number of part files to use (1=single file,-1=automatic)
     *   @param compression Compression method (default none; gzip, bzip2 and snappy available depending on runtime
     *                      environment)
     *   @param separator Field separator (default ',')
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @GET("/3/Frames/{frame_id}")
    Call<FramesV3> fetch(@Path("frame_id") String frame_id, @Query("column") String column, @Query("row_offset") long row_offset,
            @Query("row_count") int row_count, @Query("column_offset") int column_offset,
            @Query("full_column_count") int full_column_count, @Query("column_count") int column_count,
            @Query("find_compatible_models") boolean find_compatible_models, @Query("path") String path, @Query("force") boolean force,
            @Query("num_parts") int num_parts, @Query("compression") String compression, @Query("separator") byte separator,
            @Query("_exclude_fields") String _exclude_fields);

    @GET("/3/Frames/{frame_id}")
    Call<FramesV3> fetch(@Path("frame_id") String frame_id);

    /**
     * Return all Frames in the H2O distributed K/V store.
     *   @param frame_id Name of Frame of interest
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @GET("/3/Frames")
    Call<FramesListV3> list(@Query("frame_id") String frame_id, @Query("_exclude_fields") String _exclude_fields);

    @GET("/3/Frames")
    Call<FramesListV3> list();

    /**
     * Delete the specified Frame from the H2O distributed K/V store.
     *   @param frame_id Name of Frame of interest
     *   @param column Name of column of interest
     *   @param row_offset Row offset to return
     *   @param row_count Number of rows to return
     *   @param column_offset Column offset to return
     *   @param full_column_count Number of full columns to return. The columns between full_column_count and column_count
     *                            will be returned without the data
     *   @param column_count Number of columns to return
     *   @param find_compatible_models Find and return compatible models?
     *   @param path File output path
     *   @param force Overwrite existing file
     *   @param num_parts Number of part files to use (1=single file,-1=automatic)
     *   @param compression Compression method (default none; gzip, bzip2 and snappy available depending on runtime
     *                      environment)
     *   @param separator Field separator (default ',')
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @DELETE("/3/Frames/{frame_id}")
    Call<FramesV3> delete(@Path("frame_id") String frame_id, @Field("column") String column, @Field("row_offset") long row_offset,
            @Field("row_count") int row_count, @Field("column_offset") int column_offset,
            @Field("full_column_count") int full_column_count, @Field("column_count") int column_count,
            @Field("find_compatible_models") boolean find_compatible_models, @Field("path") String path, @Field("force") boolean force,
            @Field("num_parts") int num_parts, @Field("compression") String compression, @Field("separator") byte separator,
            @Field("_exclude_fields") String _exclude_fields);

    @DELETE("/3/Frames/{frame_id}")
    Call<FramesV3> delete(@Path("frame_id") String frame_id);

    /**
     * Delete all Frames from the H2O distributed K/V store.
     *   @param frame_id Name of Frame of interest
     *   @param column Name of column of interest
     *   @param row_offset Row offset to return
     *   @param row_count Number of rows to return
     *   @param column_offset Column offset to return
     *   @param full_column_count Number of full columns to return. The columns between full_column_count and column_count
     *                            will be returned without the data
     *   @param column_count Number of columns to return
     *   @param find_compatible_models Find and return compatible models?
     *   @param path File output path
     *   @param force Overwrite existing file
     *   @param num_parts Number of part files to use (1=single file,-1=automatic)
     *   @param compression Compression method (default none; gzip, bzip2 and snappy available depending on runtime
     *                      environment)
     *   @param separator Field separator (default ',')
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @DELETE("/3/Frames")
    Call<FramesV3> deleteAll(@Field("frame_id") String frame_id, @Field("column") String column, @Field("row_offset") long row_offset,
            @Field("row_count") int row_count, @Field("column_offset") int column_offset,
            @Field("full_column_count") int full_column_count, @Field("column_count") int column_count,
            @Field("find_compatible_models") boolean find_compatible_models, @Field("path") String path, @Field("force") boolean force,
            @Field("num_parts") int num_parts, @Field("compression") String compression, @Field("separator") byte separator,
            @Field("_exclude_fields") String _exclude_fields);

    @DELETE("/3/Frames")
    Call<FramesV3> deleteAll();

    /**
     * Create frame with random (uniformly distributed) data. You can specify how many columns of each type to make; and
     * what the desired range for each column type.
     *   @param dest Id for the frame to be created.
     *   @param seed Random number seed that determines the random values.
     *   @param nrows Number of rows.
     *   @param ncols_real Number of real-valued columns. Values in these columns will be uniformly distributed between
     *                     real_lb and real_ub.
     *   @param ncols_int Number of integer columns.
     *   @param ncols_enum Number of enum (categorical) columns.
     *   @param ncols_bool Number of boolean (binary) columns.
     *   @param ncols_str Number of string columns.
     *   @param ncols_time Number of time columns.
     *   @param real_lb Lower bound for the range of the real-valued columns.
     *   @param real_ub Upper bound for the range of the real-valued columns.
     *   @param int_lb Lower bound for the range of integer columns.
     *   @param int_ub Upper bound for the range of integer columns.
     *   @param enum_nlevels Number of levels (categories) for the enum columns.
     *   @param bool_p Fraction of ones in each boolean (binary) column.
     *   @param time_lb Lower bound for the range of time columns (in ms since the epoch).
     *   @param time_ub Upper bound for the range of time columns (in ms since the epoch).
     *   @param str_length Length of generated strings in string columns.
     *   @param missing_fraction Fraction of missing values.
     *   @param response_type Type of the response column to add.
     *   @param response_lb Lower bound for the response variable (real/int/time types).
     *   @param response_ub Upper bound for the response variable (real/int/time types).
     *   @param response_p Frequency of 1s for the bool (binary) response column.
     *   @param response_nlevels Number of categorical levels for the enum response column.
     *   @param _fields Filter on the set of output fields: if you set _fields="foo,bar,baz", then only those fields will
     *                  be included in the output; or you can specify _fields="-goo,gee" to include all fields except goo
     *                  and gee. If the result contains nested data structures, then you can refer to the fields within
     *                  those structures as well. For example if you specify _fields="foo(oof),bar(-rab)", then only
     *                  fields foo and bar will be included, and within foo there will be only field oof, whereas within
     *                  bar all fields except rab will be reported.
     */
    @FormUrlEncoded
    @POST("/4/Frames/$simple")
    Call<JobV4> createSimpleFrame(@Field("dest") String dest, @Field("seed") long seed, @Field("nrows") int nrows,
            @Field("ncols_real") int ncols_real, @Field("ncols_int") int ncols_int, @Field("ncols_enum") int ncols_enum,
            @Field("ncols_bool") int ncols_bool, @Field("ncols_str") int ncols_str, @Field("ncols_time") int ncols_time,
            @Field("real_lb") double real_lb, @Field("real_ub") double real_ub, @Field("int_lb") int int_lb, @Field("int_ub") int int_ub,
            @Field("enum_nlevels") int enum_nlevels, @Field("bool_p") double bool_p, @Field("time_lb") long time_lb,
            @Field("time_ub") long time_ub, @Field("str_length") int str_length, @Field("missing_fraction") double missing_fraction,
            @Field("response_type") SimpleRecipeResponseType response_type, @Field("response_lb") double response_lb,
            @Field("response_ub") double response_ub, @Field("response_p") double response_p,
            @Field("response_nlevels") int response_nlevels, @Field("_fields") String _fields);

    @FormUrlEncoded
    @POST("/4/Frames/$simple")
    Call<JobV4> createSimpleFrame();

}
