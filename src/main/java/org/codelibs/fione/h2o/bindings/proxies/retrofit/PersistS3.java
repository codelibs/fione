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

import org.codelibs.fione.h2o.bindings.pojos.PersistS3CredentialsV3;

import retrofit2.Call;
import retrofit2.http.Field;
import retrofit2.http.FormUrlEncoded;
import retrofit2.http.POST;

public interface PersistS3 {

    /**
     * Set Amazon S3 credentials (Secret Key ID, Secret Access Key)
     *   @param secret_key_id S3 Secret Key ID
     *   @param secret_access_key S3 Secret Key
     *   @param session_token S3 Session token
     */
    @FormUrlEncoded
    @POST("/3/PersistS3")
    Call<PersistS3CredentialsV3> setS3Credentials(@Field("secret_key_id") String secret_key_id,
            @Field("secret_access_key") String secret_access_key, @Field("session_token") String session_token);

    @FormUrlEncoded
    @POST("/3/PersistS3")
    Call<PersistS3CredentialsV3> setS3Credentials(@Field("secret_key_id") String secret_key_id,
            @Field("secret_access_key") String secret_access_key);

}
