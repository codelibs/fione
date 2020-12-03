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
package org.codelibs.fione.h2o.bindings.pojos;

import java.lang.reflect.Field;
import java.text.DateFormat;
import java.text.SimpleDateFormat;
import java.util.Arrays;
import java.util.Date;
import java.util.stream.Collectors;

import org.codelibs.core.CoreLibConstants;
import org.codelibs.core.lang.StringUtil;
import org.codelibs.fess.taglib.FessFunctions;

import com.google.gson.GsonBuilder;

public class SchemaV3 {

    /**
     * Public constructor
     */
    public SchemaV3() {
    }

    /**
     * Return the contents of this object as a JSON String.
     */
    @Override
    public String toString() {
        return new GsonBuilder().serializeSpecialFloatingPointValues().create().toJson(this);
    }

    protected transient String[] fieldNames;

    protected transient Object[] fieldValues;

    public String[] getFieldNames() {
        if (fieldNames == null) {
            fieldNames = Arrays.stream(getClass().getFields()).map(Field::getName).toArray(n -> new String[n]);
        }
        return fieldNames;
    }

    public Object[] getFieldValues() {
        if (fieldValues == null) {
            fieldValues =
                    Arrays.stream(getFieldNames())
                            .map(s -> {
                                try {
                                    final var value = getClass().getField(s).get(this);
                                    if (value instanceof Number) {
                                        if (s.equals("runTime")) {
                                            return FessFunctions.formatDuration(((Number) value).longValue());
                                        } else if (s.endsWith("Time")) {
                                            final DateFormat formatter = new SimpleDateFormat(CoreLibConstants.DATE_FORMAT_ISO_8601_EXTEND);
                                            return formatter.format(new Date(((Number) value).longValue()));
                                        }
                                    } else if (value instanceof String[]) {
                                        return Arrays.stream((String[]) value).collect(Collectors.joining(", "));
                                    } else if (value instanceof String[][]) {
                                        return Arrays.stream((String[][]) value)
                                                .map(v -> "[" + Arrays.stream(v).collect(Collectors.joining(", ")) + "]")
                                                .collect(Collectors.joining(", "));
                                    } else if (value instanceof KeyV3) {
                                        return ((KeyV3) value).name;
                                    } else if (value instanceof KeyV3[]) {
                                        return Arrays.stream((KeyV3[]) value).map(k -> k.name).collect(Collectors.joining(", "));
                                    }
                                    return value;
                                } catch (final Exception e) {
                                    return StringUtil.EMPTY;
                                }
                            }).toArray(n -> new Object[n]);
        }
        return fieldValues;
    }
}
