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
package org.codelibs.fione.taglib;

import org.codelibs.fione.util.StringCodecUtil;

public class FioneFunctions {

    protected FioneFunctions() {
        // nothing
    }

    public static String frameName(final String frameId) {
        if (frameId == null) {
            return null;
        }
        String name = frameId;
        final int pos = frameId.lastIndexOf('.');
        if (pos != -1) {
            name = frameId.substring(0, pos);
        }
        final String[] values = name.split("_");
        if (values.length == 2) {
            return StringCodecUtil.decode(values[1]);
        }
        return frameId;
    }
}
