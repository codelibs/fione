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
package org.codelibs.fione.h2o.bindings.pojos;

import com.google.gson.GsonBuilder;
import com.google.gson.annotations.SerializedName;

public class JobIV4 extends InputSchemaV4 {

    /**
     * Id of the job to fetch.
     */
    @SerializedName("job_id")
    public String jobId;

    /*------------------------------------------------------------------------------------------------------------------
    //                                                  INHERITED
    //------------------------------------------------------------------------------------------------------------------

    // Filter on the set of output fields: if you set _fields="foo,bar,baz", then only those fields will be included in
    // the output; or you can specify _fields="-goo,gee" to include all fields except goo and gee. If the result
    // contains nested data structures, then you can refer to the fields within those structures as well. For example if
    // you specify _fields="foo(oof),bar(-rab)", then only fields foo and bar will be included, and within foo there
    // will be only field oof, whereas within bar all fields except rab will be reported.
    public String _fields;

    */

    /**
     * Public constructor
     */
    public JobIV4() {
        jobId = "";
        _fields = "";
    }

    /**
     * Return the contents of this object as a JSON String.
     */
    @Override
    public String toString() {
        return new GsonBuilder().serializeSpecialFloatingPointValues().create().toJson(this);
    }

}
