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

import org.codelibs.fione.h2o.bindings.pojos.SplitFrameV3;

import retrofit2.Call;
import retrofit2.http.Field;
import retrofit2.http.FormUrlEncoded;
import retrofit2.http.POST;

public interface SplitFrame {

    /**
     * Split an H2O Frame.
     *   @param key Job Key
     *   @param dataset Dataset
     *   @param ratios Split ratios - resulting number of split is ratios.length+1
     *   @param destination_frames Destination keys for each output frame split.
     */
    @FormUrlEncoded
    @POST("/3/SplitFrame")
    Call<SplitFrameV3> run(@Field("key") String key, @Field("dataset") String dataset, @Field("ratios") double[] ratios,
            @Field("destination_frames") String[] destination_frames);

    @FormUrlEncoded
    @POST("/3/SplitFrame")
    Call<SplitFrameV3> run();

}
