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

import org.codelibs.fione.h2o.bindings.pojos.InitIDV3;

import retrofit2.Call;
import retrofit2.http.DELETE;
import retrofit2.http.Field;
import retrofit2.http.GET;
import retrofit2.http.Query;

public interface InitID {

    /**
     * Issue a new session ID.
     *   @param session_key Session ID
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @GET("/3/InitID")
    Call<InitIDV3> startSession(@Query("session_key") String session_key, @Query("_exclude_fields") String _exclude_fields);

    @GET("/3/InitID")
    Call<InitIDV3> startSession();

    /**
     * End a session.
     *   @param session_key Session ID
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @DELETE("/3/InitID")
    Call<InitIDV3> endSession(@Field("session_key") String session_key, @Field("_exclude_fields") String _exclude_fields);

    @DELETE("/3/InitID")
    Call<InitIDV3> endSession();

}
