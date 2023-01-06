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

public interface Interaction {

    /**
     * Create interactions between categorical columns.
     *   @param dest destination key
     *   @param source_frame Input data frame
     *   @param factor_columns Factor columns
     *   @param pairwise Whether to create pairwise quadratic interactions between factors (otherwise create one higher-
     *                   order interaction). Only applicable if there are 3 or more factors.
     *   @param max_factors Max. number of factor levels in pair-wise interaction terms (if enforced, one extra catch-all
     *                      factor will be made)
     *   @param min_occurrence Min. occurrence threshold for factor levels in pair-wise interaction terms
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @FormUrlEncoded
    @POST("/3/Interaction")
    Call<JobV3> run(@Field("dest") String dest, @Field("source_frame") String source_frame,
            @Field("factor_columns") String[] factor_columns, @Field("pairwise") boolean pairwise, @Field("max_factors") int max_factors,
            @Field("min_occurrence") int min_occurrence, @Field("_exclude_fields") String _exclude_fields);

    @FormUrlEncoded
    @POST("/3/Interaction")
    Call<JobV3> run(@Field("max_factors") int max_factors);

}
