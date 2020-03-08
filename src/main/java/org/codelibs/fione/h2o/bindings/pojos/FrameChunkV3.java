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

public class FrameChunkV3 extends SchemaV3 {

    /**
     * An identifier unique in scope of a given frame
     */
    @SerializedName("chunk_id")
    public int chunkId;

    /**
     * Number of rows represented byt the chunk
     */
    @SerializedName("row_count")
    public int rowCount;

    /**
     * Index of H2O node where the chunk is located in
     */
    @SerializedName("node_idx")
    public int nodeIdx;

    /**
     * Public constructor
     */
    public FrameChunkV3() {
        chunkId = 0;
        rowCount = 0;
        nodeIdx = 0;
    }

    /**
     * Return the contents of this object as a JSON String.
     */
    @Override
    public String toString() {
        return new GsonBuilder().serializeSpecialFloatingPointValues().create().toJson(this);
    }

}
