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

import org.codelibs.fione.h2o.bindings.pojos.FrameChunksV3;

import retrofit2.Call;
import retrofit2.http.GET;
import retrofit2.http.Path;

public interface FrameChunks {

    /**
     * Return information about chunks for a given frame.
     *   @param frame_id ID of a given frame
     */
    @GET("/3/FrameChunks/{frame_id}")
    Call<FrameChunksV3> fetch(@Path("frame_id") String frame_id);

}
