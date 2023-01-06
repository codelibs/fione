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

import org.codelibs.fione.h2o.bindings.pojos.LogsV3;

import retrofit2.Call;
import retrofit2.http.GET;
import retrofit2.http.Path;
import retrofit2.http.Query;

public interface Logs {

    /**
     * Get named log file for a node.
     *   @param nodeidx Identifier of the node to get logs from. It can be either node index starting from (0-based),
     *                  where -1 means current node, or IP and port.
     *   @param name Which specific log file to read from the log file directory. If left unspecified, the system chooses
     *               a default for you.
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @GET("/3/Logs/nodes/{nodeidx}/files/{name}")
    Call<LogsV3> fetch(@Path("nodeidx") String nodeidx, @Path("name") String name, @Query("_exclude_fields") String _exclude_fields);

    @GET("/3/Logs/nodes/{nodeidx}/files/{name}")
    Call<LogsV3> fetch(@Path("nodeidx") String nodeidx, @Path("name") String name);

}
