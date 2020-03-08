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

public class SchemaMetadataV3 extends SchemaV3 {

    /**
     * Version number of the Schema.
     */
    public int version;

    /**
     * Simple name of the Schema. NOTE: the schema_names form a single namespace.
     */
    public String name;

    /**
     * [DEPRECATED] This field is always the same as name.
     */
    public String label;

    /**
     * Simple name of the superclass of the Schema.  NOTE: the schema_names form a single namespace.
     */
    public String superclass;

    /**
     * Simple name of H2O type that this Schema represents. Must not be changed after creation (treat as final).
     */
    public String type;

    /**
     * All the public fields of the schema
     */
    public FieldMetadataV3[] fields;

    /**
     * Documentation for the schema in Markdown format with GitHub extensions
     */
    public String markdown;

    /**
     * Public constructor
     */
    public SchemaMetadataV3() {
        version = 0;
        name = "";
        label = "";
        superclass = "";
        type = "";
        fields = new FieldMetadataV3[] {};
        markdown = "";
    }

    /**
     * Return the contents of this object as a JSON String.
     */
    @Override
    public String toString() {
        return new GsonBuilder().serializeSpecialFloatingPointValues().create().toJson(this);
    }

}
