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
package org.codelibs.fione.entity;

import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

import org.apache.commons.text.StringEscapeUtils;

import com.google.common.collect.Lists;

public class ChartData {

    private String axisName;

    private final Map<String, Object[]> columnMap = new LinkedHashMap<>();

    private final Map<String, Object> columnTypeMap = new LinkedHashMap<>();

    private final Map<String, Map<String, Object>> axisMap = new LinkedHashMap<>();

    private final Map<String, Object> sizeMap = new LinkedHashMap<>();

    public void addColumn(final String name, final Object[] values) {
        columnMap.put(name, values);
    }

    public void addColumn(final String name, final Object[] values, final String type) {
        addColumn(name, values);
        columnTypeMap.put(name, type);
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
        var params = axisMap.get(axis);
        if (params == null) {
            params = new HashMap<>();
            axisMap.put(axis, params);
        }
        params.put(name, value);
    }

    public void setHeight(final int heigth) {
        sizeMap.put("height", heigth);
    }

    public int getHeight() {
        final var value = sizeMap.get("height");
        if (value instanceof Number) {
            return ((Number) value).intValue() + 100;
        }
        return 400;
    }

    public List<Map<String, Object>> getXAxis() {
        final var buf = new StringBuilder(1000);
        buf.append('[');
        final var values = columnMap.get(axisName);
        if (values != null) {
            for (final Object value : values) {
                toJsonString(buf, value, ",");
            }
        }
        buf.append(']');
        final Map<String, Object> params = new HashMap<>();
        params.put("data", buf.toString());
        params.put("name", axisName);
        return Lists.newArrayList(params);
    }

    public List<Map<String, Object>> getYAxis() {
        return columnMap.entrySet().stream().filter(e -> !e.getKey().equals(axisName)).map(e -> {
            final Map<String, Object> params = new HashMap<>();
            params.put("name", e.getKey());
            return params;
        }).collect(Collectors.toList());
    }

    public List<Map<String, Object>> getSeries() {
        return columnMap.entrySet().stream().filter(e -> !e.getKey().equals(axisName)).map(e -> {
            final var buf = new StringBuilder(1000);
            buf.append('[');
            for (final Object value : e.getValue()) {
                toJsonString(buf, value, ",");
            }
            buf.append("]");
            final Map<String, Object> params = new HashMap<>();
            params.put("data", buf.toString());
            return params;
        }).collect(Collectors.toList());
    }

    private void toJsonString(final StringBuilder buf, final Object value, final String end) {
        if (value instanceof Number) {
            buf.append(value).append(end);
        } else if (value instanceof Map) {
            buf.append('{');
            @SuppressWarnings("unchecked")
            final var map = (Map<String, Object>) value;
            map.entrySet().forEach(e -> {
                toJsonString(buf, e.getKey(), ":");
                toJsonString(buf, e.getValue(), ",");
            });
            buf.append('}').append(end);
        } else if (value != null) {
            buf.append("\"").append(StringEscapeUtils.escapeJson(value.toString())).append('\"').append(end);
        } else {
            buf.append("null").append(end);
        }
    }
}
