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
package org.codelibs.fione.taglib;

import java.util.Locale;

import org.codelibs.core.lang.StringUtil;
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

    public static String formatNumber(final Object value, final String format) {
        if (value == null) {
            return StringUtil.EMPTY;
        }
        if (StringUtil.isBlank(format)) {
            return value.toString();
        }
        final String lf = format.toLowerCase(Locale.ROOT);
        final Object arg;
        try {
            if (lf.endsWith("e") || lf.endsWith("f") || lf.endsWith("g") || lf.endsWith("a")) {
                arg = Double.valueOf(value.toString());
            } else if (lf.endsWith("d") || lf.endsWith("o") || lf.endsWith("d")) {
                arg = Long.valueOf(value.toString());
            } else if (lf.endsWith("b")) {
                arg = Boolean.valueOf(value.toString());
            } else {
                arg = value;
            }
            return String.format(format, arg).replaceFirst("0+$", "0");
        } catch (final Exception e) {
            return value.toString();
        }
    }
}
