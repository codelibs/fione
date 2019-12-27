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

import org.codelibs.fione.h2o.bindings.pojos.JobV4;
import org.codelibs.fione.h2o.bindings.pojos.JobsV3;

import retrofit2.Call;
import retrofit2.http.Field;
import retrofit2.http.FormUrlEncoded;
import retrofit2.http.GET;
import retrofit2.http.POST;
import retrofit2.http.Path;
import retrofit2.http.Query;

public interface Jobs {

    /**
     * Get a list of all the H2O Jobs (long-running actions).
     *   @param job_id Optional Job identifier
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @GET("/3/Jobs")
    Call<JobsV3> list(@Query("job_id") String job_id, @Query("_exclude_fields") String _exclude_fields);

    @GET("/3/Jobs")
    Call<JobsV3> list();

    /**
     * Get the status of the given H2O Job (long-running action).
     *   @param job_id Optional Job identifier
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @GET("/3/Jobs/{job_id}")
    Call<JobsV3> fetch(@Path("job_id") String job_id, @Query("_exclude_fields") String _exclude_fields);

    @GET("/3/Jobs/{job_id}")
    Call<JobsV3> fetch(@Path("job_id") String job_id);

    /**
     * Cancel a running job.
     *   @param job_id Optional Job identifier
     *   @param _exclude_fields Comma-separated list of JSON field paths to exclude from the result, used like:
     *                          "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
     */
    @FormUrlEncoded
    @POST("/3/Jobs/{job_id}/cancel")
    Call<JobsV3> cancel(@Path("job_id") String job_id, @Field("_exclude_fields") String _exclude_fields);

    @FormUrlEncoded
    @POST("/3/Jobs/{job_id}/cancel")
    Call<JobsV3> cancel(@Path("job_id") String job_id);

    /**
     * Retrieve information about the current state of a job.
     *   @param job_id Id of the job to fetch.
     *   @param _fields Filter on the set of output fields: if you set _fields="foo,bar,baz", then only those fields will
     *                  be included in the output; or you can specify _fields="-goo,gee" to include all fields except goo
     *                  and gee. If the result contains nested data structures, then you can refer to the fields within
     *                  those structures as well. For example if you specify _fields="foo(oof),bar(-rab)", then only
     *                  fields foo and bar will be included, and within foo there will be only field oof, whereas within
     *                  bar all fields except rab will be reported.
     */
    @GET("/4/jobs/{job_id}")
    Call<JobV4> getJob4(@Path("job_id") String job_id, @Query("_fields") String _fields);

    @GET("/4/jobs/{job_id}")
    Call<JobV4> getJob4(@Path("job_id") String job_id);

}
