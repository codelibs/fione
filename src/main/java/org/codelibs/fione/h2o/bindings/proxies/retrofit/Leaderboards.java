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

import org.codelibs.fione.h2o.bindings.pojos.LeaderboardV99;
import org.codelibs.fione.h2o.bindings.pojos.LeaderboardsV99;

import retrofit2.Call;
import retrofit2.http.GET;
import retrofit2.http.Path;
import retrofit2.http.Query;

public interface Leaderboards {

    /**
     * Return all the AutoML leaderboards.
     *   @param project_name Name of project of interest
     *   @param extensions List of extension columns to add to leaderboard
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @GET("/99/Leaderboards")
    Call<LeaderboardsV99> list(@Query("project_name") String project_name, @Query("extensions") String[] extensions,
            @Query("_exclude_fields") String _exclude_fields);

    @GET("/99/Leaderboards")
    Call<LeaderboardsV99> list();

    /**
     * Return the AutoML leaderboard for the given project.
     *   @param project_name Name of project of interest
     *   @param extensions List of extension columns to add to leaderboard
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @GET("/99/Leaderboards/{project_name}")
    Call<LeaderboardV99> fetch(@Path("project_name") String project_name, @Query("extensions") String[] extensions,
            @Query("_exclude_fields") String _exclude_fields);

    @GET("/99/Leaderboards/{project_name}")
    Call<LeaderboardV99> fetch(@Path("project_name") String project_name);

}
