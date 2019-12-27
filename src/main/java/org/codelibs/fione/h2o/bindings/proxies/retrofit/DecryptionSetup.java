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

import org.codelibs.fione.h2o.bindings.pojos.DecryptionSetupV3;

import retrofit2.Call;
import retrofit2.http.Field;
import retrofit2.http.FormUrlEncoded;
import retrofit2.http.POST;

public interface DecryptionSetup {

    /**
     * Install a decryption tool for parsing of encrypted data.
     *   @param decrypt_tool_id Target key for the Decryption Tool
     *   @param decrypt_impl Implementation of the Decryption Tool
     *   @param keystore_id Location of Java Keystore
     *   @param keystore_type Keystore type
     *   @param key_alias Key alias
     *   @param password Key password
     *   @param cipher_spec Specification of the cipher (and padding)
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @FormUrlEncoded
    @POST("/3/DecryptionSetup")
    Call<DecryptionSetupV3> setupDecryption(@Field("decrypt_tool_id") String decrypt_tool_id, @Field("decrypt_impl") String decrypt_impl,
            @Field("keystore_id") String keystore_id, @Field("keystore_type") String keystore_type, @Field("key_alias") String key_alias,
            @Field("password") String password, @Field("cipher_spec") String cipher_spec, @Field("_exclude_fields") String _exclude_fields);

    @FormUrlEncoded
    @POST("/3/DecryptionSetup")
    Call<DecryptionSetupV3> setupDecryption();

}
