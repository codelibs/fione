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

import org.codelibs.fione.h2o.bindings.pojos.DataInfoFrameV3;

import retrofit2.Call;
import retrofit2.http.Field;
import retrofit2.http.FormUrlEncoded;
import retrofit2.http.POST;

public interface DataInfoFrame {

    /**
     * Test only
     *   @param frame input frame
     *   @param interactions interactions
     *   @param use_all use all factor levels
     *   @param standardize standardize
     *   @param interactions_only interactions only returned
     */
    @FormUrlEncoded
    @POST("/3/DataInfoFrame")
    Call<DataInfoFrameV3> getDataInfoFrame(@Field("frame") String frame, @Field("interactions") String[] interactions,
            @Field("use_all") boolean use_all, @Field("standardize") boolean standardize,
            @Field("interactions_only") boolean interactions_only);

    @FormUrlEncoded
    @POST("/3/DataInfoFrame")
    Call<DataInfoFrameV3> getDataInfoFrame();

}
