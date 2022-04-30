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

public class StepV99 {

    /**
     * The id of the step (must be unique per step provider).
     */
    public String id;

    /**
     * The group of execution of the given step (groups are executed in ascending order of priority).Steps with group=0
     * are skipped. Defaults to -1 to use the default group assigned to the step id.
     */
    public int group;

    /**
     * The relative weight for the given step (can impact time and/or number of models allocated for this step). Steps
     * with weight=0 are skipped. Defaults to -1 to use the default weight assigned to the step id.
     */
    public int weight;

    /**
     * Public constructor
     */
    public StepV99() {
        id = "";
        group = -1;
        weight = -1;
    }

    /**
     * Return the contents of this object as a JSON String.
     */
    @Override
    public String toString() {
        return new Gson().toJson(this);
    }

}
