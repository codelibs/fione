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

public class MakeGLMModelV3 extends SchemaV3 {

    /**
     * source model
     */
    public ModelKeyV3 model;

    /**
     * destination key
     */
    public ModelKeyV3 dest;

    /**
     * coefficient names
     */
    public String[] names;

    /**
     * new glm coefficients
     */
    public double[] beta;

    /**
     * decision threshold for label-generation
     */
    public float threshold;

    /**
     * Public constructor
     */
    public MakeGLMModelV3() {
        threshold = 0.5f;
    }

    /**
     * Return the contents of this object as a JSON String.
     */
    @Override
    public String toString() {
        return new GsonBuilder().serializeSpecialFloatingPointValues().create().toJson(this);
    }

}
