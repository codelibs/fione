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

public class SaveToHiveTableV3 extends RequestSchemaV3 {

    /**
     * H2O Frame ID
     */
    @SerializedName("frame_id")
    public FrameKeyV3 frameId;

    /**
     * HIVE JDBC URL
     */
    @SerializedName("jdbc_url")
    public String jdbcUrl;

    /**
     * Name of table to save data to.
     */
    @SerializedName("table_name")
    public String tableName;

    /**
     * HDFS Path to where the table should be stored.
     */
    @SerializedName("table_path")
    public String tablePath;

    /**
     * Storage format of the created table.
     */
    public ApiSaveToHiveTableHandlerHiveFrameSaverFormat format;

    /**
     * HDFS Path where to store temporary data.
     */
    @SerializedName("tmp_path")
    public String tmpPath;

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
    public SaveToHiveTableV3() {
        jdbcUrl = "";
        tableName = "";
        tablePath = "";
        tmpPath = "";
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
