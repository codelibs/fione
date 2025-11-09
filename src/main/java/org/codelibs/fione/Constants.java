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
package org.codelibs.fione;

import java.nio.charset.Charset;
import java.nio.charset.StandardCharsets;

public class Constants {
    private Constants() {
        // Utility class - prevent instantiation
    }

    // Character encoding constants (previously inherited from Fess)
    public static final Charset UTF_8_CHARSET = StandardCharsets.UTF_8;
    public static final String UTF_8 = "UTF-8";

    // Fione-specific constants
    public static final String REGRESSION_TYPE = "r";

    public static final String MULTICLASS_TYPE = "m";

    public static final String BINARYCLASS_TYPE = "b";

    public static final String CHART_MAX_ITEM_SIZE = "fione.chart.max_item_size";

}
