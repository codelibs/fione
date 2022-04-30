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

import org.codelibs.fione.h2o.bindings.pojos.ApiSaveToHiveTableHandlerHiveFrameSaverFormat;
import org.codelibs.fione.h2o.bindings.pojos.SaveToHiveTableV3;

import retrofit2.Call;
import retrofit2.http.Field;
import retrofit2.http.FormUrlEncoded;
import retrofit2.http.POST;

public interface SaveToHiveTable {

    /**
     * Save an H2O Frame contents into a Hive table.
     *   @param frame_id H2O Frame ID
     *   @param jdbc_url HIVE JDBC URL
     *   @param table_name Name of table to save data to.
     *   @param table_path HDFS Path to where the table should be stored.
     *   @param format Storage format of the created table.
     *   @param tmp_path HDFS Path where to store temporary data.
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @FormUrlEncoded
    @POST("/3/SaveToHiveTable")
    Call<SaveToHiveTableV3> saveToHiveTable(@Field("frame_id") String frame_id, @Field("jdbc_url") String jdbc_url,
            @Field("table_name") String table_name, @Field("table_path") String table_path,
            @Field("format") ApiSaveToHiveTableHandlerHiveFrameSaverFormat format, @Field("tmp_path") String tmp_path,
            @Field("_exclude_fields") String _exclude_fields);

    @FormUrlEncoded
    @POST("/3/SaveToHiveTable")
    Call<SaveToHiveTableV3> saveToHiveTable(@Field("frame_id") String frame_id, @Field("jdbc_url") String jdbc_url,
            @Field("table_name") String table_name);

}
