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
package org.codelibs.fione.entity;

import java.util.HashMap;
import java.util.Map;

import org.lastaflute.taglib.function.LaFunctions;

public class ChartData {

    private String axisName;

    private final Map<String, Object[]> columnMap = new HashMap<>();

    private final Map<String, Object> columnTypeMap = new HashMap<>();

    private final Map<String, Map<String, Object>> axisMap = new HashMap<>();

    private final Map<String, Object> sizeMap = new HashMap<>();

    private boolean axisRotated;

    public void addColumn(final String name, final Object[] values) {
        columnMap.put(name, values);
    }

    public void addColumn(final String name, final Object[] values, final String type) {
        addColumn(name, values);
        columnTypeMap.put(name, type);
    }

    public String getColumnData() {
        final StringBuilder buf = new StringBuilder(1000);
        buf.append('[');
        columnMap.entrySet().forEach(e -> {
            buf.append("[\"").append(LaFunctions.h(e.getKey())).append('\"');
            for (final Object value : e.getValue()) {
                if (value instanceof Number) {
                    buf.append(',').append(value);
                } else {
                    buf.append(",\"").append(value).append('\"');
                }
            }
            buf.append("],");
        });
        buf.append(']');
        return buf.toString();
    }

    public String getColumnTypeData() {
        return toJsonString(columnTypeMap);
    }

    public void setAxisName(final String name) {
        axisName = name;
    }

    public String getAxisName() {
        return axisName;
    }

    public void addAxisLabel(final String axis, final String value) {
        addAxisInfo(axis, "label", value);
    }

    public void addAxisType(final String axis, final String value) {
        addAxisInfo(axis, "type", value);
    }

    protected void addAxisInfo(final String axis, final String name, final String value) {
        Map<String, Object> params = axisMap.get(axis);
        if (params == null) {
            params = new HashMap<>();
            axisMap.put(axis, params);
        }
        params.put(name, value);
    }

    public void setAxisRotated(final boolean rotated) {
        this.axisRotated = rotated;
    }

    public String getAxisData() {
        final StringBuilder buf = new StringBuilder(100);
        buf.append('{');
        if (axisRotated) {
            buf.append("rotated:true,");
        }
        axisMap.entrySet().forEach(e -> {
            buf.append(LaFunctions.h(e.getKey())).append(':');
            buf.append(toJsonString(e.getValue())).append(',');
        });
        buf.append('}');
        return buf.toString();
    }

    protected String toJsonString(final Map<String, Object> map) {
        final StringBuilder buf = new StringBuilder(1000);
        buf.append('{');
        map.entrySet().forEach(e -> {
            buf.append(LaFunctions.h(e.getKey())).append(':');
            final Object value = e.getValue();
            if (value instanceof Number) {
                buf.append(value.toString());
            } else if (value instanceof Boolean) {
                buf.append(((Boolean) value).booleanValue());
            } else {
                buf.append('\"').append(value).append('\"');
            }
            buf.append(',');
        });
        buf.append('}');
        return buf.toString();
    }

    public void setHeight(final int heigth) {
        sizeMap.put("height", heigth);
    }

    public String getSizeData() {
        return toJsonString(sizeMap);
    }
}
