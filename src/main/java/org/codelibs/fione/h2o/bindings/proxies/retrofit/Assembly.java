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

import org.codelibs.fione.h2o.bindings.pojos.AssemblyV99;

import retrofit2.Call;
import retrofit2.http.Field;
import retrofit2.http.FormUrlEncoded;
import retrofit2.http.GET;
import retrofit2.http.POST;
import retrofit2.http.Path;
import retrofit2.http.Query;

public interface Assembly {

    /**
     * Generate a Java POJO from the Assembly
     *   @param assembly_id The key of the Assembly object to retrieve from the DKV.
     *   @param pojo_name The name of the file and generated class
     *   @param steps A list of steps describing the assembly line.
     *   @param frame Input Frame for the assembly.
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @GET("/99/Assembly.java/{assembly_id}/{pojo_name}")
    Call<AssemblyV99> toJava(@Path("assembly_id") String assembly_id, @Path("pojo_name") String pojo_name, @Query("steps") String[] steps,
            @Query("frame") String frame, @Query("_exclude_fields") String _exclude_fields);

    @GET("/99/Assembly.java/{assembly_id}/{pojo_name}")
    Call<AssemblyV99> toJava(@Path("assembly_id") String assembly_id, @Path("pojo_name") String pojo_name);

    /**
     * Fit an assembly to an input frame
     *   @param steps A list of steps describing the assembly line.
     *   @param frame Input Frame for the assembly.
     *   @param pojo_name The name of the file and generated class
     *   @param assembly_id The key of the Assembly object to retrieve from the DKV.
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @FormUrlEncoded
    @POST("/99/Assembly")
    Call<AssemblyV99> fit(@Field("steps") String[] steps, @Field("frame") String frame, @Field("pojo_name") String pojo_name,
            @Field("assembly_id") String assembly_id, @Field("_exclude_fields") String _exclude_fields);

    @FormUrlEncoded
    @POST("/99/Assembly")
    Call<AssemblyV99> fit();

}
