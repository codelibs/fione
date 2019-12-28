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

import org.codelibs.core.lang.StringUtil;

import com.google.gson.GsonBuilder;
import com.google.gson.annotations.SerializedName;

public class AutoMLBuildModelsV99 extends SchemaV3 {

    /**
     * A list of algorithms to skip during the model-building phase.
     */
    @SerializedName("exclude_algos")
    public String[] excludeAlgos;

    /**
     * A list of algorithms to restrict to during the model-building phase.
     */
    @SerializedName("include_algos")
    public String[] includeAlgos;

    /**
     * The list of modeling steps to be used by the AutoML engine (they may not all get executed, depending on other
     * constraints).
     */
    @SerializedName("modeling_plan")
    public StepDefinitionV99[] modelingPlan;

    /**
     * Custom algorithm parameters.
     */
    @SerializedName("algo_parameters")
    public AutoMLCustomParameterV99[] algoParameters;

    /**
     * A mapping representing monotonic constraints. Use +1 to enforce an increasing constraint and -1 to specify a
     * decreasing constraint.
     */
    @SerializedName("monotone_constraints")
    public KeyValueV3[] monotoneConstraints;

    /**
     * Public constructor
     */
    public AutoMLBuildModelsV99() {
        excludeAlgos = StringUtil.EMPTY_STRINGS;
        monotoneConstraints = new KeyValueV3[0];
    }

    /**
     * Return the contents of this object as a JSON String.
     */
    @Override
    public String toString() {
        return new GsonBuilder().serializeSpecialFloatingPointValues().create().toJson(this);
    }

}
