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
import com.google.gson.annotations.SerializedName;

public class EventLogV99 {

    /**
     * ID of the AutoML run for which the event log was recorded
     */
    @SerializedName("automl_id")
    public AutoMLKeyV3 automlId;

    /**
     * List of events produced during the AutoML run
     */
    public EventLogEntryV99[] events;

    /**
     * A table representation of this event log, for easy rendering
     */
    public TwoDimTableV3 table;

    /**
     * Public constructor
     */
    public EventLogV99() {
    }

    /**
     * Return the contents of this object as a JSON String.
     */
    @Override
    public String toString() {
        return new GsonBuilder().serializeSpecialFloatingPointValues().create().toJson(this);
    }

}
