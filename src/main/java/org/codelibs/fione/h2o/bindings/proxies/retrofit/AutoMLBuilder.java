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

import java.util.HashMap;
import java.util.Map;

import org.codelibs.fione.h2o.bindings.pojos.AutoMLBuildControlV99;
import org.codelibs.fione.h2o.bindings.pojos.AutoMLBuildModelsV99;
import org.codelibs.fione.h2o.bindings.pojos.AutoMLBuildSpecV99;
import org.codelibs.fione.h2o.bindings.pojos.AutoMLInputV99;

import retrofit2.Call;
import retrofit2.http.Body;
import retrofit2.http.FormUrlEncoded;
import retrofit2.http.Headers;
import retrofit2.http.POST;

public interface AutoMLBuilder {

    //    @FormUrlEncoded
    //    @POST("/99/AutoMLBuilder")
    //    Call<AutoMLBuildSpecV99> build(@Field("build_control") AutoMLBuildControlV99 build_control,
    //            @Field("input_spec") AutoMLInputV99 input_spec, @Field("build_models") AutoMLBuildModelsV99 build_models);
    @Headers({ "Accept: application/json", "Content-type: application/json" })
    @POST("/99/AutoMLBuilder")
    Call<AutoMLBuildSpecV99> build(@Body Map<String, Object> body);

    /**
     * Start an AutoML build process.
     *   @param buildControl Specification of overall controls for the AutoML build process.
     *   @param inputSpec Specification of the input data for the AutoML build process.
     *   @param buildModels If present, specifies details of how to train models.
     */
    default Call<AutoMLBuildSpecV99> build(final AutoMLBuildControlV99 buildControl, final AutoMLInputV99 inputSpec,
            final AutoMLBuildModelsV99 buildModels) {
        final Map<String, Object> body = new HashMap<>();
        body.put("build_control", buildControl);
        body.put("input_spec", inputSpec);
        body.put("build_models", buildModels);
        return build(body);
    }

    @FormUrlEncoded
    @POST("/99/AutoMLBuilder")
    Call<AutoMLBuildSpecV99> build();

}
