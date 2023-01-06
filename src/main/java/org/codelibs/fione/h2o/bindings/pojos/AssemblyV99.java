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

public class AssemblyV99 extends RequestSchemaV3 {

    /**
     * A list of steps describing the assembly line.
     */
    public String[] steps;

    /**
     * Input Frame for the assembly.
     */
    public FrameKeyV3 frame;

    /**
     * The name of the file and generated class
     */
    @SerializedName("pojo_name")
    public String pojoName;

    /**
     * The key of the Assembly object to retrieve from the DKV.
     */
    @SerializedName("assembly_id")
    public String assemblyId;

    /**
     * Output of the assembly line.
     */
    public FrameKeyV3 result;

    /**
     * A Key to the fit Assembly data structure
     */
    public AssemblyKeyV3 assembly;

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
    public AssemblyV99() {
        pojoName = "";
        assemblyId = "";
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
