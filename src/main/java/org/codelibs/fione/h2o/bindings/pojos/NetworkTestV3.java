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

public class NetworkTestV3 extends RequestSchemaV3 {

    /**
     * Collective broadcast/reduce times in microseconds (for each message size)
     */
    @SerializedName("microseconds_collective")
    public double[] microsecondsCollective;

    /**
     * Collective bandwidths in Bytes/sec (for each message size, for each node)
     */
    @SerializedName("bandwidths_collective")
    public double[] bandwidthsCollective;

    /**
     * Round-trip times in microseconds (for each message size, for each node)
     */
    public double[][] microseconds;

    /**
     * Bi-directional bandwidths in Bytes/sec (for each message size, for each node)
     */
    public double[][] bandwidths;

    /**
     * Nodes
     */
    public String[] nodes;

    /**
     * NetworkTestResults
     */
    public TwoDimTableV3 table;

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
    public NetworkTestV3() {
        _excludeFields = "";
    }

    /**
     * Return the contents of this object as a JSON String.
     */
    @Override
    public String toString() {
        return new GsonBuilder().serializeSpecialFloatingPointValues().create().toJson(this);
    }

}
