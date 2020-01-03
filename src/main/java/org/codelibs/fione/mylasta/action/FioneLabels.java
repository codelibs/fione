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
package org.codelibs.fione.mylasta.action;

import org.codelibs.fess.mylasta.action.FessMessages;

/**
 * The keys for message.
 * @author FreeGen
 */
public class FioneLabels extends FessMessages {

    /** The serial version UID for object serialization. (Default) */
    private static final long serialVersionUID = 1L;

    /** The key of the message: Fione */
    public static final String LABELS_menu_fione = "{labels.menu_fione}";

    /** The key of the message: AutoML */
    public static final String LABELS_menu_automl = "{labels.menu_automl}";

    /** The key of the message: AutoML */
    public static final String LABELS_AUTOML = "{labels.automl}";

    /** The key of the message: Projects */
    public static final String LABELS_automl_title_details = "{labels.automl_title_details}";

    /** The key of the message: Name */
    public static final String LABELS_automl_name = "{labels.automl_name}";

    /**
     * Assert the property is not null.
     * @param property The value of the property. (NotNull)
     */
    protected void assertPropertyNotNull(String property) {
        if (property == null) {
            String msg = "The argument 'property' for message should not be null.";
            throw new IllegalArgumentException(msg);
        }
    }
}
