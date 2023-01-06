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

public class TreeStatsV3 extends SchemaV3 {

    /**
     * minDepth
     */
    @SerializedName("min_depth")
    public int minDepth;

    /**
     * maxDepth
     */
    @SerializedName("max_depth")
    public int maxDepth;

    /**
     * meanDepth
     */
    @SerializedName("mean_depth")
    public float meanDepth;

    /**
     * minLeaves
     */
    @SerializedName("min_leaves")
    public int minLeaves;

    /**
     * maxLeaves
     */
    @SerializedName("max_leaves")
    public int maxLeaves;

    /**
     * meanLeaves
     */
    @SerializedName("mean_leaves")
    public float meanLeaves;

    /**
     * Public constructor
     */
    public TreeStatsV3() {
        minDepth = 0;
        maxDepth = 0;
        meanDepth = 0.0f;
        minLeaves = 0;
        maxLeaves = 0;
        meanLeaves = 0.0f;
    }

    /**
     * Return the contents of this object as a JSON String.
     */
    @Override
    public String toString() {
        return new GsonBuilder().serializeSpecialFloatingPointValues().create().toJson(this);
    }

}
