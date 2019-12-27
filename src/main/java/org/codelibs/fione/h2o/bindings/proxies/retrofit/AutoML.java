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

import org.codelibs.fione.h2o.bindings.pojos.AutoMLV99;

import retrofit2.Call;
import retrofit2.http.GET;
import retrofit2.http.Path;
import retrofit2.http.Query;

public interface AutoML {

    /**
     * Fetch the specified AutoML object.
     *   @param automl_id Optional AutoML run ID; omitting this returns all runs
     *   @param project_name Identifier for models that should be grouped together in the same leaderboard
     *   @param sort_metric Metric used to sort leaderboard
     */
    @GET("/99/AutoML/{automl_id}")
    Call<AutoMLV99> fetch(@Path("automl_id") String automl_id, @Query("project_name") String project_name,
            @Query("sort_metric") String sort_metric);

    @GET("/99/AutoML/{automl_id}")
    Call<AutoMLV99> fetch(@Path("automl_id") String automl_id);

}
