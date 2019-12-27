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

public class MetadataV3 extends RequestSchemaV3 {

    /**
     * Number for specifying an endpoint
     */
    public int num;

    /**
     * HTTP method (GET, POST, DELETE) if fetching by path
     */
    @SerializedName("http_method")
    public String httpMethod;

    /**
     * Path for specifying an endpoint
     */
    public String path;

    /**
     * Class name, for fetching docs for a schema (DEPRECATED)
     */
    public String classname;

    /**
     * Schema name (e.g., DocsV1), for fetching docs for a schema
     */
    public String schemaname;

    /**
     * List of endpoint routes
     */
    public RouteV3[] routes;

    /**
     * List of schemas
     */
    public SchemaMetadataV3[] schemas;

    /**
     * Table of Contents Markdown
     */
    public String markdown;

    /*------------------------------------------------------------------------------------------------------------------
    //                                                  INHERITED
    //------------------------------------------------------------------------------------------------------------------

    // Comma-separated list of JSON field paths to exclude from the result, used like:
    // "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
    public String _excludeFields;

    */

    /**
     * Public constructor
     */
    public MetadataV3() {
        num = 0;
        httpMethod = "";
        path = "";
        classname = "";
        schemaname = "";
        markdown = "";
        _excludeFields = "";
    }

    /**
     * Return the contents of this object as a JSON String.
     */
    @Override
    public String toString() {
        return new GsonBuilder().serializeSpecialFloatingPointValues().create().toJson(this);
    }

}
