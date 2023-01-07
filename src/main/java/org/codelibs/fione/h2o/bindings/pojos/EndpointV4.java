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

public class EndpointV4 extends OutputSchemaV4 {

    /**
     * Method+Url of the request; variable parts are enclosed in curly braces. For example: /4/schemas/{schema_name}
     */
    public String url;

    /**
     * Short description of the functionality provided by the endpoint.
     */
    public String description;

    /**
     * Unique name of the endpoint. These names can be used to look up the endpoint's info via GET /4/endpoints/{name}.
     */
    public String name;

    /**
     * Input schema.
     */
    @SerializedName("input_schema")
    public String inputSchema;

    /**
     * Schema for the result returned by the endpoint.
     */
    @SerializedName("output_schema")
    public String outputSchema;

    /*------------------------------------------------------------------------------------------------------------------
    //                                                  INHERITED
    //------------------------------------------------------------------------------------------------------------------

    // Url describing the schema of the current object.
    public String __schema;

    */

    /**
     * Public constructor
     */
    public EndpointV4() {
        url = "null null";
        description = "";
        name = "";
        inputSchema = "";
        outputSchema = "";
        __schema = "/4/schemas/EndpointV4";
    }

    /**
     * Return the contents of this object as a JSON String.
     */
    @Override
    public String toString() {
        return new GsonBuilder().serializeSpecialFloatingPointValues().create().toJson(this);
    }

}
