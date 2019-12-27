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

import org.codelibs.fione.h2o.bindings.pojos.FrameKeyV3;
import org.codelibs.fione.h2o.bindings.pojos.H2otargetencodingTargetEncoderDataLeakageHandlingStrategy;

import retrofit2.Call;
import retrofit2.http.GET;
import retrofit2.http.Query;

public interface TargetEncoderTransform {

    /**
     * Transform using give TargetEncoderModel
     *   @param model Target Encoder model to use.
     *   @param seed Seed value
     *   @param data_leakage_handling Data leakage handling strategy.
     *   @param noise Noise
     *   @param frame Frame to transform
     *   @param blending Enables or disables blending
     *   @param inflection_point Inflection point
     *   @param smoothing Smoothing
     */
    @GET("/3/TargetEncoderTransform")
    Call<FrameKeyV3> transform(@Query("model") String model, @Query("seed") long seed,
            @Query("data_leakage_handling") H2otargetencodingTargetEncoderDataLeakageHandlingStrategy data_leakage_handling,
            @Query("noise") double noise, @Query("frame") String frame, @Query("blending") boolean blending,
            @Query("inflection_point") double inflection_point, @Query("smoothing") double smoothing);

    @GET("/3/TargetEncoderTransform")
    Call<FrameKeyV3> transform();

}
