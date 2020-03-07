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
package org.codelibs.fione.h2o.bindings.pojos;

import static org.codelibs.fione.h2o.bindings.H2oApi.keyToString;

import com.google.gson.GsonBuilder;
import com.google.gson.annotations.SerializedName;

public class JobsV3 extends RequestSchemaV3 {

    /**
     * Optional Job identifier
     */
    @SerializedName("job_id")
    public JobKeyV3 jobId;

    /**
     * jobs
     */
    public JobV3[] jobs;

    /*------------------------------------------------------------------------------------------------------------------
    //                                                  INHERITED
    //------------------------------------------------------------------------------------------------------------------

    // Comma-separated list of JSON field paths to exclude from the result, used like:
    // "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
    public String _excludeFields;

    */

    /**
     * Public constructor
     */
    public JobsV3() {
        _excludeFields = "";
    }

    /**
     * Return the contents of this object as a JSON String.
     */
    @Override
    public String toString() {
        return new GsonBuilder().serializeSpecialFloatingPointValues().create().toJson(this);
    }

    public JobV3 findJob(final String jobId) {
        for (final JobV3 job : jobs) {
            if (jobId.equals(keyToString(job.key))) {
                return job;
            }
        }
        return null;
    }
}
