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

public class KMeansV3 extends ClusteringModelBuilderSchema {

    /*------------------------------------------------------------------------------------------------------------------
    //                                                  INHERITED
    //------------------------------------------------------------------------------------------------------------------

    // Model builder parameters.
    public KMeansParametersV3 parameters;

    // The algo name for this ModelBuilder.
    public String algo;

    // The pretty algo name for this ModelBuilder (e.g., Generalized Linear Model, rather than GLM).
    public String algoFullName;

    // Model categories this ModelBuilder can build.
    public ModelCategory[] canBuild;

    // Indicator whether the model is supervised or not.
    public boolean supervised;

    // Should the builder always be visible, be marked as beta, or only visible if the user starts up with the
    // experimental flag?
    public ModelBuilderBuilderVisibility visibility;

    // Job Key
    public JobV3 job;

    // Parameter validation messages
    public ValidationMessageV3[] messages;

    // Count of parameter validation errors
    public int errorCount;

    // HTTP status to return for this build.
    public int __httpStatus;

    // Comma-separated list of JSON field paths to exclude from the result, used like:
    // "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
    public String _excludeFields;

    */

    /**
     * Public constructor
     */
    public KMeansV3() {
        algo = "";
        algoFullName = "";
        supervised = false;
        errorCount = 0;
        __httpStatus = 0;
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
