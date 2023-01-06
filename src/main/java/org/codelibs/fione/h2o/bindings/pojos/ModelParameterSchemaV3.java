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

public class ModelParameterSchemaV3 extends SchemaV3 {

    /**
     * name in the JSON, e.g. "lambda"
     */
    public String name;

    /**
     * [DEPRECATED] same as name.
     */
    public String label;

    /**
     * help for the UI, e.g. "regularization multiplier, typically used for foo bar baz etc."
     */
    public String help;

    /**
     * the field is required
     */
    public boolean required;

    /**
     * Java type, e.g. "double"
     */
    public String type;

    /**
     * default value, e.g. 1
     */
    @SerializedName("default_value")
    public Object defaultValue;

    /**
     * actual value as set by the user and / or modified by the ModelBuilder, e.g., 10
     */
    @SerializedName("actual_value")
    public Object actualValue;

    /**
     * input value as set by the user, e.g., 10
     */
    @SerializedName("input_value")
    public Object inputValue;

    /**
     * the importance of the parameter, used by the UI, e.g. "critical", "extended" or "expert"
     */
    public String level;

    /**
     * list of valid values for use by the front-end
     */
    public String[] values;

    /**
     * For Vec-type fields this is the set of Frame-type fields which must contain the named column; for example, for a
     * SupervisedModel the response_column must be in both the training_frame and (if it's set) the validation_frame
     */
    @SerializedName("is_member_of_frames")
    public String[] isMemberOfFrames;

    /**
     * For Vec-type fields this is the set of other Vec-type fields which must contain mutually exclusive values; for
     * example, for a SupervisedModel the response_column must be mutually exclusive with the weights_column
     */
    @SerializedName("is_mutually_exclusive_with")
    public String[] isMutuallyExclusiveWith;

    /**
     * Parameter can be used in grid call
     */
    public boolean gridable;

    /**
     * Public constructor
     */
    public ModelParameterSchemaV3() {
        name = "";
        label = "";
        help = "";
        required = false;
        type = "";
        level = "";
        gridable = false;
    }

    /**
     * Return the contents of this object as a JSON String.
     */
    @Override
    public String toString() {
        return new GsonBuilder().serializeSpecialFloatingPointValues().create().toJson(this);
    }

}
