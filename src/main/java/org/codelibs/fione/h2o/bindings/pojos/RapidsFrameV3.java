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

public class RapidsFrameV3 extends RapidsSchemaV3 {

    /**
     * Frame result
     */
    public FrameKeyV3 key;

    /**
     * Rows in Frame result
     */
    @SerializedName("num_rows")
    public long numRows;

    /**
     * Columns in Frame result
     */
    @SerializedName("num_cols")
    public int numCols;

    /*------------------------------------------------------------------------------------------------------------------
    //                                                  INHERITED
    //------------------------------------------------------------------------------------------------------------------

    // A Rapids AstRoot expression
    public String ast;

    // Session key
    public String sessionId;

    // [DEPRECATED] Key name to assign Frame results
    public String id;

    // Comma-separated list of JSON field paths to exclude from the result, used like:
    // "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
    public String _excludeFields;

    */

    /**
     * Public constructor
     */
    public RapidsFrameV3() {
        numRows = 0L;
        numCols = 0;
        ast = "";
        sessionId = "";
        id = "";
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
