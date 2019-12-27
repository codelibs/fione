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

public class StepDefinitionV99 {

    /**
     * Name of the step provider (usually, this is also the name of an algorithm).
     */
    public String name;

    /**
     * An alias representing a predefined list of steps to be executed.
     */
    public H2oautomlStepDefinitionAlias alias;

    /**
     * The list of steps to be executed (Mutually exclusive with alias).
     */
    public StepV99[] steps;

    /**
     * Public constructor
     */
    public StepDefinitionV99() {
        name = "";
    }

    /**
     * Return the contents of this object as a JSON String.
     */
    @Override
    public String toString() {
        return new GsonBuilder().serializeSpecialFloatingPointValues().create().toJson(this);
    }

}
