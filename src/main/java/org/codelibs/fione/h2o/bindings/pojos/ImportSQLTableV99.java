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

public class ImportSQLTableV99 extends RequestSchemaV3 {

    /**
     * connection_url
     */
    @SerializedName("connection_url")
    public String connectionUrl;

    /**
     * table
     */
    public String table;

    /**
     * select_query
     */
    @SerializedName("select_query")
    public String selectQuery;

    /**
     * use_temp_table
     */
    @SerializedName("use_temp_table")
    public String useTempTable;

    /**
     * temp_table_name
     */
    @SerializedName("temp_table_name")
    public String tempTableName;

    /**
     * username
     */
    public String username;

    /**
     * password
     */
    public String password;

    /**
     * columns
     */
    public String columns;

    /**
     * Mode for data loading. All modes may not be supported by all databases.
     */
    @SerializedName("fetch_mode")
    public String fetchMode;

    /**
     * Desired number of chunks for the target Frame. Optional.
     */
    @SerializedName("num_chunks_hint")
    public String numChunksHint;

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
    public ImportSQLTableV99() {
        connectionUrl = "";
        table = "";
        selectQuery = "";
        useTempTable = "";
        tempTableName = "";
        username = "";
        password = "";
        columns = "*";
        fetchMode = "";
        numChunksHint = "";
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
