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

import org.codelibs.fione.h2o.bindings.pojos.GramV3;

import retrofit2.Call;
import retrofit2.http.GET;
import retrofit2.http.Query;

public interface ComputeGram {

    /**
     * Get weighted gram matrix
     *   @param X source data
     *   @param W weight vector
     *   @param use_all_factor_levels use all factor levels when doing 1-hot encoding
     *   @param standardize standardize data
     *   @param skip_missing skip missing values
     */
    @GET("/3/ComputeGram")
    Call<GramV3> computeGram(@Query("X") String X, @Query("W") String W, @Query("use_all_factor_levels") boolean use_all_factor_levels,
            @Query("standardize") boolean standardize, @Query("skip_missing") boolean skip_missing);

    @GET("/3/ComputeGram")
    Call<GramV3> computeGram(@Query("X") String X);

}
