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

import com.fasterxml.jackson.annotation.JsonIgnore;
import com.google.gson.Gson;
import com.google.gson.annotations.SerializedName;

public class ModelSchemaBaseV3 extends SchemaV3 {

    /**
     * Model key
     */
    @SerializedName("model_id")
    public ModelKeyV3 modelId;

    /**
     * The algo name for this Model.
     */
    public String algo;

    /**
     * The pretty algo name for this Model (e.g., Generalized Linear Model, rather than GLM).
     */
    @SerializedName("algo_full_name")
    public String algoFullName;

    /**
     * The response column name for this Model (if applicable). Is null otherwise.
     */
    @SerializedName("response_column_name")
    public String responseColumnName;

    /**
     * The treatment column name for this Model (if applicable). Is null otherwise.
     */
    @SerializedName("treatment_column_name")
    public String treatmentColumnName;

    /**
     * The Model's training frame key
     */
    @SerializedName("data_frame")
    public FrameKeyV3 dataFrame;

    /**
     * Timestamp for when this model was completed
     */
    public long timestamp;

    /**
     * Indicator, whether export to POJO is available
     */
    @SerializedName("have_pojo")
    public boolean havePojo;

    /**
     * Indicator, whether export to MOJO is available
     */
    @SerializedName("have_mojo")
    public boolean haveMojo;

    /**
     * Public constructor
     */
    public ModelSchemaBaseV3() {
        algo = "";
        algoFullName = "";
        responseColumnName = "";
        treatmentColumnName = "";
        timestamp = 0L;
        havePojo = false;
        haveMojo = false;
    }

    /**
     * Return the contents of this object as a JSON String.
     */
    @Override
    public String toString() {
        return new Gson().toJson(this);
    }

    @JsonIgnore
    private transient boolean inLocal = false;

    public boolean isInLocal() {
        return inLocal;
    }

    public void setInLocal(final boolean inLocal) {
        this.inLocal = inLocal;
    }
}
