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

import com.google.gson.Gson;
import com.google.gson.annotations.SerializedName;

public class IOEvent extends EventV3 {

    /**
     * flavor of the recorded io (ice/hdfs/...)
     */
    @SerializedName("io_flavor")
    public String ioFlavor;

    /**
     * node where this io event happened
     */
    public String node;

    /**
     * data info
     */
    public String data;

    /*------------------------------------------------------------------------------------------------------------------
    //                                                  INHERITED
    //------------------------------------------------------------------------------------------------------------------

    // Time when the event was recorded. Format is hh:mm:ss:ms
    public String date;

    // Time in nanos
    public long nanos;

    // type of recorded event
    public TimelineEventEventType type;

    */

    /**
     * Public constructor
     */
    public IOEvent() {
        ioFlavor = "unknown";
        node = "unknown";
        data = "unknown";
        date = "08:59:59:999";
        nanos = -1L;
        type = TimelineEventEventType.io;
    }

    /**
     * Return the contents of this object as a JSON String.
     */
    @Override
    public String toString() {
        return new Gson().toJson(this);
    }

}
