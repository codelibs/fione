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

import org.codelibs.fione.h2o.bindings.pojos.JobV3;
import org.codelibs.fione.h2o.bindings.pojos.PartialDependenceV3;

import retrofit2.Call;
import retrofit2.http.Field;
import retrofit2.http.FormUrlEncoded;
import retrofit2.http.GET;
import retrofit2.http.POST;
import retrofit2.http.Path;
import retrofit2.http.Query;

public interface PartialDependence {

    /**
     * Create data for partial dependence plot(s) for the specified model and frame.
     *   @param model_id Model
     *   @param frame_id Frame
     *   @param row_index Row Index
     *   @param cols Column(s)
     *   @param weight_column_index weight_column_index
     *   @param add_missing_na add_missing_na
     *   @param nbins Number of bins
     *   @param user_splits User define split points
     *   @param user_cols Column(s) of user defined splits
     *   @param num_user_splits Number of user defined splits per column
     *   @param col_pairs_2dpdp lists of column name pairs to plot 2D pdp for
     *   @param destination_key Key to store the destination
     */
    @FormUrlEncoded
    @POST("/3/PartialDependence/")
    Call<JobV3> makePartialDependence(@Field("model_id") String model_id, @Field("frame_id") String frame_id,
            @Field("row_index") long row_index, @Field("cols") String[] cols, @Field("weight_column_index") int weight_column_index,
            @Field("add_missing_na") boolean add_missing_na, @Field("nbins") int nbins, @Field("user_splits") double[] user_splits,
            @Field("user_cols") String[] user_cols, @Field("num_user_splits") int[] num_user_splits,
            @Field("col_pairs_2dpdp") String[][] col_pairs_2dpdp, @Field("destination_key") String destination_key);

    @FormUrlEncoded
    @POST("/3/PartialDependence/")
    Call<JobV3> makePartialDependence();

    /**
     * Fetch partial dependence data.
     *   @param name Name (string representation) for this Key.
     *   @param type Name (string representation) for the type of Keyed this Key points to.
     *   @param URL URL for the resource that this Key points to, if one exists.
     */
    @GET("/3/PartialDependence/{name}")
    Call<PartialDependenceV3> fetchPartialDependence(@Path("name") String name, @Query("type") String type, @Query("URL") String URL);

    @GET("/3/PartialDependence/{name}")
    Call<PartialDependenceV3> fetchPartialDependence(@Path("name") String name);

}
