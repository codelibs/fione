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

import org.codelibs.fione.h2o.bindings.pojos.FrameKeyV3;

import retrofit2.Call;
import retrofit2.http.GET;
import retrofit2.http.Query;

public interface TargetEncoderTransform {

    /**
     * Transform using give TargetEncoderModel
     *   @param model Target Encoder model to use.
     *   @param frame Frame to transform.
     *   @param as_training Force encoding mode for training data: when using a leakage handling strategy different from
     *                      None, training data should be transformed with this flag set to true (Defaults to false).
     *   @param blending Enables or disables blending. Defaults to the value assigned at model creation.
     *   @param inflection_point Inflection point. Defaults to the value assigned at model creation.
     *   @param smoothing Smoothing. Defaults to the value assigned at model creation.
     *   @param noise Noise. Defaults to the value assigned at model creation.
     */
    @GET("/3/TargetEncoderTransform")
    Call<FrameKeyV3> transform(@Query("model") String model, @Query("frame") String frame, @Query("as_training") boolean as_training,
            @Query("blending") boolean blending, @Query("inflection_point") double inflection_point, @Query("smoothing") double smoothing,
            @Query("noise") double noise);

    @GET("/3/TargetEncoderTransform")
    Call<FrameKeyV3> transform();

}
