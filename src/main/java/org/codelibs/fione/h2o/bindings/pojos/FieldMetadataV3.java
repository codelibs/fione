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

import com.google.gson.GsonBuilder;
import com.google.gson.annotations.SerializedName;

public class FieldMetadataV3 extends SchemaV3 {

    /**
     * Field name in the Schema
     */
    public String name;

    /**
     * Type for this field
     */
    public String type;

    /**
     * Type for this field is itself a Schema.
     */
    @SerializedName("is_schema")
    public boolean isSchema;

    /**
     * Schema name for this field, if it is_schema, or the name of the enum, if it's an enum.
     */
    @SerializedName("schema_name")
    public String schemaName;

    /**
     * Value for this field
     */
    public Object value;

    /**
     * A short help description to appear alongside the field in a UI
     */
    public String help;

    /**
     * The label that should be displayed for the field if the name is insufficient
     */
    public String label;

    /**
     * Is this field required, or is the default value generally sufficient?
     */
    public boolean required;

    /**
     * How important is this field?  The web UI uses the level to do a slow reveal of the parameters
     */
    public APILevel level;

    /**
     * Is this field an input, output or inout?
     */
    public APIDirection direction;

    /**
     * Is the field inherited from the parent schema?
     */
    @SerializedName("is_inherited")
    public boolean isInherited;

    /**
     * If this field is inherited from a class higher in the hierarchy which one?
     */
    @SerializedName("inherited_from")
    public String inheritedFrom;

    /**
     * Is the field gridable (i.e., it can be used in grid call)
     */
    @SerializedName("is_gridable")
    public boolean isGridable;

    /**
     * For enum-type fields the allowed values are specified using the values annotation;  this is used in UIs to tell
     * the user the allowed values, and for validation
     */
    public String[] values;

    /**
     * Should this field be rendered in the JSON representation?
     */
    public boolean json;

    /**
     * For Vec-type fields this is the set of other Vec-type fields which must contain mutually exclusive values; for
     * example, for a SupervisedModel the response_column must be mutually exclusive with the weights_column
     */
    @SerializedName("is_member_of_frames")
    public String[] isMemberOfFrames;

    /**
     * For Vec-type fields this is the set of Frame-type fields which must contain the named column; for example, for a
     * SupervisedModel the response_column must be in both the training_frame and (if it's set) the validation_frame
     */
    @SerializedName("is_mutually_exclusive_with")
    public String[] isMutuallyExclusiveWith;

    /**
     * Public constructor
     */
    public FieldMetadataV3() {
        name = "";
        type = "";
        isSchema = false;
        schemaName = "";
        help = "";
        label = "";
        required = false;
        isInherited = false;
        inheritedFrom = "";
        isGridable = false;
        json = false;
    }

    /**
     * Return the contents of this object as a JSON String.
     */
    @Override
    public String toString() {
        return new GsonBuilder().serializeSpecialFloatingPointValues().create().toJson(this);
    }

}
