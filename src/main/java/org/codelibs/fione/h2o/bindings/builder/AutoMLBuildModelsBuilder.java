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
package org.codelibs.fione.h2o.bindings.builder;

import org.codelibs.fione.h2o.bindings.pojos.AutoMLBuildModelsV99;
import org.codelibs.fione.h2o.bindings.pojos.AutoMLCustomParameterV99;
import org.codelibs.fione.h2o.bindings.pojos.KeyValueV3;
import org.codelibs.fione.h2o.bindings.pojos.StepDefinitionV99;

public class AutoMLBuildModelsBuilder {

    public static Context create() {
        return new Context();
    }

    public static class Context {
        AutoMLBuildModelsV99 data = new AutoMLBuildModelsV99();

        public AutoMLBuildModelsV99 build() {
            return data;
        }

        public Context algoParameters(final AutoMLCustomParameterV99[] algoParameters) {
            data.algoParameters = algoParameters;
            return this;
        }

        public Context excludeAlgos(final String[] excludeAlgos) {
            data.excludeAlgos = excludeAlgos;
            return this;
        }

        public Context includeAlgos(final String[] includeAlgos) {
            data.includeAlgos = includeAlgos;
            return this;
        }

        public Context modelingPlan(final StepDefinitionV99[] modelingPlan) {
            data.modelingPlan = modelingPlan;
            return this;
        }

        public Context monotoneConstraints(final KeyValueV3[] monotoneConstraints) {
            data.monotoneConstraints = monotoneConstraints;
            return this;
        }
    }
}
