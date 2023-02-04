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

public class PSVMModelV3 extends ModelSchemaV3<PSVMParametersV3, PSVMModelOutputV3> {

    /*------------------------------------------------------------------------------------------------------------------
    //                                                  INHERITED
    //------------------------------------------------------------------------------------------------------------------

    // The build parameters for the model (e.g. K for KMeans).
    public PSVMParametersV3 parameters;

    // The build output for the model (e.g. the cluster centers for KMeans).
    public PSVMModelOutputV3 output;

    // Compatible frames, if requested
    public String[] compatibleFrames;

    // Checksum for all the things that go into building the Model.
    public long checksum;

    // Model key
    public ModelKeyV3 modelId;

    // The algo name for this Model.
    public String algo;

    // The pretty algo name for this Model (e.g., Generalized Linear Model, rather than GLM).
    public String algoFullName;

    // The response column name for this Model (if applicable). Is null otherwise.
    public String responseColumnName;

    // The treatment column name for this Model (if applicable). Is null otherwise.
    public String treatmentColumnName;

    // The Model's training frame key
    public FrameKeyV3 dataFrame;

    // Timestamp for when this model was completed
    public long timestamp;

    // Indicator, whether export to POJO is available
    public boolean havePojo;

    // Indicator, whether export to MOJO is available
    public boolean haveMojo;

    */

    /**
     * Public constructor
     */
    public PSVMModelV3() {
        checksum = 0L;
        algo = "";
        algoFullName = "";
        responseColumnName = "";
        treatmentColumnName = "";
        timestamp = 0L;
        havePojo = false;
        haveMojo = false;
    }

    /**
     * Return the contents of this object as a JSON String.
     */
    @Override
    public String toString() {
        return new GsonBuilder().serializeSpecialFloatingPointValues().create().toJson(this);
    }

}
