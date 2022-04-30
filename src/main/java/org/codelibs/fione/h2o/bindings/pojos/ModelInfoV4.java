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

import com.google.gson.Gson;
import com.google.gson.annotations.SerializedName;

public class ModelInfoV4 extends OutputSchemaV4 {

    /**
     * Algorithm name, such as 'gbm', 'deeplearning', etc.
     */
    public String algo;

    /**
     * Development status of the algorithm: alpha, beta, or stable.
     */
    public String maturity;

    /**
     * Does the model support generation of POJOs?
     */
    @SerializedName("have_pojo")
    public boolean havePojo;

    /**
     * Does the model support generation of MOJOs?
     */
    @SerializedName("have_mojo")
    public boolean haveMojo;

    /**
     * Mojo version number for this algorithm.
     */
    @SerializedName("mojo_version")
    public String mojoVersion;

    /*------------------------------------------------------------------------------------------------------------------
    //                                                  INHERITED
    //------------------------------------------------------------------------------------------------------------------

    // Url describing the schema of the current object.
    public String __schema;

    */

    /**
     * Public constructor
     */
    public ModelInfoV4() {
        algo = "";
        maturity = "";
        havePojo = false;
        haveMojo = false;
        mojoVersion = "";
        __schema = "/4/schemas/ModelInfoV4";
    }

    /**
     * Return the contents of this object as a JSON String.
     */
    @Override
    public String toString() {
        return new Gson().toJson(this);
    }

}
