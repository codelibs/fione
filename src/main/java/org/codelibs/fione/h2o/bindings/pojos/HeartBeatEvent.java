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

public class HeartBeatEvent extends EventV3 {

    /**
     * number of sent heartbeats
     */
    public int sends;

    /**
     * number of received heartbeats
     */
    public int recvs;

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
    public HeartBeatEvent() {
        sends = -1;
        recvs = -1;
        date = "";
        nanos = -1L;
        type = TimelineEventEventType.unknown;
    }

    /**
     * Return the contents of this object as a JSON String.
     */
    @Override
    public String toString() {
        return new GsonBuilder().serializeSpecialFloatingPointValues().create().toJson(this);
    }

}
