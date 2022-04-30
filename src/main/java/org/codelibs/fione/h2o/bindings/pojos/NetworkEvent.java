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

public class NetworkEvent extends EventV3 {

    /**
     * Boolean flag distinguishing between sends (true) and receives(false)
     */
    @SerializedName("is_send")
    public boolean isSend;

    /**
     * network protocol (UDP/TCP)
     */
    public String protocol;

    /**
     * UDP type (exec,ack, ackack,...
     */
    @SerializedName("msg_type")
    public String msgType;

    /**
     * Sending node
     */
    public String from;

    /**
     * Receiving node
     */
    public String to;

    /**
     * Pretty print of the first few bytes of the msg payload. Contains class name for tasks.
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
    public NetworkEvent() {
        isSend = false;
        protocol = "unknown";
        msgType = "unknown";
        from = "unknown";
        to = "unknown";
        data = "unknown";
        date = "";
        nanos = -1L;
        type = TimelineEventEventType.unknown;
    }

    /**
     * Return the contents of this object as a JSON String.
     */
    @Override
    public String toString() {
        return new Gson().toJson(this);
    }

}
