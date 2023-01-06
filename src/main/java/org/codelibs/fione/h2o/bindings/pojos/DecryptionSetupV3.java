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
package org.codelibs.fione.h2o.bindings.pojos;

import com.google.gson.GsonBuilder;
import com.google.gson.annotations.SerializedName;

public class DecryptionSetupV3 extends RequestSchemaV3 {

    /**
     * Target key for the Decryption Tool
     */
    @SerializedName("decrypt_tool_id")
    public DecryptionToolKeyV3 decryptToolId;

    /**
     * Implementation of the Decryption Tool
     */
    @SerializedName("decrypt_impl")
    public String decryptImpl;

    /**
     * Location of Java Keystore
     */
    @SerializedName("keystore_id")
    public FrameKeyV3 keystoreId;

    /**
     * Keystore type
     */
    @SerializedName("keystore_type")
    public String keystoreType;

    /**
     * Key alias
     */
    @SerializedName("key_alias")
    public String keyAlias;

    /**
     * Key password
     */
    public String password;

    /**
     * Specification of the cipher (and padding)
     */
    @SerializedName("cipher_spec")
    public String cipherSpec;

    /*------------------------------------------------------------------------------------------------------------------
    //                                                  INHERITED
    //------------------------------------------------------------------------------------------------------------------

    // Comma-separated list of JSON field paths to exclude from the result, used like:
    // "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
    public String _excludeFields;

    */

    /**
     * Public constructor
     */
    public DecryptionSetupV3() {
        decryptImpl = "water.parser.GenericDecryptionTool";
        keystoreType = "";
        keyAlias = "";
        password = "";
        cipherSpec = "";
        _excludeFields = "";
    }

    /**
     * Return the contents of this object as a JSON String.
     */
    @Override
    public String toString() {
        return new GsonBuilder().serializeSpecialFloatingPointValues().create().toJson(this);
    }

}
