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
import java.io.InputStream;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;
import java.util.function.BiConsumer;
import java.util.function.Consumer;

import javax.annotation.PostConstruct;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.codelibs.core.exception.IORuntimeException;
import org.codelibs.curl.Curl;
import org.codelibs.curl.CurlResponse;
import org.codelibs.fess.app.web.base.login.FessLoginAssist;
import org.codelibs.fess.util.ComponentUtil;
import org.codelibs.fione.exception.FioneSystemException;
import org.codelibs.fione.exception.H2oAccessException;
import org.codelibs.fione.h2o.bindings.H2oApi;
import org.codelibs.fione.h2o.bindings.pojos.AutoMLBuildControlV99;
import org.codelibs.fione.h2o.bindings.pojos.AutoMLBuildModelsV99;
import org.codelibs.fione.h2o.bindings.pojos.AutoMLBuildSpecV99;
import org.codelibs.fione.h2o.bindings.pojos.AutoMLInputV99;
import org.codelibs.fione.h2o.bindings.pojos.FrameKeyV3;
import org.codelibs.fione.h2o.bindings.pojos.FramesListV3;
import org.codelibs.fione.h2o.bindings.pojos.FramesV3;
import org.codelibs.fione.h2o.bindings.pojos.ImportFilesV3;
import org.codelibs.fione.h2o.bindings.pojos.InitIDV3;
import org.codelibs.fione.h2o.bindings.pojos.JobKeyV3;
import org.codelibs.fione.h2o.bindings.pojos.JobsV3;
import org.codelibs.fione.h2o.bindings.pojos.LeaderboardV99;
import org.codelibs.fione.h2o.bindings.pojos.ModelExportV3;
import org.codelibs.fione.h2o.bindings.pojos.ModelKeyV3;
import org.codelibs.fione.h2o.bindings.pojos.ModelMetricsListSchemaV3;
import org.codelibs.fione.h2o.bindings.pojos.ModelsV3;
import org.codelibs.fione.h2o.bindings.pojos.ParseSetupV3;
import org.codelibs.fione.h2o.bindings.pojos.ParseV3;
import org.codelibs.fione.h2o.bindings.pojos.RapidsSchemaV3;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.AutoMLBuilder;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.Frames;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.Jobs;
import org.codelibs.fione.util.StringCodecUtil;

import com.google.common.cache.CacheBuilder;
import com.google.common.cache.CacheLoader;
import com.google.common.cache.LoadingCache;
import com.google.common.cache.RemovalListener;

import okhttp3.Interceptor;
import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

public class H2oHelper {

    private static final Logger logger = LogManager.getLogger(H2oHelper.class);

    protected String endpoint;

    protected int connectTimeout = 15;

    protected int writeTimeout = 60 * 15;

    protected int readTimeout = 60 * 15;

    protected String secretKeyId;

    protected String secretAccessKey;

    protected long cacheDuration = 7 * 24L;// hours

    private final List<Interceptor> httpInterceptorList = new ArrayList<>();

    private LoadingCache<String, H2oApi> h2oApiCache;

    @PostConstruct
    public void init() {
        final RemovalListener<String, H2oApi> listener =
                notification -> new Callable<>(notification.getValue().endSession(notification.getKey())).execute(response -> {}, t -> {});
        h2oApiCache = CacheBuilder.newBuilder()//
                .expireAfterAccess(cacheDuration, TimeUnit.HOURS)//
                .removalListener(listener)//
                .build(new CacheLoader<String, H2oApi>() {
                    @Override
                    public H2oApi load(final String key) throws IOException {
                        final H2oApi h2o =
                                new H2oApi(endpoint).connectTimeout(connectTimeout).readTimeout(readTimeout).writeTimeout(writeTimeout);
                        httpInterceptorList.stream().forEach(h2o::addInterceptor);
                        h2o.newSession(key).execute();
                        return h2o;
                    }
                });
    }

    public void invalidate() {
        h2oApiCache.invalidateAll();
    }

    protected H2oApi getH2oApi() {
        final String sessionKey = getSessionKey();
        try {
            return h2oApiCache.get(sessionKey);
        } catch (final ExecutionException e) {
            throw new FioneSystemException("Failed to read data from cache.", e);
        }
    }

    public void setEndpoint(final String endpoint) {
        this.endpoint = endpoint;
    }

    public Callable<ImportFilesV3> importFiles(final String path) {
        return new Callable<>(getH2oApi().importFiles(path));
    }

    public Callable<FramesListV3> getFrames(final FrameKeyV3 frameId) {
        return new Callable<>(getH2oApi().frames(frameId));
    }

    public Callable<FramesListV3> getFrames(final String frameId) {
        return getFrames(new FrameKeyV3(frameId));
    }

    public Callable<FramesV3> deleteFrame(final FrameKeyV3 frameId) {
        return new Callable<>(getH2oApi().deleteFrame(frameId));
    }

    public Callable<FramesV3> deleteFrame(final String frameId) {
        return deleteFrame(new FrameKeyV3(frameId));
    }

    public Callable<ParseSetupV3> setupParse(final String[] sourceFrames) {
        return new Callable<>(getH2oApi().guessParseSetup(sourceFrames));
    }

    public Callable<ParseV3> parseFiles(final ParseV3 params) {
        return new Callable<>(getH2oApi().parse(params));
    }

    public Callable<JobsV3> fetchJobs(final String jobId) {
        final Jobs service = getH2oApi().getService(Jobs.class);
        final Call<JobsV3> call = service.fetch(jobId);
        return new Callable<>(call);
    }

