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
package org.codelibs.fione.h2o.bindings.proxies.retrofit;

import org.codelibs.fione.h2o.bindings.pojos.JobV3;

import retrofit2.Call;
import retrofit2.http.Field;
import retrofit2.http.FormUrlEncoded;
import retrofit2.http.POST;

public interface ImportSQLTable {

    /**
     * Import SQL table into an H2O Frame.
     *   @param connection_url connection_url
     *   @param table table
     *   @param select_query select_query
     *   @param use_temp_table use_temp_table
     *   @param temp_table_name temp_table_name
     *   @param username username
     *   @param password password
     *   @param columns columns
     *   @param fetch_mode Mode for data loading. All modes may not be supported by all databases.
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @FormUrlEncoded
    @POST("/99/ImportSQLTable")
    Call<JobV3> importSQLTable(@Field("connection_url") String connection_url, @Field("table") String table,
            @Field("select_query") String select_query, @Field("use_temp_table") String use_temp_table,
            @Field("temp_table_name") String temp_table_name, @Field("username") String username, @Field("password") String password,
            @Field("columns") String columns, @Field("fetch_mode") String fetch_mode, @Field("_exclude_fields") String _exclude_fields);

    @FormUrlEncoded
    @POST("/99/ImportSQLTable")
    Call<JobV3> importSQLTable(@Field("connection_url") String connection_url, @Field("username") String username,
            @Field("password") String password);

}
