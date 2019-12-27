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

public class AutoMLBuildSpecV99 extends SchemaV3 {

    /**
     * Specification of overall controls for the AutoML build process.
     */
    @SerializedName("build_control")
    public AutoMLBuildControlV99 buildControl;

    /**
     * Specification of the input data for the AutoML build process.
     */
    @SerializedName("input_spec")
    public AutoMLInputV99 inputSpec;

    /**
     * If present, specifies details of how to train models.
     */
    @SerializedName("build_models")
    public AutoMLBuildModelsV99 buildModels;

    /**
     * The AutoML Job key
     */
    public JobV3 job;

    /**
     * Public constructor
     */
    public AutoMLBuildSpecV99() {
        buildControl = new AutoMLBuildControlV99();
        inputSpec = new AutoMLInputV99();
        buildModels = new AutoMLBuildModelsV99();
        //        {'__meta': {'schema_version': 99, 'schema_name': 'AutoMLBuildModelsV99', 'schema_type': 'AutoMLBuildModels'}, 'exclude_algos': None, 'include_algos': None, 'modeling_plan': None, 'algo_parameters': None, 'monotone_constraints': None};
    }

    /**
     * Return the contents of this object as a JSON String.
     */
    @Override
    public String toString() {
        return new GsonBuilder().serializeSpecialFloatingPointValues().create().toJson(this);
    }

}
