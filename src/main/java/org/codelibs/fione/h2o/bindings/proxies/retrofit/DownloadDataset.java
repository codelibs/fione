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

import org.codelibs.fione.h2o.bindings.pojos.DownloadDataV3;

import retrofit2.Call;
import retrofit2.http.GET;
import retrofit2.http.Query;

public interface DownloadDataset {

    /**
     * Download dataset as a CSV.
     *   @param frame_id Frame to download
     *   @param hex_string Emit double values in a machine readable lossless format with Double.toHexString().
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @GET("/3/DownloadDataset")
    Call<DownloadDataV3> fetch(@Query("frame_id") String frame_id, @Query("hex_string") boolean hex_string,
            @Query("_exclude_fields") String _exclude_fields);

    @GET("/3/DownloadDataset")
    Call<DownloadDataV3> fetch(@Query("frame_id") String frame_id);

    /**
     * Download dataset as a CSV.
     *   @param frame_id Frame to download
     *   @param hex_string Emit double values in a machine readable lossless format with Double.toHexString().
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @GET("/3/DownloadDataset.bin")
    Call<DownloadDataV3> fetchStreaming(@Query("frame_id") String frame_id, @Query("hex_string") boolean hex_string,
            @Query("_exclude_fields") String _exclude_fields);

    @GET("/3/DownloadDataset.bin")
    Call<DownloadDataV3> fetchStreaming(@Query("frame_id") String frame_id);

}
