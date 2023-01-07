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

public interface MissingInserter {

    /**
     * Insert missing values.
     *   @param dataset dataset
     *   @param fraction Fraction of data to replace with a missing value
     *   @param seed Seed
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @FormUrlEncoded
    @POST("/3/MissingInserter")
    Call<JobV3> run(@Field("dataset") String dataset, @Field("fraction") double fraction, @Field("seed") long seed,
            @Field("_exclude_fields") String _exclude_fields);

    @FormUrlEncoded
    @POST("/3/MissingInserter")
    Call<JobV3> run(@Field("dataset") String dataset, @Field("fraction") double fraction);

}
