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
package org.codelibs.fione.util;

import java.net.URLEncoder;

import org.apache.commons.codec.binary.Base64;
import org.codelibs.core.lang.StringUtil;
import org.codelibs.fess.crawler.Constants;

public class StringCodecUtil {

    public static String encodeUrlSafe(final String value) {
        return Base64.encodeBase64URLSafeString(value.getBytes(Constants.UTF_8_CHARSET));
    }

    public static String decode(final String value) {
        return new String(Base64.decodeBase64(value), Constants.UTF_8_CHARSET);
    }

    public static String normalize(final String value) {
        return URLEncoder.encode(value, Constants.UTF_8_CHARSET).replaceAll("[+%]", StringUtil.EMPTY);
    }
}
