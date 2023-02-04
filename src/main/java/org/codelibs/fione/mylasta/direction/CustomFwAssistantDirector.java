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
package org.codelibs.fione.mylasta.direction;

import java.util.List;
import java.util.function.Consumer;

import org.codelibs.fess.mylasta.direction.FessFwAssistantDirector;

public class CustomFwAssistantDirector extends FessFwAssistantDirector {
    @Override
    protected Consumer<List<String>> createMessageNameList() {
        return nameList -> {
            // order is important
            nameList.add("fione_message");
            nameList.add("fione_label");
            nameList.add("fess_message");
        };
    }
}
