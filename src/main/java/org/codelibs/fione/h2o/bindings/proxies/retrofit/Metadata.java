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

import org.codelibs.fione.h2o.bindings.pojos.MetadataV3;

import retrofit2.Call;
import retrofit2.http.GET;
import retrofit2.http.Path;
import retrofit2.http.Query;

public interface Metadata {

    /**
     * Return the list of (almost) all REST API endpoints.
     *   @param num Number for specifying an endpoint
     *   @param http_method HTTP method (GET, POST, DELETE) if fetching by path
     *   @param path Path for specifying an endpoint
     *   @param classname Class name, for fetching docs for a schema (DEPRECATED)
     *   @param schemaname Schema name (e.g., DocsV1), for fetching docs for a schema
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @GET("/3/Metadata/endpoints")
    Call<MetadataV3> listRoutes(@Query("num") int num, @Query("http_method") String http_method, @Query("path") String path,
            @Query("classname") String classname, @Query("schemaname") String schemaname, @Query("_exclude_fields") String _exclude_fields);

    @GET("/3/Metadata/endpoints")
    Call<MetadataV3> listRoutes();

    /**
     * Return the REST API endpoint metadata, including documentation, for the endpoint specified by path or index.
     *   @param path Path for specifying an endpoint
     *   @param num Number for specifying an endpoint
     *   @param http_method HTTP method (GET, POST, DELETE) if fetching by path
     *   @param classname Class name, for fetching docs for a schema (DEPRECATED)
     *   @param schemaname Schema name (e.g., DocsV1), for fetching docs for a schema
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @GET("/3/Metadata/endpoints/{path}")
    Call<MetadataV3> fetchRoute(@Path("path") String path, @Query("num") int num, @Query("http_method") String http_method,
            @Query("classname") String classname, @Query("schemaname") String schemaname, @Query("_exclude_fields") String _exclude_fields);

    @GET("/3/Metadata/endpoints/{path}")
    Call<MetadataV3> fetchRoute(@Path("path") String path);

    /**
     * Return the REST API schema metadata for specified schema class.
     *   @param classname Class name, for fetching docs for a schema (DEPRECATED)
     *   @param num Number for specifying an endpoint
     *   @param http_method HTTP method (GET, POST, DELETE) if fetching by path
     *   @param path Path for specifying an endpoint
     *   @param schemaname Schema name (e.g., DocsV1), for fetching docs for a schema
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @GET("/3/Metadata/schemaclasses/{classname}")
    Call<MetadataV3> fetchSchemaMetadataByClass(@Path("classname") String classname, @Query("num") int num,
            @Query("http_method") String http_method, @Query("path") String path, @Query("schemaname") String schemaname,
            @Query("_exclude_fields") String _exclude_fields);

    @GET("/3/Metadata/schemaclasses/{classname}")
    Call<MetadataV3> fetchSchemaMetadataByClass(@Path("classname") String classname);

    /**
     * Return the REST API schema metadata for specified schema.
     *   @param schemaname Schema name (e.g., DocsV1), for fetching docs for a schema
     *   @param num Number for specifying an endpoint
     *   @param http_method HTTP method (GET, POST, DELETE) if fetching by path
     *   @param path Path for specifying an endpoint
     *   @param classname Class name, for fetching docs for a schema (DEPRECATED)
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @GET("/3/Metadata/schemas/{schemaname}")
    Call<MetadataV3> fetchSchemaMetadata(@Path("schemaname") String schemaname, @Query("num") int num,
            @Query("http_method") String http_method, @Query("path") String path, @Query("classname") String classname,
            @Query("_exclude_fields") String _exclude_fields);

    @GET("/3/Metadata/schemas/{schemaname}")
    Call<MetadataV3> fetchSchemaMetadata(@Path("schemaname") String schemaname);

    /**
     * Return list of all REST API schemas.
     *   @param num Number for specifying an endpoint
     *   @param http_method HTTP method (GET, POST, DELETE) if fetching by path
     *   @param path Path for specifying an endpoint
     *   @param classname Class name, for fetching docs for a schema (DEPRECATED)
     *   @param schemaname Schema name (e.g., DocsV1), for fetching docs for a schema
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @GET("/3/Metadata/schemas")
    Call<MetadataV3> listSchemas(@Query("num") int num, @Query("http_method") String http_method, @Query("path") String path,
            @Query("classname") String classname, @Query("schemaname") String schemaname, @Query("_exclude_fields") String _exclude_fields);

    @GET("/3/Metadata/schemas")
    Call<MetadataV3> listSchemas();

}
