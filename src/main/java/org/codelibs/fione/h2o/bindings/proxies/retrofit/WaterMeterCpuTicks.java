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

import org.codelibs.fione.h2o.bindings.pojos.WaterMeterCpuTicksV3;

import retrofit2.Call;
import retrofit2.http.GET;
import retrofit2.http.Path;
import retrofit2.http.Query;

public interface WaterMeterCpuTicks {

    /**
     * Return a CPU usage snapshot of all cores of all nodes in the H2O cluster.
     *   @param nodeidx Index of node to query ticks for (0-based)
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @GET("/3/WaterMeterCpuTicks/{nodeidx}")
    Call<WaterMeterCpuTicksV3> fetch(@Path("nodeidx") int nodeidx, @Query("_exclude_fields") String _exclude_fields);

    @GET("/3/WaterMeterCpuTicks/{nodeidx}")
    Call<WaterMeterCpuTicksV3> fetch(@Path("nodeidx") int nodeidx);

}
