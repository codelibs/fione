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

import org.codelibs.fione.h2o.bindings.pojos.GridSchemaV99;
import org.codelibs.fione.h2o.bindings.pojos.GridsV99;

import retrofit2.Call;
import retrofit2.http.GET;
import retrofit2.http.Path;
import retrofit2.http.Query;

public interface Grids {

    /**
     * Return the specified grid search result.
     *   @param grid_id Grid id
     *   @param sort_by Model performance metric to sort by. Examples: logloss, residual_deviance, mse, rmse, mae,rmsle,
     *                  auc, r2, f1, recall, precision, accuracy, mcc, err, err_count, lift_top_group, max_per_class_error
     *   @param decreasing Specify whether sort order should be decreasing.
     *   @param model_ids Model IDs built by a grid search
     */
    @GET("/99/Grids/{grid_id}")
    Call<GridSchemaV99> fetch(@Path("grid_id") String grid_id, @Query("sort_by") String sort_by, @Query("decreasing") boolean decreasing,
            @Query("model_ids") String[] model_ids);

    @GET("/99/Grids/{grid_id}")
    Call<GridSchemaV99> fetch(@Path("grid_id") String grid_id);

    /**
     * Return all grids from H2O distributed K/V store.
     */
    @GET("/99/Grids")
    Call<GridsV99> list();

}
