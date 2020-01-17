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
package org.codelibs.fione.entity;

import org.apache.commons.codec.binary.Base64;
import org.codelibs.fess.crawler.Constants;
import org.codelibs.fione.h2o.bindings.pojos.ParseV3;

import com.google.gson.GsonBuilder;

public class DataSet {

    public static final String TRAIN = "train";

    public static final String TEST = "test";

    private String id;

    private String name;

    private String path;

    private String type = TRAIN;

    private ParseV3 schema;

    public DataSet() {
        // no-op
    }

    public DataSet(final String id) {
        this.id = id;
        this.name = new String(Base64.decodeBase64(id), Constants.UTF_8_CHARSET);
    }

    public String getName() {
        return name;
    }

    public void setName(final String name) {
        this.name = name;
    }

    public ParseV3 getSchema() {
        return schema;
    }

    public void setSchema(final ParseV3 meta) {
        this.schema = meta;
    }

    public String getId() {
        return id;
    }

    public void setId(final String id) {
        this.id = id;
    }

    public String getPath() {
        return path;
    }

    public void setPath(final String path) {
        this.path = path;
    }

    public String getType() {
        return type;
    }

    public void setType(final String type) {
        this.type = type;
    }

    @Override
    public String toString() {
        return new GsonBuilder().serializeSpecialFloatingPointValues().create().toJson(this);
    }

}
