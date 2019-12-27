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

import org.codelibs.fione.h2o.bindings.pojos.JobV3;

import retrofit2.Call;
import retrofit2.http.Field;
import retrofit2.http.FormUrlEncoded;
import retrofit2.http.POST;

public interface DCTTransformer {

    /**
     * Row-by-row discrete cosine transforms in 1D, 2D and 3D.
     *   @param dataset Dataset
     *   @param destination_frame Destination Frame ID
     *   @param dimensions Dimensions of the input array: Height, Width, Depth (Nx1x1 for 1D, NxMx1 for 2D)
     *   @param inverse Whether to do the inverse transform
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @FormUrlEncoded
    @POST("/99/DCTTransformer")
    Call<JobV3> run(@Field("dataset") String dataset, @Field("destination_frame") String destination_frame,
            @Field("dimensions") int[] dimensions, @Field("inverse") boolean inverse, @Field("_exclude_fields") String _exclude_fields);

    @FormUrlEncoded
    @POST("/99/DCTTransformer")
    Call<JobV3> run(@Field("dataset") String dataset, @Field("dimensions") int[] dimensions);

}
