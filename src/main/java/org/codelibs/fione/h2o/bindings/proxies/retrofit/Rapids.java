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

import org.codelibs.fione.h2o.bindings.pojos.RapidsHelpV3;
import org.codelibs.fione.h2o.bindings.pojos.RapidsSchemaV3;

import retrofit2.Call;
import retrofit2.http.Field;
import retrofit2.http.FormUrlEncoded;
import retrofit2.http.GET;
import retrofit2.http.POST;

public interface Rapids {

    /**
     * Execute an Rapids AstRoot.
     *   @param ast A Rapids AstRoot expression
     *   @param session_id Session key
     *   @param id [DEPRECATED] Key name to assign Frame results
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @FormUrlEncoded
    @POST("/99/Rapids")
    Call<RapidsSchemaV3> rapidsExec(@Field("ast") String ast, @Field("session_id") String session_id, @Field("id") String id,
            @Field("_exclude_fields") String _exclude_fields);

    @FormUrlEncoded
    @POST("/99/Rapids")
    Call<RapidsSchemaV3> rapidsExec(@Field("ast") String ast);

    /**
     * Produce help for Rapids AstRoot language.
     */
    @GET("/99/Rapids/help")
    Call<RapidsHelpV3> genHelp();

}