    public Callable<FramesV3> getFrameSummary(final String frameId) {
        return new Callable<>(getH2oApi().frameSummary(frameId));
    }

    public Callable<FramesV3> getFrameColumnSummary(final String frameId, final String column) {
        final Frames service = getH2oApi().getService(Frames.class);
        final Call<FramesV3> call = service.columnSummary(frameId, column);
        return new Callable<>(call);
    }

    public Callable<AutoMLBuildSpecV99> runAutoML(final AutoMLBuildControlV99 buildControl, final AutoMLInputV99 inputSpec,
            final AutoMLBuildModelsV99 buildModels) {
        final AutoMLBuilder service = getH2oApi().getService(AutoMLBuilder.class);
        final Call<AutoMLBuildSpecV99> call = service.build(buildControl, inputSpec, buildModels);
        return new Callable<>(call);
    }

    public Callable<LeaderboardV99> getLeaderboard(final String projectName) {
        return new Callable<>(getH2oApi().leaderboard(projectName));
    }

    public Callable<ModelsV3> getModel(final ModelKeyV3 model) {
        return new Callable<>(getH2oApi().model(model));
    }

    public Callable<ModelsV3> deleteModel(final ModelKeyV3 model) {
        return new Callable<>(getH2oApi().deleteModel(model));
    }

    public Callable<ModelMetricsListSchemaV3> predict(final ModelKeyV3 model, final FrameKeyV3 frame) {
        return new Callable<>(getH2oApi().predict(model, frame));
    }

    public Callable<ModelMetricsListSchemaV3> predict(final String modelId, final String frameId) {
        return predict(new ModelKeyV3(modelId), new FrameKeyV3(frameId));
    }

    public Callable<JobsV3> getJobs(final JobKeyV3 jobId) {
        return new Callable<>(getH2oApi().jobs(jobId));
    }

    public Callable<JobsV3> getJobs(final String jobId) {
        return getJobs(new JobKeyV3(jobId));
    }

    public Callable<RapidsSchemaV3> bindFrames(final FrameKeyV3 destinationFrame, final FrameKeyV3[] sourceFrames) {
        final StringBuilder buf = new StringBuilder(100);
        buf.append("(assign ").append(H2oApi.keyToString(destinationFrame)).append(" (cbind");
        Arrays.stream(sourceFrames).map(H2oApi::keyToString).forEach(s -> buf.append(' ').append(s));
        buf.append("))");
        return new Callable<>(getH2oApi().rapidsExec(buf.toString()));
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
        return new Callable<>(getH2oApi().exportFrame(params));
    }

    public Callable<FramesV3> getFrameData(final FramesV3 params) {
        return new Callable<>(getH2oApi().frame(params));
    }

    public Callable<InitIDV3> newSession() {
        return new Callable<>(getH2oApi().newSession(getSessionKey()));
    }

    public void closeSession() {
        h2oApiCache.invalidate(getSessionKey());
    }

    protected String getSessionKey() {
        String sessionKey;
        try {
            sessionKey = ComponentUtil.getComponent(FessLoginAssist.class).getSavedUserBean().map(u -> u.getUserId()).orElse("guest");
        } catch (final Exception e) {
            if (logger.isDebugEnabled()) {
                logger.debug("Failed to get sessionKey.", e);
            }
            sessionKey = "guest";
        }
        return StringCodecUtil.encodeUrlSafe(sessionKey);
    }

    public void writeMojo(final String modelId, final Consumer<InputStream> in, final Consumer<Exception> e) {
        String url = getH2oApi().getUrl();
        if (!url.endsWith("/")) {
            url = url + "/";
        }
        try (CurlResponse response = Curl.get(url + "3/Models/" + modelId + "/mojo").execute()) {
            in.accept(response.getContentAsStream());
        } catch (final Exception e1) {
            e.accept(e1);
        }
    }

    public void writeGenModel(final String modelId, final Consumer<InputStream> in, final Consumer<Exception> e) {
        String url = getH2oApi().getUrl();
        if (!url.endsWith("/")) {
            url = url + "/";
        }
        try (CurlResponse response = Curl.get(url + "3/h2o-genmodel.jar").execute()) {
            in.accept(response.getContentAsStream());
        } catch (final Exception e1) {
            e.accept(e1);
        }
    }

    public Callable<ModelExportV3> exportModel(final String modelId, final String path) {
        final ModelExportV3 params = new ModelExportV3();
        params.modelId = new ModelKeyV3(modelId);
        params.dir = path;
        params.force = true;
        return new Callable<>(getH2oApi().exportModel(params));
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

        public Response<T> execute(final long timeout) {
            final CountDownLatch latch = new CountDownLatch(1);
            final AtomicReference<Response<T>> result = new AtomicReference<>();
            final AtomicReference<Throwable> failure = new AtomicReference<>();
            execute(res -> {
                result.set(res);
                latch.countDown();
            }, t -> {
                failure.set(t);
                latch.countDown();
            });
            try {
                latch.await(timeout, TimeUnit.MILLISECONDS);
            } catch (final InterruptedException e) {
                throw new H2oAccessException("Interrupted.", e);
            }
            final Response<T> response = result.get();
            if (response != null) {
                return response;
            }
            final Throwable t = failure.get();
            if (t != null) {
                throw new H2oAccessException("Execution exception.", t);
            }
            call.cancel();
            throw new H2oAccessException("Request timeout.");
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

    public void setCacheDuration(final long cacheDuration) {
        this.cacheDuration = cacheDuration;
    }

}
