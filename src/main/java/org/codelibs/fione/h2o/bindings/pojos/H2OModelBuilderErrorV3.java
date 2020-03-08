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
package org.codelibs.fione.h2o.bindings.pojos;

import com.google.gson.GsonBuilder;
import com.google.gson.annotations.SerializedName;

public class H2OModelBuilderErrorV3 extends H2OErrorV3 {

    /**
     * Model builder parameters.
     */
    public ModelParametersSchemaV3 parameters;

    /**
     * Parameter validation messages
     */
    public ValidationMessageV3[] messages;

    /**
     * Count of parameter validation errors
     */
    @SerializedName("error_count")
    public int errorCount;

    /*------------------------------------------------------------------------------------------------------------------
    //                                                  INHERITED
    //------------------------------------------------------------------------------------------------------------------

    // Milliseconds since the epoch for the time that this H2OError instance was created.  Generally this is a short
    // time since the underlying error ocurred.
    public long timestamp;

    // Error url
    public String errorUrl;

    // Message intended for the end user (a data scientist).
    public String msg;

    // Potentially more detailed message intended for a developer (e.g. a front end engineer or someone designing a
    // language binding).
    public String devMsg;

    // HTTP status code for this error.
    public int httpStatus;

    // Any values that are relevant to reporting or handling this error.  Examples are a key name if the error is on a
    // key, or a field name and object name if it's on a specific field.
    public Map<String,Object> values;

    // Exception type, if any.
    public String exceptionType;

    // Raw exception message, if any.
    public String exceptionMsg;

    // Stacktrace, if any.
    public String[] stacktrace;

    */

    /**
     * Public constructor
     */
    public H2OModelBuilderErrorV3() {
        errorCount = 0;
        timestamp = 0L;
        errorUrl = "";
        msg = "";
        devMsg = "";
        httpStatus = 0;
        exceptionType = "";
        exceptionMsg = "";
    }

    /**
     * Return the contents of this object as a JSON String.
     */
    @Override
    public String toString() {
        return new GsonBuilder().serializeSpecialFloatingPointValues().create().toJson(this);
    }

}
