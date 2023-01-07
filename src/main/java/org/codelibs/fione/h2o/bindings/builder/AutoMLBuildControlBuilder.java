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

import org.codelibs.fione.h2o.bindings.pojos.AutoMLBuildControlV99;
import org.codelibs.fione.h2o.bindings.pojos.AutoMLStoppingCriteriaV99;

public class AutoMLBuildControlBuilder {

    public static Context create() {
        return new Context();
    }

    public static class Context {
        AutoMLBuildControlV99 data = new AutoMLBuildControlV99();

        public AutoMLBuildControlV99 build() {
            return data;
        }

        public Context balanceClasses(final boolean balanceClasses) {
            data.balanceClasses = balanceClasses;
            return this;
        }

        public Context classSamplingFactors(final float[] classSamplingFactors) {
            data.classSamplingFactors = classSamplingFactors;
            return this;
        }

        public Context exportCheckpointsDir(final String exportCheckpointsDir) {
            data.exportCheckpointsDir = exportCheckpointsDir;
            return this;
        }

        public Context keepCrossValidationFoldAssignment(final boolean keepCrossValidationFoldAssignment) {
            data.keepCrossValidationFoldAssignment = keepCrossValidationFoldAssignment;
            return this;
        }

        public Context keepCrossValidationModels(final boolean keepCrossValidationModels) {
            data.keepCrossValidationModels = keepCrossValidationModels;
            return this;
        }

        public Context keepCrossValidationPredictions(final boolean keepCrossValidationPredictions) {
            data.keepCrossValidationPredictions = keepCrossValidationPredictions;
            return this;
        }

        public Context maxAfterBalanceSize(final float maxAfterBalanceSize) {
            data.maxAfterBalanceSize = maxAfterBalanceSize;
            return this;
        }

        public Context nfolds(final int nfolds) {
            data.nfolds = nfolds;
            return this;
        }

        public Context projectName(final String projectName) {
            data.projectName = projectName;
            return this;
        }

        public Context stoppingCriteria(final AutoMLStoppingCriteriaV99 stoppingCriteria) {
            data.stoppingCriteria = stoppingCriteria;
            return this;
        }

    }
}
