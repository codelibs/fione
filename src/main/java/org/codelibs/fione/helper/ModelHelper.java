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
package org.codelibs.fione.helper;

import java.io.Reader;

import jakarta.annotation.PostConstruct;

import org.codelibs.fione.exception.ModelIOException;
import org.codelibs.fione.h2o.bindings.pojos.ModelSchemaBaseV3;

import com.fasterxml.jackson.annotation.JsonAutoDetect.Visibility;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonTypeInfo;
import com.fasterxml.jackson.annotation.PropertyAccessor;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.jsontype.impl.LaissezFaireSubTypeValidator;

public class ModelHelper {

    private ObjectMapper objectMapper;

    @PostConstruct
    public void init() {
        objectMapper = new ObjectMapper();
        objectMapper.setVisibility(PropertyAccessor.ALL, Visibility.NONE);
        objectMapper.setVisibility(PropertyAccessor.FIELD, Visibility.ANY);
        objectMapper.setDefaultTyping(
                new ObjectMapper.DefaultTypeResolverBuilder(ObjectMapper.DefaultTyping.EVERYTHING, LaissezFaireSubTypeValidator.instance)//
                        .init(JsonTypeInfo.Id.CLASS, null)//
                        .inclusion(JsonTypeInfo.As.PROPERTY)//
                        .typeProperty("classType"));
        objectMapper.setSerializationInclusion(JsonInclude.Include.NON_NULL);
        objectMapper.configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false);
    }

    public String serialize(final ModelSchemaBaseV3 model) {
        try {
            return objectMapper.writeValueAsString(model);
        } catch (final JsonProcessingException e) {
            throw new ModelIOException("Failed to serialize " + model, e);
        }
    }

    public ModelSchemaBaseV3 deserialize(final Reader reader) {
        try {
            return objectMapper.readValue(reader, ModelSchemaBaseV3.class);
        } catch (final Exception e) {
            throw new ModelIOException("Failed to deserialize " + reader, e);
        }
    }
}
