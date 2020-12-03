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
package org.codelibs.fione.h2o.bindings.builder;

import org.codelibs.core.lang.StringUtil;
import org.codelibs.fione.h2o.bindings.pojos.AutoMLInputV99;
import org.codelibs.fione.h2o.bindings.pojos.Automlapischemas3AutoMLBuildSpecAutoMLMetricProvider;
import org.codelibs.fione.h2o.bindings.pojos.ColSpecifierV3;
import org.codelibs.fione.h2o.bindings.pojos.FrameKeyV3;

public class AutoMLInputBuilder {

    public static Context create() {
        return new Context();
    }

    public static class Context {
        AutoMLInputV99 data = new AutoMLInputV99();

        public AutoMLInputV99 build() {
            return data;
        }

        public Context blendingFrame(final FrameKeyV3 blendingFrame) {
            data.blendingFrame = blendingFrame;
            return this;
        }

        public Context blendingFrame(final String name) {
            data.blendingFrame = newFrameKey(name);
            return this;
        }

        public Context foldColumn(final ColSpecifierV3 foldColumn) {
            data.foldColumn = foldColumn;
            return this;
        }

        public Context foldColumn(final String columnName, final String[] isMemberOfFrames) {
            final var colSpecifier = new ColSpecifierV3();
            colSpecifier.columnName = columnName;
            colSpecifier.isMemberOfFrames = isMemberOfFrames;
            data.foldColumn = colSpecifier;
            return this;
        }

        public Context ignoredColumns(final String[] ignoredColumns) {
            data.ignoredColumns = ignoredColumns;
            return this;
        }

        public Context leaderboardFrame(final FrameKeyV3 leaderboardFrame) {
            data.leaderboardFrame = leaderboardFrame;
            return this;
        }

        public Context leaderboardFrame(final String name) {
            data.leaderboardFrame = newFrameKey(name);
            return this;
        }

        public Context responseColumn(final ColSpecifierV3 responseColumn) {
            data.responseColumn = responseColumn;
            return this;
        }

        public Context responseColumn(final String columnName, final String[] isMemberOfFrames) {
            final var colSpecifier = new ColSpecifierV3();
            colSpecifier.columnName = columnName;
            colSpecifier.isMemberOfFrames = isMemberOfFrames == null ? StringUtil.EMPTY_STRINGS : isMemberOfFrames;
            data.responseColumn = colSpecifier;
            return this;
        }

        public Context sortMetric(final Automlapischemas3AutoMLBuildSpecAutoMLMetricProvider sortMetric) {
            data.sortMetric = sortMetric;
            return this;
        }

        public Context trainingFrame(final FrameKeyV3 trainingFrame) {
            data.trainingFrame = trainingFrame;
            return this;
        }

        public Context trainingFrame(final String name) {
            data.trainingFrame = newFrameKey(name);
            return this;
        }

        public Context validationFrame(final FrameKeyV3 validationFrame) {
            data.validationFrame = validationFrame;
            return this;
        }

        public Context validationFrame(final String name) {
            data.validationFrame = newFrameKey(name);
            return this;
        }

        public Context weightsColumn(final ColSpecifierV3 weightsColumn) {
            data.weightsColumn = weightsColumn;
            return this;
        }

        public Context weightsColumn(final String columnName, final String[] isMemberOfFrames) {
            final var colSpecifier = new ColSpecifierV3();
            colSpecifier.columnName = columnName;
            colSpecifier.isMemberOfFrames = isMemberOfFrames;
            data.weightsColumn = colSpecifier;
            return this;
        }

        private FrameKeyV3 newFrameKey(final String name) {
            final var frameKey = new FrameKeyV3();
            frameKey.name = name;
            frameKey.type = "Key<Frame>";
            frameKey.url = "/3/Frames/" + name;
            return frameKey;
        }
    }
}
