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

import org.codelibs.fione.h2o.bindings.pojos.FeatureInteractionV3;

import retrofit2.Call;
import retrofit2.http.Field;
import retrofit2.http.FormUrlEncoded;
import retrofit2.http.POST;

public interface FeatureInteraction {

    /**
     * Fetch feature interaction data
     *   @param model_id Model id of interest
     *   @param max_interaction_depth Maximum interaction depth
     *   @param max_tree_depth Maximum tree depth
     *   @param max_deepening Maximum deepening
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @FormUrlEncoded
    @POST("/3/FeatureInteraction")
    Call<FeatureInteractionV3> makeFeatureInteraction(@Field("model_id") String model_id,
            @Field("max_interaction_depth") int max_interaction_depth, @Field("max_tree_depth") int max_tree_depth,
            @Field("max_deepening") int max_deepening, @Field("_exclude_fields") String _exclude_fields);

    @FormUrlEncoded
    @POST("/3/FeatureInteraction")
    Call<FeatureInteractionV3> makeFeatureInteraction(@Field("max_interaction_depth") int max_interaction_depth,
            @Field("max_tree_depth") int max_tree_depth, @Field("max_deepening") int max_deepening);

}
