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

import org.codelibs.fione.h2o.bindings.pojos.CloudV3;

import retrofit2.Call;
import retrofit2.http.Field;
import retrofit2.http.GET;
import retrofit2.http.HEAD;
import retrofit2.http.Query;

public interface Cloud {

    /**
     * Determine the status of the nodes in the H2O cloud.
     *   @param skip_ticks skip_ticks
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @GET("/3/Cloud")
    Call<CloudV3> status(@Query("skip_ticks") boolean skip_ticks, @Query("_exclude_fields") String _exclude_fields);

    @GET("/3/Cloud")
    Call<CloudV3> status();

    /**
     * Determine the status of the nodes in the H2O cloud.
     *   @param skip_ticks skip_ticks
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @HEAD("/3/Cloud")
    Call<CloudV3> head(@Field("skip_ticks") boolean skip_ticks, @Field("_exclude_fields") String _exclude_fields);

    @HEAD("/3/Cloud")
    Call<CloudV3> head();

}
