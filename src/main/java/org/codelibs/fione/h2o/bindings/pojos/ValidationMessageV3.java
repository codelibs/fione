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
package org.codelibs.fione.h2o.bindings.pojos;

import com.google.gson.Gson;
import com.google.gson.annotations.SerializedName;

public class ValidationMessageV3 extends SchemaV3 {

    /**
     * Type of validation message (ERROR, WARN, INFO, HIDE)
     */
    @SerializedName("message_type")
    public String messageType;

    /**
     * Field to which the message applies
     */
    @SerializedName("field_name")
    public String fieldName;

    /**
     * Message text
     */
    public String message;

    /**
     * Public constructor
     */
    public ValidationMessageV3() {
        messageType = "";
        fieldName = "";
        message = "";
    }

    /**
     * Return the contents of this object as a JSON String.
     */
    @Override
    public String toString() {
        return new Gson().toJson(this);
    }

}
