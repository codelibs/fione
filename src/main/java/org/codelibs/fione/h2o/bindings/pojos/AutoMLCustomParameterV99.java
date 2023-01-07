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

import com.google.gson.GsonBuilder;

public class AutoMLCustomParameterV99 {

    /**
     * Scope of application of the parameter (specific algo, or any algo).
     */
    public Automlapischemas3AutoMLBuildSpecScopeProvider scope;

    /**
     * Name of the model parameter.
     */
    public String name;

    /**
     * Value of the model parameter.
     */
    public Object value;

    /**
     * Public constructor
     */
    public AutoMLCustomParameterV99() {
        this(null, "", null);
    }

    public AutoMLCustomParameterV99(final Automlapischemas3AutoMLBuildSpecScopeProvider scope, final String name, final Object value) {
        this.scope = scope;
        this.name = name;
        this.value = value;
    }

    /**
     * Return the contents of this object as a JSON String.
     */
    @Override
    public String toString() {
        return new GsonBuilder().serializeSpecialFloatingPointValues().create().toJson(this);
    }

}
