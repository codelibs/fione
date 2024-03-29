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

import org.codelibs.fione.h2o.bindings.pojos.ModelsInfoV4;

import retrofit2.Call;
import retrofit2.http.GET;
import retrofit2.http.Query;

public interface Modelsinfo {

    /**
     * Return basic information about all models available to train.
     *   @param __schema Url describing the schema of the current object.
     */
    @GET("/4/modelsinfo")
    Call<ModelsInfoV4> modelsInfo(@Query("__schema") String __schema);

    @GET("/4/modelsinfo")
    Call<ModelsInfoV4> modelsInfo();

}
