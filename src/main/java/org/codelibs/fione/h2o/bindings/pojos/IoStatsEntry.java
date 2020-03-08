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

public class IoStatsEntry extends SchemaV3 {

    /**
     * Back end type
     */
    public String backend;

    /**
     * Number of store events
     */
    @SerializedName("store_count")
    public long storeCount;

    /**
     * Cumulative stored bytes
     */
    @SerializedName("store_bytes")
    public long storeBytes;

    /**
     * Number of delete events
     */
    @SerializedName("delete_count")
    public long deleteCount;

    /**
     * Number of load events
     */
    @SerializedName("load_count")
    public long loadCount;

    /**
     * Cumulative loaded bytes
     */
    @SerializedName("load_bytes")
    public long loadBytes;

    /**
     * Public constructor
     */
    public IoStatsEntry() {
        backend = "";
        storeCount = 0L;
        storeBytes = 0L;
        deleteCount = 0L;
        loadCount = 0L;
        loadBytes = 0L;
    }

    /**
     * Return the contents of this object as a JSON String.
     */
    @Override
    public String toString() {
        return new GsonBuilder().serializeSpecialFloatingPointValues().create().toJson(this);
    }

}
