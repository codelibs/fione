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
package org.codelibs.fione.h2o.bindings.builder;

import org.codelibs.fione.h2o.bindings.pojos.AutoMLStoppingCriteriaV99;
import org.codelibs.fione.h2o.bindings.pojos.ScoreKeeperStoppingMetric;

public class AutoMLStoppingCriteriaBuilder {

    public static Context create() {
        return new Context();
    }

    public static class Context {
        AutoMLStoppingCriteriaV99 data = new AutoMLStoppingCriteriaV99();

        public AutoMLStoppingCriteriaV99 build() {
            return data;
        }

        public Context maxModels(final int maxModels) {
            data.maxModels = maxModels;
            return this;
        }

        public Context maxRuntimeSecs(final double maxRuntimeSecs) {
            data.maxRuntimeSecs = maxRuntimeSecs;
            return this;
        }

        public Context maxRuntimeSecsPerModel(final double maxRuntimeSecsPerModel) {
            data.maxRuntimeSecsPerModel = maxRuntimeSecsPerModel;
            return this;
        }

        public Context seed(final int seed) {
            data.seed = seed;
            return this;
        }

        public Context stoppingMetric(final ScoreKeeperStoppingMetric stoppingMetric) {
            data.stoppingMetric = stoppingMetric;
            return this;
        }

        public Context stoppingRounds(final int stoppingRounds) {
            data.stoppingRounds = stoppingRounds;
            return this;
        }

        public Context stoppingTolerance(final double stoppingTolerance) {
            data.stoppingTolerance = stoppingTolerance;
            return this;
        }
    }
}
