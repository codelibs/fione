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

import org.codelibs.fione.h2o.bindings.pojos.TabulateV3;

import retrofit2.Call;
import retrofit2.http.Field;
import retrofit2.http.FormUrlEncoded;
import retrofit2.http.POST;

public interface Tabulate {

    /**
     * Tabulate one column vs another.
     *   @param dataset Dataset
     *   @param predictor Predictor
     *   @param response Response
     *   @param weight Observation weights (optional)
     *   @param nbins_predictor Number of bins for predictor column
     *   @param nbins_response Number of bins for response column
     */
    @FormUrlEncoded
    @POST("/99/Tabulate")
    Call<TabulateV3> run(@Field("dataset") String dataset, @Field("predictor") String predictor, @Field("response") String response,
            @Field("weight") String weight, @Field("nbins_predictor") int nbins_predictor, @Field("nbins_response") int nbins_response);

    @FormUrlEncoded
    @POST("/99/Tabulate")
    Call<TabulateV3> run(@Field("dataset") String dataset, @Field("predictor") String predictor, @Field("response") String response);

}
