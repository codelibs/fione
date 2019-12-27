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

import com.google.gson.GsonBuilder;

public class EventLogEntryV99 extends SchemaV3 {

    /**
     * Timestamp for this event, in milliseconds since Jan 1, 1970
     */
    public long timestamp;

    /**
     * Importance of this log event
     */
    public H2oautomleventsEventLogEntryLevel level;

    /**
     * Stage of the AutoML process for this log event
     */
    public H2oautomleventsEventLogEntryStage stage;

    /**
     * Message for this event
     */
    public String message;

    /**
     * String identifier associated to this entry
     */
    public String name;

    /**
     * Value associated to this entry
     */
    public String value;

    /**
     * Public constructor
     */
    public EventLogEntryV99() {
        timestamp = 0L;
        message = "";
        name = "";
        value = "";
    }

    /**
     * Return the contents of this object as a JSON String.
     */
    @Override
    public String toString() {
        return new GsonBuilder().serializeSpecialFloatingPointValues().create().toJson(this);
    }

}
