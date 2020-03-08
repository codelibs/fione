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
import com.google.gson.annotations.SerializedName;

public class TargetEncoderTransformParametersV3 extends SchemaV3 {

    /**
     * Target Encoder model to use.
     */
    public ModelKeyV3 model;

    /**
     * Seed value
     */
    public long seed;

    /**
     * Data leakage handling strategy.
     */
    @SerializedName("data_leakage_handling")
    public H2otargetencodingTargetEncoderDataLeakageHandlingStrategy dataLeakageHandling;

    /**
     * Noise
     */
    public double noise;

    /**
     * Frame to transform
     */
    public FrameKeyV3 frame;

    /**
     * Enables or disables blending
     */
    public boolean blending;

    /**
     * Inflection point
     */
    @SerializedName("inflection_point")
    public double inflectionPoint;

    /**
     * Smoothing
     */
    public double smoothing;

    /**
     * Public constructor
     */
    public TargetEncoderTransformParametersV3() {
        seed = 0L;
        noise = 0.0;
        blending = false;
        inflectionPoint = 0.0;
        smoothing = 0.0;
    }

    /**
     * Return the contents of this object as a JSON String.
     */
    @Override
    public String toString() {
        return new GsonBuilder().serializeSpecialFloatingPointValues().create().toJson(this);
    }

}
