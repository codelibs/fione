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
package org.codelibs.fione.helper;

import java.util.function.BiConsumer;

import javax.annotation.PostConstruct;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.codelibs.core.lang.StringUtil;
import org.codelibs.fione.h2o.bindings.H2oApi;
import org.codelibs.fione.h2o.bindings.pojos.AutoMLBuildControlV99;
import org.codelibs.fione.h2o.bindings.pojos.AutoMLBuildModelsV99;
import org.codelibs.fione.h2o.bindings.pojos.AutoMLBuildSpecV99;
import org.codelibs.fione.h2o.bindings.pojos.AutoMLInputV99;
import org.codelibs.fione.h2o.bindings.pojos.FramesV3;
import org.codelibs.fione.h2o.bindings.pojos.ImportFilesV3;
import org.codelibs.fione.h2o.bindings.pojos.JobsV3;
import org.codelibs.fione.h2o.bindings.pojos.ParseSetupV3;
import org.codelibs.fione.h2o.bindings.pojos.ParseV3;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.AutoMLBuilder;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.Frames;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.Jobs;

import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

public class H2oHelper {
    private static final Logger logger = LogManager.getLogger(H2oHelper.class);

    protected String endpoint;

    protected int connectTimeout = 15;

    protected int writeTimeout = 60;

    protected int readTimeout = 60;

    protected String secretKeyId;

    protected String secretAccessKey;

    private H2oApi h2o;

    @PostConstruct
    public void init() {
        h2o = new H2oApi(endpoint).connectTimeout(connectTimeout).readTimeout(readTimeout).writeTimeout(writeTimeout);
        if (StringUtil.isNotBlank(secretKeyId) && StringUtil.isNotBlank(secretAccessKey)) {
            new Callable<>(h2o.setS3Credentials(secretKeyId, secretAccessKey)).execute((call, res) -> {
                logger.info("Use S3 credentials.");
            }, (call, t) -> {
                logger.warn("Failed to set S3 credentials.", t);
            });
        }
    }

    public void setEndpoint(final String endpoint) {
        this.endpoint = endpoint;
    }

    public Callable<ImportFilesV3> importFiles(final String path) {
        return new Callable<>(h2o.importFiles(path));
    }

    public Callable<ParseSetupV3> setupParse(final String[] sourceFrames) {
        return new Callable<>(h2o.guessParseSetup(sourceFrames));
    }

    public Callable<ParseV3> parseFiles(final ParseV3 params) {
        return new Callable<>(h2o.parse(params));
    }

    public Callable<JobsV3> fetchJobs(final String jobId) {
        final Jobs service = h2o.getService(Jobs.class);
        final Call<JobsV3> call = service.fetch(jobId);
        return new Callable<>(call);
    }

    public Callable<FramesV3> getFrameSummary(final String frameId) {
        return new Callable<>(h2o.frameSummary(frameId));
    }

    public Callable<FramesV3> getFrameColumnSummary(final String frameId, final String column) {
        final Frames service = h2o.getService(Frames.class);
        final Call<FramesV3> call = service.columnSummary(frameId, column);
        return new Callable<>(call);
    }

    public Callable<AutoMLBuildSpecV99> runAutoML(final AutoMLBuildControlV99 buildControl, final AutoMLInputV99 inputSpec,
            final AutoMLBuildModelsV99 buildModels) {
        final AutoMLBuilder service = h2o.getService(AutoMLBuilder.class);
        final Call<AutoMLBuildSpecV99> call = service.build(buildControl, inputSpec, buildModels);
        return new Callable<>(call);
    }

    public ParseV3 convert(final ParseSetupV3 params) {
        final ParseV3 newParams = new ParseV3();
        newParams._excludeFields = params._excludeFields;
        newParams.checkHeader = params.checkHeader;
        newParams.chunkSize = params.chunkSize;
        newParams.columnNames = params.columnNames;
        newParams.columnTypes = params.columnTypes;
        newParams.customNonDataLineMarkers = params.customNonDataLineMarkers;
        newParams.decryptTool = params.decryptTool;
        newParams.destinationFrame = H2oApi.stringToFrameKey(params.destinationFrame);
        newParams.naStrings = params.naStrings;
        newParams.numberColumns = params.numberColumns;
        newParams.parseType = params.parseType;
        newParams.separator = params.separator;
        newParams.singleQuotes = params.singleQuotes;
        newParams.skippedColumns = params.skippedColumns;
        newParams.sourceFrames = params.sourceFrames;
        newParams.deleteOnDone = true;
        newParams.blocking = true;
        return newParams;
    }

    public static class Callable<T> {

        private final Call<T> call;

        protected Callable(final Call<T> call) {
            this.call = call;
        }

        public void execute(final BiConsumer<Call<T>, Response<T>> onResponse, final BiConsumer<Call<T>, Throwable> onFailure) {
            call.enqueue(new Callback<T>() {
                @Override
                public void onResponse(final Call<T> call, final Response<T> response) {
                    try {
                        onResponse.accept(call, response);
                    } catch (final Throwable t) {
                        onFailure(call, t);
                    }
                }

                @Override
                public void onFailure(final Call<T> call, final Throwable t) {
                    onFailure.accept(call, t);
                }
            });
        }
    }

    public void setConnectTimeout(final int connectTimeout) {
        this.connectTimeout = connectTimeout;
    }

    public void setWriteTimeout(final int writeTimeout) {
        this.writeTimeout = writeTimeout;
    }

    public void setReadTimeout(final int readTimeout) {
        this.readTimeout = readTimeout;
    }

    public void setSecretKeyId(final String secretKeyId) {
        this.secretKeyId = secretKeyId;
    }

    public void setSecretAccessKey(final String secretAccessKey) {
        this.secretAccessKey = secretAccessKey;
    }

}
