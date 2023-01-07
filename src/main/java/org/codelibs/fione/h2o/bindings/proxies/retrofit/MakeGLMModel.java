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

import org.codelibs.fione.h2o.bindings.pojos.GLMModelV3;

import retrofit2.Call;
import retrofit2.http.Field;
import retrofit2.http.FormUrlEncoded;
import retrofit2.http.POST;

public interface MakeGLMModel {

    /**
     * Make a new GLM model based on existing one
     *   @param model source model
     *   @param dest destination key
     *   @param names coefficient names
     *   @param beta new glm coefficients
     *   @param threshold decision threshold for label-generation
     */
    @FormUrlEncoded
    @POST("/3/MakeGLMModel")
    Call<GLMModelV3> make_model(@Field("model") String model, @Field("dest") String dest, @Field("names") String[] names,
            @Field("beta") double[] beta, @Field("threshold") float threshold);

    @FormUrlEncoded
    @POST("/3/MakeGLMModel")
    Call<GLMModelV3> make_model(@Field("model") String model, @Field("names") String[] names, @Field("beta") double[] beta);

}
