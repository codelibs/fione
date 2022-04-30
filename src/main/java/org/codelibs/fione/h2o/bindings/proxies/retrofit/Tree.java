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
package org.codelibs.fione.h2o.bindings.proxies.retrofit;

import org.codelibs.fione.h2o.bindings.pojos.TreeHandlerPlainLanguageRules;
import org.codelibs.fione.h2o.bindings.pojos.TreeV3;

import retrofit2.Call;
import retrofit2.http.GET;
import retrofit2.http.Query;

public interface Tree {

    /**
     * Obtain a traverseable representation of a specific tree
     *   @param model Key of the model the desired tree belongs to
     *   @param tree_number Index of the tree in the model.
     *   @param tree_class Name of the class of the tree. Ignored for regression and binomial.
     *   @param plain_language_rules Whether to generate plain language rules.
     */
    @GET("/3/Tree")
    Call<TreeV3> getTree(@Query("model") String model, @Query("tree_number") int tree_number, @Query("tree_class") String tree_class,
            @Query("plain_language_rules") TreeHandlerPlainLanguageRules plain_language_rules);

    @GET("/3/Tree")
    Call<TreeV3> getTree(@Query("model") String model, @Query("tree_number") int tree_number);

}
