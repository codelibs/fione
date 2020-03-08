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

public class TreeV3 extends SchemaV3 {

    /**
     * Key of the model the desired tree belongs to
     */
    public ModelKeyV3 model;

    /**
     * Index of the tree in the model.
     */
    @SerializedName("tree_number")
    public int treeNumber;

    /**
     * Name of the class of the tree. Ignored for regression and binomial.
     */
    @SerializedName("tree_class")
    public String treeClass;

    /**
     * Left child nodes in the tree
     */
    @SerializedName("left_children")
    public int[] leftChildren;

    /**
     * Right child nodes in the tree
     */
    @SerializedName("right_children")
    public int[] rightChildren;

    /**
     * Number of the root node
     */
    @SerializedName("root_node_id")
    public int rootNodeId;

    /**
     * Split thresholds (numeric and possibly categorical columns)
     */
    public float[] thresholds;

    /**
     * Names of the column of the split
     */
    public String[] features;

    /**
     * Which way NA Splits (LEFT, RIGHT, NA)
     */
    public String[] nas;

    /**
     * Description of the tree's nodes
     */
    public String[] descriptions;

    /**
     * Categorical levels on the edge from the parent node
     */
    public int[][] levels;

    /**
     * Prediction values on terminal nodes
     */
    public float[] predictions;

    /**
     * Public constructor
     */
    public TreeV3() {
        treeNumber = 0;
        treeClass = "";
        rootNodeId = 0;
    }

    /**
     * Return the contents of this object as a JSON String.
     */
    @Override
    public String toString() {
        return new GsonBuilder().serializeSpecialFloatingPointValues().create().toJson(this);
    }

}
