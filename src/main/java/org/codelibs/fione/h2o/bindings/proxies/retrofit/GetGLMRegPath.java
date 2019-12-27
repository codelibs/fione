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

import org.codelibs.fione.h2o.bindings.pojos.GLMRegularizationPathV3;

import retrofit2.Call;
import retrofit2.http.GET;
import retrofit2.http.Query;

public interface GetGLMRegPath {

    /**
     * Get full regularization path
     *   @param model source model
     *   @param lambdas Computed lambda values
     *   @param explained_deviance_train explained deviance on the training set
     *   @param explained_deviance_valid explained deviance on the validation set
     *   @param coefficients coefficients for all lambdas
     *   @param coefficients_std standardized coefficients for all lambdas
     *   @param coefficient_names coefficient names
     */
    @GET("/3/GetGLMRegPath")
    Call<GLMRegularizationPathV3> extractRegularizationPath(@Query("model") String model, @Query("lambdas") double[] lambdas,
            @Query("explained_deviance_train") double[] explained_deviance_train,
            @Query("explained_deviance_valid") double[] explained_deviance_valid, @Query("coefficients") double[][] coefficients,
            @Query("coefficients_std") double[][] coefficients_std, @Query("coefficient_names") String[] coefficient_names);

    @GET("/3/GetGLMRegPath")
    Call<GLMRegularizationPathV3> extractRegularizationPath(@Query("model") String model);

}
