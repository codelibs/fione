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

public class TargetEncoderTransformParametersV3 extends SchemaV3 {

    /**
     * Target Encoder model to use.
     */
    public ModelKeyV3 model;

    /**
     * Frame to transform.
     */
    public FrameKeyV3 frame;

    /**
     * Force encoding mode for training data: when using a leakage handling strategy different from None, training data
     * should be transformed with this flag set to true (Defaults to false).
     */
    @SerializedName("as_training")
    public boolean asTraining;

    /**
     * Enables or disables blending. Defaults to the value assigned at model creation.
     */
    public boolean blending;

    /**
     * Inflection point. Defaults to the value assigned at model creation.
     */
    @SerializedName("inflection_point")
    public double inflectionPoint;

    /**
     * Smoothing. Defaults to the value assigned at model creation.
     */
    public double smoothing;

    /**
     * Noise. Defaults to the value assigned at model creation.
     */
    public double noise;

    /**
     * Public constructor
     */
    public TargetEncoderTransformParametersV3() {
        asTraining = false;
        blending = false;
        inflectionPoint = -1.0;
        smoothing = -1.0;
        noise = -2.0;
    }

    /**
     * Return the contents of this object as a JSON String.
     */
    @Override
    public String toString() {
        return new Gson().toJson(this);
    }

}
