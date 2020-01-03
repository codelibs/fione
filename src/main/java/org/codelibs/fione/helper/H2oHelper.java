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

import java.io.IOException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.function.BiConsumer;
import java.util.function.Consumer;

import javax.annotation.PostConstruct;

import org.codelibs.core.exception.IORuntimeException;
import org.codelibs.fione.h2o.bindings.H2oApi;
import org.codelibs.fione.h2o.bindings.pojos.AutoMLBuildControlV99;
import org.codelibs.fione.h2o.bindings.pojos.AutoMLBuildModelsV99;
import org.codelibs.fione.h2o.bindings.pojos.AutoMLBuildSpecV99;
import org.codelibs.fione.h2o.bindings.pojos.AutoMLInputV99;
import org.codelibs.fione.h2o.bindings.pojos.FrameKeyV3;
import org.codelibs.fione.h2o.bindings.pojos.FramesListV3;
import org.codelibs.fione.h2o.bindings.pojos.FramesV3;
import org.codelibs.fione.h2o.bindings.pojos.ImportFilesV3;
import org.codelibs.fione.h2o.bindings.pojos.JobKeyV3;
import org.codelibs.fione.h2o.bindings.pojos.JobsV3;
import org.codelibs.fione.h2o.bindings.pojos.LeaderboardV99;
import org.codelibs.fione.h2o.bindings.pojos.ModelKeyV3;
import org.codelibs.fione.h2o.bindings.pojos.ModelMetricsListSchemaV3;
import org.codelibs.fione.h2o.bindings.pojos.ModelsV3;
import org.codelibs.fione.h2o.bindings.pojos.ParseSetupV3;
import org.codelibs.fione.h2o.bindings.pojos.ParseV3;
import org.codelibs.fione.h2o.bindings.pojos.RapidsSchemaV3;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.AutoMLBuilder;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.Frames;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.Jobs;

import okhttp3.Interceptor;
import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

public class H2oHelper {

    protected String endpoint;

    protected int connectTimeout = 15;

    protected int writeTimeout = 60;

    protected int readTimeout = 60;

    protected String secretKeyId;

    protected String secretAccessKey;

    private H2oApi h2o;

    private final List<Interceptor> httpInterceptorList = new ArrayList<>();

    @PostConstruct
    public void init() {
        h2o = new H2oApi(endpoint).connectTimeout(connectTimeout).readTimeout(readTimeout).writeTimeout(writeTimeout);
        httpInterceptorList.stream().forEach(h2o::addInterceptor);
        //  if (StringUtil.isNotBlank(secretKeyId) && StringUtil.isNotBlank(secretAccessKey)) {
        //      new Callable<>(h2o.setS3Credentials(secretKeyId, secretAccessKey)).execute((call, res) -> {
        //          if (res.code() == 200) {
        //              logger.info("Use S3 credentials.");
        //          } else {
        //              logger.warn("Failed to set S3 credentials: {}", res);
        //          }
        //      }, (call, t) -> {
        //          logger.warn("Failed to set S3 credentials.", t);
        //      });
        //  }
    }

    public void setEndpoint(final String endpoint) {
        this.endpoint = endpoint;
    }

    public Callable<ImportFilesV3> importFiles(final String path) {
        return new Callable<>(h2o.importFiles(path));
    }

    public Callable<FramesListV3> getFrames(final FrameKeyV3 frameId) {
        return new Callable<>(h2o.frames(frameId));
    }

    public Callable<FramesListV3> getFrames(final String frameId) {
        return getFrames(new FrameKeyV3(frameId));
    }

    public Callable<FramesV3> deleteFrame(final FrameKeyV3 frameId) {
        return new Callable<>(h2o.deleteFrame(frameId));
    }

    public Callable<FramesV3> deleteFrame(final String frameId) {
        return deleteFrame(new FrameKeyV3(frameId));
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

    public Callable<LeaderboardV99> getLeaderboard(final String projectName) {
        return new Callable<>(h2o.leaderboard(projectName));
    }

    public Callable<ModelsV3> getModel(final ModelKeyV3 model) {
        return new Callable<>(h2o.model(model));
    }

    public Callable<ModelMetricsListSchemaV3> predict(final ModelKeyV3 model, final FrameKeyV3 frame) {
        return new Callable<>(h2o.predict(model, frame));
    }

    public Callable<ModelMetricsListSchemaV3> predict(final String modelId, final String frameId) {
        return predict(new ModelKeyV3(modelId), new FrameKeyV3(frameId));
    }

    public Callable<JobsV3> getJobs(final JobKeyV3 jobId) {
        return new Callable<>(h2o.jobs(jobId));
    }

    public Callable<JobsV3> getJobs(final String jobId) {
        return getJobs(new JobKeyV3(jobId));
    }

    public Callable<RapidsSchemaV3> bindFrames(final FrameKeyV3 destinationFrame, final FrameKeyV3[] sourceFrames) {
        final StringBuilder buf = new StringBuilder(100);
        buf.append("(assign ").append(H2oApi.keyToString(destinationFrame)).append(" (cbind");
        Arrays.stream(sourceFrames).map(H2oApi::keyToString).forEach(s -> buf.append(' ').append(s));
        buf.append("))");
        return new Callable<>(h2o.rapidsExec(buf.toString()));
    }

    public Callable<RapidsSchemaV3> bindFrames(final String destinationFrame, final String[] sourceFrames) {
        return bindFrames(new FrameKeyV3(destinationFrame), Arrays.stream(sourceFrames).map(FrameKeyV3::new)
                .toArray(n -> new FrameKeyV3[n]));
    }

    public Callable<FramesV3> exportFrame(final FrameKeyV3 frame, final String path, final boolean overwrite) {
        final FramesV3 params = new FramesV3();
        params.frameId = frame;
        params.path = path;
        params.force = overwrite;
        params.compression = null;
        return new Callable<>(h2o.exportFrame(params));
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

        public void execute(final Consumer<Response<T>> onResponse, final Consumer<Throwable> onFailure) {
            execute((x, res) -> onResponse.accept(res), (x, t) -> onFailure.accept(t));
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

        public Response<T> execute() {
            try {
                return call.execute();
            } catch (final IOException e) {
                throw new IORuntimeException(e);
            }
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

    public void addHttpInterceptor(final Interceptor interceptor) {
        httpInterceptorList.add(interceptor);
    }

}
