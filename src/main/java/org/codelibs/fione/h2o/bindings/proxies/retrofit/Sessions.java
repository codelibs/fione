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
package org.codelibs.fione.h2o.bindings.proxies.retrofit;

import org.codelibs.fione.h2o.bindings.pojos.InitIDV3;
import org.codelibs.fione.h2o.bindings.pojos.SessionIdV4;

import retrofit2.Call;
import retrofit2.http.DELETE;
import retrofit2.http.Field;
import retrofit2.http.FormUrlEncoded;
import retrofit2.http.POST;
import retrofit2.http.Path;

public interface Sessions {

    /**
     * Start a new Rapids session, and return the session id.
     *   @param _fields Filter on the set of output fields: if you set _fields="foo,bar,baz", then only those fields will
     *                  be included in the output; or you can specify _fields="-goo,gee" to include all fields except goo
     *                  and gee. If the result contains nested data structures, then you can refer to the fields within
     *                  those structures as well. For example if you specify _fields="foo(oof),bar(-rab)", then only
     *                  fields foo and bar will be included, and within foo there will be only field oof, whereas within
     *                  bar all fields except rab will be reported.
     */
    @FormUrlEncoded
    @POST("/4/sessions")
    Call<SessionIdV4> newSession4(@Field("_fields") String _fields);

    @FormUrlEncoded
    @POST("/4/sessions")
    Call<SessionIdV4> newSession4();

    /**
     * Close the Rapids session.
     *   @param session_key Session ID
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @DELETE("/4/sessions/{session_key}")
    Call<InitIDV3> endSession(@Path("session_key") String session_key, @Field("_exclude_fields") String _exclude_fields);

    @DELETE("/4/sessions/{session_key}")
    Call<InitIDV3> endSession(@Path("session_key") String session_key);

}
