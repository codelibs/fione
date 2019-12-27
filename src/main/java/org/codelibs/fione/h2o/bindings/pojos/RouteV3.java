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

public class RouteV3 extends SchemaV3 {

    /**

     */
    @SerializedName("http_method")
    public String httpMethod;

    /**

     */
    @SerializedName("url_pattern")
    public String urlPattern;

    /**

     */
    public String summary;

    /**

     */
    @SerializedName("api_name")
    public String apiName;

    /**

     */
    @SerializedName("handler_class")
    public String handlerClass;

    /**

     */
    @SerializedName("handler_method")
    public String handlerMethod;

    /**

     */
    @SerializedName("input_schema")
    public String inputSchema;

    /**

     */
    @SerializedName("output_schema")
    public String outputSchema;

    /**

     */
    @SerializedName("path_params")
    public String[] pathParams;

    /**

     */
    public String markdown;

    /**
     * Public constructor
     */
    public RouteV3() {
        httpMethod = "";
        urlPattern = "";
        summary = "";
        apiName = "";
        handlerClass = "";
        handlerMethod = "";
        inputSchema = "";
        outputSchema = "";
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
