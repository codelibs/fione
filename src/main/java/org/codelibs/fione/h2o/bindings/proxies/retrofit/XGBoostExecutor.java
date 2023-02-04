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

import org.codelibs.fione.h2o.bindings.pojos.StreamingSchema;
import org.codelibs.fione.h2o.bindings.pojos.XGBoostExecRespV3;

import retrofit2.Call;
import retrofit2.http.Field;
import retrofit2.http.FormUrlEncoded;
import retrofit2.http.POST;

public interface XGBoostExecutor {

    /**
     * Remote XGBoost execution - init
     *   @param key Identifier
     *   @param data Arbitrary request data stored as Base64 encoded binary
     */
    @FormUrlEncoded
    @POST("/3/XGBoostExecutor.init")
    Call<XGBoostExecRespV3> init(@Field("key") String key, @Field("data") String data);

    @FormUrlEncoded
    @POST("/3/XGBoostExecutor.init")
    Call<XGBoostExecRespV3> init();

    /**
     * Remote XGBoost execution - setup
     *   @param key Identifier
     *   @param data Arbitrary request data stored as Base64 encoded binary
     */
    @FormUrlEncoded
    @POST("/3/XGBoostExecutor.setup")
    Call<StreamingSchema> setup(@Field("key") String key, @Field("data") String data);

    @FormUrlEncoded
    @POST("/3/XGBoostExecutor.setup")
    Call<StreamingSchema> setup();

    /**
     * Remote XGBoost execution - update
     *   @param key Identifier
     *   @param data Arbitrary request data stored as Base64 encoded binary
     */
    @FormUrlEncoded
    @POST("/3/XGBoostExecutor.update")
    Call<XGBoostExecRespV3> update(@Field("key") String key, @Field("data") String data);

    @FormUrlEncoded
    @POST("/3/XGBoostExecutor.update")
    Call<XGBoostExecRespV3> update();

    /**
     * Remote XGBoost execution - get booster
     *   @param key Identifier
     *   @param data Arbitrary request data stored as Base64 encoded binary
     */
    @FormUrlEncoded
    @POST("/3/XGBoostExecutor.getBooster")
    Call<StreamingSchema> getBooster(@Field("key") String key, @Field("data") String data);

    @FormUrlEncoded
    @POST("/3/XGBoostExecutor.getBooster")
    Call<StreamingSchema> getBooster();

    /**
     * Remote XGBoost execution - cleanup
     *   @param key Identifier
     *   @param data Arbitrary request data stored as Base64 encoded binary
     */
    @FormUrlEncoded
    @POST("/3/XGBoostExecutor.cleanup")
    Call<XGBoostExecRespV3> cleanup(@Field("key") String key, @Field("data") String data);

    @FormUrlEncoded
    @POST("/3/XGBoostExecutor.cleanup")
    Call<XGBoostExecRespV3> cleanup();

}
