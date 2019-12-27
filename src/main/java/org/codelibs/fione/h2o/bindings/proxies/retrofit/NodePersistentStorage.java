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

import org.codelibs.fione.h2o.bindings.pojos.NodePersistentStorageV3;

import retrofit2.Call;
import retrofit2.http.DELETE;
import retrofit2.http.Field;
import retrofit2.http.FormUrlEncoded;
import retrofit2.http.GET;
import retrofit2.http.POST;
import retrofit2.http.Path;
import retrofit2.http.Query;

public interface NodePersistentStorage {

    /**
     * Return true or false.
     *   @param category Category name
     *   @param name Key name
     *   @param value Value
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @GET("/3/NodePersistentStorage/categories/{category}/names/{name}/exists")
    Call<NodePersistentStorageV3> exists(@Path("category") String category, @Path("name") String name, @Query("value") String value,
            @Query("_exclude_fields") String _exclude_fields);

    @GET("/3/NodePersistentStorage/categories/{category}/names/{name}/exists")
    Call<NodePersistentStorageV3> exists(@Path("category") String category, @Path("name") String name);

    /**
     * Return true or false.
     *   @param category Category name
     *   @param name Key name
     *   @param value Value
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @GET("/3/NodePersistentStorage/configured")
    Call<NodePersistentStorageV3> configured(@Query("category") String category, @Query("name") String name, @Query("value") String value,
            @Query("_exclude_fields") String _exclude_fields);

    @GET("/3/NodePersistentStorage/configured")
    Call<NodePersistentStorageV3> configured();

    /**
     * Store a named value.
     *   @param category Category name
     *   @param name Key name
     *   @param value Value
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @FormUrlEncoded
    @POST("/3/NodePersistentStorage/{category}/{name}")
    Call<NodePersistentStorageV3> put_with_name(@Path("category") String category, @Path("name") String name, @Field("value") String value,
            @Field("_exclude_fields") String _exclude_fields);

    @FormUrlEncoded
    @POST("/3/NodePersistentStorage/{category}/{name}")
    Call<NodePersistentStorageV3> put_with_name(@Path("category") String category, @Path("name") String name);

    /**
     * Return value for a given name.
     *   @param category Category name
     *   @param name Key name
     *   @param value Value
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @GET("/3/NodePersistentStorage/{category}/{name}")
    Call<NodePersistentStorageV3> get_as_string(@Path("category") String category, @Path("name") String name, @Query("value") String value,
            @Query("_exclude_fields") String _exclude_fields);

    @GET("/3/NodePersistentStorage/{category}/{name}")
    Call<NodePersistentStorageV3> get_as_string(@Path("category") String category, @Path("name") String name);

    /**
     * Delete a key.
     *   @param category Category name
     *   @param name Key name
     *   @param value Value
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @DELETE("/3/NodePersistentStorage/{category}/{name}")
    Call<NodePersistentStorageV3> delete(@Path("category") String category, @Path("name") String name, @Field("value") String value,
            @Field("_exclude_fields") String _exclude_fields);

    @DELETE("/3/NodePersistentStorage/{category}/{name}")
    Call<NodePersistentStorageV3> delete(@Path("category") String category, @Path("name") String name);

    /**
     * Store a value.
     *   @param category Category name
     *   @param name Key name
     *   @param value Value
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @FormUrlEncoded
    @POST("/3/NodePersistentStorage/{category}")
    Call<NodePersistentStorageV3> put(@Path("category") String category, @Field("name") String name, @Field("value") String value,
            @Field("_exclude_fields") String _exclude_fields);

    @FormUrlEncoded
    @POST("/3/NodePersistentStorage/{category}")
    Call<NodePersistentStorageV3> put(@Path("category") String category);

    /**
     * Return all keys stored for a given category.
     *   @param category Category name
     *   @param name Key name
     *   @param value Value
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @GET("/3/NodePersistentStorage/{category}")
    Call<NodePersistentStorageV3> list(@Path("category") String category, @Query("name") String name, @Query("value") String value,
            @Query("_exclude_fields") String _exclude_fields);

    @GET("/3/NodePersistentStorage/{category}")
    Call<NodePersistentStorageV3> list(@Path("category") String category);

}
