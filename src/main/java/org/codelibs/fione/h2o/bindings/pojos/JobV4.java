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
package org.codelibs.fione.h2o.bindings.pojos;

import com.google.gson.GsonBuilder;
import com.google.gson.annotations.SerializedName;

public class JobV4 extends OutputSchemaV4 {

    /**
     * Job id
     */
    @SerializedName("job_id")
    public String jobId;

    /**
     * Job status
     */
    public JobStatus status;

    /**
     * Current progress, a number going from 0 to 1
     */
    public float progress;

    /**
     * Current progress status description
     */
    @SerializedName("progress_msg")
    public String progressMsg;

    /**
     * Start time
     */
    @SerializedName("start_time")
    public long startTime;

    /**
     * Runtime in milliseconds
     */
    public long duration;

    /**
     * Id of the target object (being created by this Job)
     */
    @SerializedName("target_id")
    public String targetId;

    /**
     * Type of the target: Frame, Model, etc.
     */
    @SerializedName("target_type")
    public String targetType;

    /**
     * Exception message, if an exception occurred
     */
    public String exception;

    /**
     * Stacktrace
     */
    public String stacktrace;

    /*------------------------------------------------------------------------------------------------------------------
    //                                                  INHERITED
    //------------------------------------------------------------------------------------------------------------------

    // Url describing the schema of the current object.
    public String __schema;

    */

    /**
     * Public constructor
     */
    public JobV4() {
        jobId = "";
        progress = 0.0f;
        progressMsg = "";
        startTime = 0L;
        duration = 0L;
        targetId = "";
        targetType = "";
        exception = "";
        stacktrace = "";
        __schema = "/4/schemas/JobV4";
    }

    /**
     * Return the contents of this object as a JSON String.
     */
    @Override
    public String toString() {
        return new GsonBuilder().serializeSpecialFloatingPointValues().create().toJson(this);
    }

}
