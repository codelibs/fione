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

import org.codelibs.fione.h2o.bindings.pojos.ModelExportV3;
import org.codelibs.fione.h2o.bindings.pojos.ModelsV3;
import org.codelibs.fione.h2o.bindings.pojos.StreamingSchema;

import retrofit2.Call;
import retrofit2.http.DELETE;
import retrofit2.http.Field;
import retrofit2.http.FormUrlEncoded;
import retrofit2.http.GET;
import retrofit2.http.POST;
import retrofit2.http.Path;
import retrofit2.http.Query;

public interface Models {

    /**
     * Return the specified Model from the H2O distributed K/V store, optionally with the list of compatible Frames.
     *   @param model_id Name of Model of interest
     *   @param preview Return potentially abridged model suitable for viewing in a browser
     *   @param find_compatible_frames Find and return compatible frames?
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @GET("/3/Models/{model_id}")
    Call<ModelsV3> fetch(@Path("model_id") String model_id, @Query("preview") boolean preview,
            @Query("find_compatible_frames") boolean find_compatible_frames, @Query("_exclude_fields") String _exclude_fields);

    @GET("/3/Models/{model_id}")
    Call<ModelsV3> fetch(@Path("model_id") String model_id);

    /**
     * Return all Models from the H2O distributed K/V store.
     *   @param model_id Name of Model of interest
     *   @param preview Return potentially abridged model suitable for viewing in a browser
     *   @param find_compatible_frames Find and return compatible frames?
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @GET("/3/Models")
    Call<ModelsV3> list(@Query("model_id") String model_id, @Query("preview") boolean preview,
            @Query("find_compatible_frames") boolean find_compatible_frames, @Query("_exclude_fields") String _exclude_fields);

    @GET("/3/Models")
    Call<ModelsV3> list();

    /**
     * Delete the specified Model from the H2O distributed K/V store.
     *   @param model_id Name of Model of interest
     *   @param preview Return potentially abridged model suitable for viewing in a browser
     *   @param find_compatible_frames Find and return compatible frames?
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @DELETE("/3/Models/{model_id}")
    Call<ModelsV3> delete(@Path("model_id") String model_id, @Field("preview") boolean preview,
            @Field("find_compatible_frames") boolean find_compatible_frames, @Field("_exclude_fields") String _exclude_fields);

    @DELETE("/3/Models/{model_id}")
    Call<ModelsV3> delete(@Path("model_id") String model_id);

    /**
     * Delete all Models from the H2O distributed K/V store.
     *   @param model_id Name of Model of interest
     *   @param preview Return potentially abridged model suitable for viewing in a browser
     *   @param find_compatible_frames Find and return compatible frames?
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @DELETE("/3/Models")
    Call<ModelsV3> deleteAll(@Field("model_id") String model_id, @Field("preview") boolean preview,
            @Field("find_compatible_frames") boolean find_compatible_frames, @Field("_exclude_fields") String _exclude_fields);

    @DELETE("/3/Models")
    Call<ModelsV3> deleteAll();

    /**
     * Return potentially abridged model suitable for viewing in a browser (currently only used for java model code).
     *   @param model_id Name of Model of interest
     *   @param preview Return potentially abridged model suitable for viewing in a browser
     *   @param find_compatible_frames Find and return compatible frames?
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @GET("/3/Models.java/{model_id}/preview")
    Call<StreamingSchema> fetchPreview(@Path("model_id") String model_id, @Query("preview") boolean preview,
            @Query("find_compatible_frames") boolean find_compatible_frames, @Query("_exclude_fields") String _exclude_fields);

    @GET("/3/Models.java/{model_id}/preview")
    Call<StreamingSchema> fetchPreview(@Path("model_id") String model_id);

    /**
     * [DEPRECATED] Return the stream containing model implementation in Java code.
     *   @param model_id Name of Model of interest
     *   @param preview Return potentially abridged model suitable for viewing in a browser
     *   @param find_compatible_frames Find and return compatible frames?
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @GET("/3/Models.java/{model_id}")
    Call<StreamingSchema> fetchJavaCode(@Path("model_id") String model_id, @Query("preview") boolean preview,
            @Query("find_compatible_frames") boolean find_compatible_frames, @Query("_exclude_fields") String _exclude_fields);

    @GET("/3/Models.java/{model_id}")
    Call<StreamingSchema> fetchJavaCode(@Path("model_id") String model_id);

    /**
     * Return the model in the MOJO format. This format can then be interpreted by gen_model.jar in order to perform
     * prediction / scoring. Currently works for GBM and DRF algos only.
     *   @param model_id Name of Model of interest
     *   @param preview Return potentially abridged model suitable for viewing in a browser
     *   @param find_compatible_frames Find and return compatible frames?
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @GET("/3/Models/{model_id}/mojo")
    Call<StreamingSchema> fetchMojo(@Path("model_id") String model_id, @Query("preview") boolean preview,
            @Query("find_compatible_frames") boolean find_compatible_frames, @Query("_exclude_fields") String _exclude_fields);

    @GET("/3/Models/{model_id}/mojo")
    Call<StreamingSchema> fetchMojo(@Path("model_id") String model_id);

    /**
     * Import given binary model into H2O.
     *   @param model_id Save imported model under given key into DKV.
     *   @param dir Source directory (hdfs, s3, local) containing serialized model
     *   @param force Override existing model in case it exists or throw exception if set to false
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @FormUrlEncoded
    @POST("/99/Models.bin/{model_id}")
    Call<ModelsV3> importModel(@Path("model_id") String model_id, @Field("dir") String dir, @Field("force") boolean force,
            @Field("_exclude_fields") String _exclude_fields);

    @FormUrlEncoded
    @POST("/99/Models.bin/{model_id}")
    Call<ModelsV3> importModel(@Path("model_id") String model_id);

    /**
     * Export given model.
     *   @param model_id Name of Model of interest
     *   @param dir Destination file (hdfs, s3, local)
     *   @param force Overwrite destination file in case it exists or throw exception if set to false.
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @GET("/99/Models.bin/{model_id}")
    Call<ModelExportV3> exportModel(@Path("model_id") String model_id, @Query("dir") String dir, @Query("force") boolean force,
            @Query("_exclude_fields") String _exclude_fields);

    @GET("/99/Models.bin/{model_id}")
    Call<ModelExportV3> exportModel(@Path("model_id") String model_id);

    /**
     * Export given model as Mojo.
     *   @param model_id Name of Model of interest
     *   @param dir Destination file (hdfs, s3, local)
     *   @param force Overwrite destination file in case it exists or throw exception if set to false.
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @GET("/99/Models.mojo/{model_id}")
    Call<ModelExportV3> exportMojo(@Path("model_id") String model_id, @Query("dir") String dir, @Query("force") boolean force,
            @Query("_exclude_fields") String _exclude_fields);

    @GET("/99/Models.mojo/{model_id}")
    Call<ModelExportV3> exportMojo(@Path("model_id") String model_id);

    /**
     * Export given model details in json format.
     *   @param model_id Name of Model of interest
     *   @param dir Destination file (hdfs, s3, local)
     *   @param force Overwrite destination file in case it exists or throw exception if set to false.
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @GET("/99/Models/{model_id}/json")
    Call<ModelExportV3> exportModelDetails(@Path("model_id") String model_id, @Query("dir") String dir, @Query("force") boolean force,
            @Query("_exclude_fields") String _exclude_fields);

    @GET("/99/Models/{model_id}/json")
    Call<ModelExportV3> exportModelDetails(@Path("model_id") String model_id);

}
