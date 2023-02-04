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
package org.codelibs.fione.h2o.bindings.proxies.retrofit;

import org.codelibs.fione.h2o.bindings.pojos.Word2VecSynonymsV3;

import retrofit2.Call;
import retrofit2.http.GET;
import retrofit2.http.Query;

public interface Word2VecSynonyms {

    /**
     * Find synonyms using a word2vec model
     *   @param model Source word2vec Model
     *   @param word Target word to find synonyms for
     *   @param count Number of synonyms
     *   @param synonyms Synonymous words
     *   @param scores Similarity scores
     */
    @GET("/3/Word2VecSynonyms")
    Call<Word2VecSynonymsV3> findSynonyms(@Query("model") String model, @Query("word") String word, @Query("count") int count,
            @Query("synonyms") String[] synonyms, @Query("scores") double[] scores);

    @GET("/3/Word2VecSynonyms")
    Call<Word2VecSynonymsV3> findSynonyms(@Query("model") String model, @Query("word") String word, @Query("count") int count);

}
