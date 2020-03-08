/*
 * Copyright 2012-2020 CodeLibs Project and the Others.
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

import org.codelibs.fione.h2o.bindings.pojos.RemoveAllV3;
import org.codelibs.fione.h2o.bindings.pojos.RemoveV3;

import retrofit2.Call;
import retrofit2.http.DELETE;
import retrofit2.http.Field;
import retrofit2.http.Path;

public interface DKV {

    /**
     * Remove an arbitrary key from the H2O distributed K/V store.
     *   @param key Object to be removed.
     *   @param cascade If true, removal operation will cascade down the object tree.
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @DELETE("/3/DKV/{key}")
    Call<RemoveV3> remove(@Path("key") String key, @Field("cascade") boolean cascade, @Field("_exclude_fields") String _exclude_fields);

    @DELETE("/3/DKV/{key}")
    Call<RemoveV3> remove(@Path("key") String key);

    /**
     * Remove all keys from the H2O distributed K/V store.
     *   @param retained_keys Keys of the models to retain
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @DELETE("/3/DKV")
    Call<RemoveAllV3> removeAll(@Field("retained_keys") String[] retained_keys, @Field("_exclude_fields") String _exclude_fields);

    @DELETE("/3/DKV")
    Call<RemoveAllV3> removeAll();

}
