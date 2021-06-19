/*
 * Copyright 2012-2020 CodeLibs Project and the Others.
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

import static org.codelibs.core.stream.StreamUtil.stream;
import static org.codelibs.fione.h2o.bindings.H2oApi.keyToString;

import java.io.BufferedOutputStream;
import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.io.PipedInputStream;
import java.io.PipedOutputStream;
import java.io.PrintWriter;
import java.io.Reader;
import java.io.StringWriter;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.locks.ReadWriteLock;
import java.util.concurrent.locks.ReentrantReadWriteLock;
import java.util.function.BiPredicate;
import java.util.function.Consumer;
import java.util.stream.Collectors;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

import javax.annotation.PostConstruct;
import javax.annotation.Resource;

import org.apache.commons.lang3.StringUtils;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.codelibs.core.io.CopyUtil;
import org.codelibs.core.lang.StringUtil;
import org.codelibs.core.lang.ThreadUtil;
import org.codelibs.core.net.UuidUtil;
import org.codelibs.fess.crawler.Constants;
import org.codelibs.fess.exception.StorageException;
import org.codelibs.fess.mylasta.direction.FessConfig;
import org.codelibs.fess.util.ComponentUtil;
import org.codelibs.fess.util.ResourceUtil;
import org.codelibs.fione.entity.DataSet;
import org.codelibs.fione.entity.Project;
import org.codelibs.fione.exception.CacheNotFoundException;
import org.codelibs.fione.exception.FioneSystemException;
import org.codelibs.fione.exception.H2oAccessException;
import org.codelibs.fione.h2o.bindings.H2oApi;
import org.codelibs.fione.h2o.bindings.pojos.AutoMLBuildControlV99;
import org.codelibs.fione.h2o.bindings.pojos.AutoMLBuildModelsV99;
import org.codelibs.fione.h2o.bindings.pojos.AutoMLInputV99;
import org.codelibs.fione.h2o.bindings.pojos.ColV3;
import org.codelibs.fione.h2o.bindings.pojos.FrameBaseV3;
import org.codelibs.fione.h2o.bindings.pojos.FrameKeyV3;
import org.codelibs.fione.h2o.bindings.pojos.FrameV3;
import org.codelibs.fione.h2o.bindings.pojos.FramesV3;
import org.codelibs.fione.h2o.bindings.pojos.JobKeyV3;
import org.codelibs.fione.h2o.bindings.pojos.JobV3;
import org.codelibs.fione.h2o.bindings.pojos.JobV3.Kind;
import org.codelibs.fione.h2o.bindings.pojos.KeyV3;
import org.codelibs.fione.h2o.bindings.pojos.LeaderboardV99;
import org.codelibs.fione.h2o.bindings.pojos.ModelKeyV3;
import org.codelibs.fione.h2o.bindings.pojos.ModelSchemaBaseV3;
import org.codelibs.fione.h2o.bindings.pojos.ModelSchemaV3;
import org.codelibs.fione.h2o.bindings.pojos.ParseSetupV3;
import org.codelibs.fione.h2o.bindings.pojos.ParseV3;
import org.codelibs.fione.helper.PythonHelper.PythonModule;
import org.codelibs.fione.util.StringCodecUtil;
import org.lastaflute.core.smartdeploy.ManagedHotdeploy;
import org.lastaflute.di.exception.IORuntimeException;
import org.lastaflute.web.servlet.request.stream.WrittenStreamOut;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.google.common.cache.Cache;
import com.google.common.cache.CacheBuilder;
import com.google.common.collect.Lists;
import com.google.gson.Gson;
import com.orangesignal.csv.CsvConfig;
import com.orangesignal.csv.CsvReader;
import com.orangesignal.csv.CsvWriter;

import io.minio.BucketExistsArgs;
import io.minio.CopyObjectArgs;
import io.minio.CopySource;
import io.minio.GetObjectArgs;
import io.minio.ListObjectsArgs;
import io.minio.MakeBucketArgs;
import io.minio.MinioClient;
import io.minio.PutObjectArgs;
import io.minio.RemoveObjectArgs;
import io.minio.RemoveObjectsArgs;
import io.minio.Result;
import io.minio.errors.ErrorResponseException;
import io.minio.messages.DeleteError;
import io.minio.messages.DeleteObject;
import io.minio.messages.Item;
import retrofit2.Response;

public class ProjectHelper {

    private static final Logger logger = LogManager.getLogger(ProjectHelper.class);

    private static final String FIONE_END = "FIONE:END";

    private static final String NO_SUCH_KEY = "NoSuchKey";

    private static final String NO_SUCH_OBJECT = "NoSuchObject";

    @Resource
    protected H2oHelper h2oHelper;

    @Resource
    protected ModelHelper modelHelper;

    protected String projectFolderName = "fione";

    protected long requestTimeout = 5000L;

    protected final Gson gson = H2oApi.createGson();

    protected ReadWriteLock jobLock = new ReentrantReadWriteLock();

    protected Cache<String, Object> responseCache;

    @PostConstruct
    public void init() {
        final var fessConfig = ComponentUtil.getFessConfig();
        final var cacheBuilder = CacheBuilder.newBuilder();
        if (ManagedHotdeploy.isHotdeploy()) {
            cacheBuilder.expireAfterWrite(10, TimeUnit.SECONDS);
        } else {
            cacheBuilder.expireAfterWrite(fessConfig.getSystemPropertyAsInt("fione.api.cache.expire", 1), TimeUnit.MINUTES);
        }
        responseCache = cacheBuilder.build();
    }

    public Project[] getProjects() {
        final var fessConfig = ComponentUtil.getFessConfig();
        final List<Project> list = new ArrayList<>();
        try {
            final var minioClient = createClient(fessConfig);
            for (final Result<Item> result : minioClient.listObjects(ListObjectsArgs.builder().bucket(fessConfig.getStorageBucket())
                    .prefix(projectFolderName + "/").recursive(false).build())) {
                final var item = result.get();
                final var objectName = item.objectName();
                if (logger.isDebugEnabled()) {
                    logger.debug("objectName: {}", objectName);
                }
                final var values = objectName.split("/");
                if (values.length == 2) {
                    final var project = new Project(values[1]);
                    list.add(project);
                }
            }
        } catch (final Exception e) {
            if (logger.isDebugEnabled()) {
                logger.debug("Failed to access " + fessConfig.getStorageEndpoint(), e);
            }
        }
        return list.toArray(n -> new Project[n]);
    }

    protected MinioClient createClient(final FessConfig fessConfig) {
        try {
            return MinioClient.builder().endpoint(fessConfig.getStorageEndpoint())
                    .credentials(fessConfig.getStorageAccessKey(), fessConfig.getStorageSecretKey()).build();
        } catch (final Exception e) {
            throw new StorageException("Failed to create MinioClient: " + fessConfig.getStorageEndpoint(), e);
        }
    }

    public void store(final Project project) {
        if (logger.isDebugEnabled()) {
            logger.debug("Store project:{}", project);
        }
        final var fessConfig = ComponentUtil.getFessConfig();
        final var minioClient = createClient(fessConfig);
        final var json = gson.toJson(project);
        if (logger.isDebugEnabled()) {
            logger.debug("project: {}", json);
        }
        final var objectName = getProjectConfigPath(project.getId());
        try (var bais = new ByteArrayInputStream(json.getBytes(Constants.UTF_8_CHARSET))) {
            final var bucketName = fessConfig.getStorageBucket();
            if (!minioClient.bucketExists(BucketExistsArgs.builder().bucket(bucketName).build())) {
                minioClient.makeBucket(MakeBucketArgs.builder().bucket(bucketName).build());
                logger.info("Create bucket {}.", bucketName);
            }
            minioClient.putObject(PutObjectArgs.builder().bucket(bucketName).object(objectName)
                    .stream(bais, -1, PutObjectArgs.MIN_MULTIPART_SIZE).build());
        } catch (final Exception e) {
            throw new StorageException("Failed to create " + objectName, e);
        }
    }

    public Project getProject(final String sessionKey, final String projectId) {
        return getProject(sessionKey, projectId, true);
    }

    protected Project getProject(final String sessionKey, final String projectId, final boolean loadParams) {
        final var fessConfig = ComponentUtil.getFessConfig();
        final var minioClient = createClient(fessConfig);
        final var objectName = getProjectConfigPath(projectId);
        try (Reader reader =
                new InputStreamReader(minioClient.getObject(GetObjectArgs.builder().bucket(fessConfig.getStorageBucket())
                        .object(objectName).build()), Constants.UTF_8_CHARSET)) {
            final var project = gson.fromJson(reader, Project.class);
            if (loadParams) {
                project.setDataSets(getDataSets(fessConfig, minioClient, projectId));
                project.setFrameIds(getFrames(sessionKey, project));
                project.setJobs(getJobs(sessionKey, projectId));
            }
            return project;
        } catch (final Exception e) {
            throw new StorageException("Failed to read " + objectName, e);
        }
    }

    public boolean projectExists(final String sessionKey, final String projectId) {
        try {
            return getProject(sessionKey, projectId, false) != null;
        } catch (final StorageException e) {
            if (logger.isDebugEnabled()) {
                logger.debug("Project {} does not exist.", projectId, e);
            }
        }
        return false;
    }

    public String getFrameName(final String projectId, final String dataSetId) {
        return projectId + "_" + dataSetId;
    }

    protected String[] getFrames(final String sessionKey, final Project project) {
        return getFrames(sessionKey, project, String::startsWith);
    }

    protected String[] getFrames(final String sessionKey, final Project project, final BiPredicate<String, String> condition) {
        final List<String> frameIdList = new ArrayList<>();
        Arrays.stream(project.getDataSets()).map(d -> getFrameName(project.getId(), d.getId())).forEach(baseName -> {
            try {
                final var response = h2oHelper.getFrames(sessionKey, baseName).execute(requestTimeout);
                if (logger.isDebugEnabled()) {
                    logger.debug("getFrames: {}", response);
                }
                if (response.code() == 200) {
                    for (final FrameBaseV3 frame : response.body().frames) {
                        final var frameId = keyToString(frame.frameId);
                        if (frameId != null && condition.test(frameId, baseName)) {
                            frameIdList.add(frameId);
                        }
                    }
                } else {
                    logger.warn("Failed to get frames: {}", response);
                }
            } catch (final Exception e) {
                final var msg = e.getMessage();
                if (msg != null && msg.toLowerCase().contains("timeout")) {
                    logger.debug("Failed to get frames.", e);
                } else {
                    logger.warn("Failed to get frames.", e);
                }
            }
        });
        return frameIdList.stream().distinct().toArray(n -> new String[n]);
    }

    public DataSet[] getDataSets(final String projectId) {
        final var fessConfig = ComponentUtil.getFessConfig();
        final var minioClient = createClient(fessConfig);
        return getDataSets(fessConfig, minioClient, projectId);
    }

    protected DataSet[] getDataSets(final FessConfig fessConfig, final MinioClient minioClient, final String projectId) {
        final var prefix = projectFolderName + "/" + projectId + "/data/";
        final List<DataSet> list = new ArrayList<>();
        for (final Result<Item> result : minioClient.listObjects(ListObjectsArgs.builder().bucket(fessConfig.getStorageBucket())
                .prefix(prefix).recursive(false).build())) {
            try {
                final var item = result.get();
                final var objectName = item.objectName();
                final var values = objectName.split("/");
                if (values.length == 4) {
                    final var dataSetId = StringCodecUtil.encodeUrlSafe(values[3]);
                    final var dataSet = getDataSet(fessConfig, minioClient, projectId, dataSetId);
                    list.add(dataSet);
                }
            } catch (final Exception e) {
                logger.warn("Failed to read dataset", e);
            }
        }
        return list.toArray(n -> new DataSet[n]);
    }

    public DataSet getDataSet(final String projectId, final String dataSetId) {
        final var fessConfig = ComponentUtil.getFessConfig();
        final var minioClient = createClient(fessConfig);
        return getDataSet(fessConfig, minioClient, projectId, dataSetId);
    }

    protected DataSet getDataSet(final FessConfig fessConfig, final MinioClient minioClient, final String projectId, final String dataSetId) {
        final var objectName = getDataSetConfigPath(projectId, dataSetId);
        try (Reader reader =
                new InputStreamReader(minioClient.getObject(GetObjectArgs.builder().bucket(fessConfig.getStorageBucket())
                        .object(objectName).build()), Constants.UTF_8_CHARSET)) {
            return gson.fromJson(reader, DataSet.class);
        } catch (final Exception e) {
            if (logger.isDebugEnabled()) {
                logger.warn("Failed to read " + objectName, e);
            }
        }
        return createDataSet(projectId, dataSetId);
    }

    public DataSet addDataSet(final String sessionKey, final String projectId, final String fileName, final InputStream in,
            final int checkHeader) {
        final var fessConfig = ComponentUtil.getFessConfig();
        final var minioClient = createClient(fessConfig);
        final var objectName = getDataPath(projectId, fileName);
        try {
            minioClient.putObject(PutObjectArgs.builder().bucket(fessConfig.getStorageBucket()).object(objectName)
                    .stream(in, -1, PutObjectArgs.MIN_MULTIPART_SIZE).build());
        } catch (final Exception e) {
            throw new StorageException("Failed to store " + objectName, e);
        }

        final var dataSet = createDataSet(projectId, StringCodecUtil.encodeUrlSafe(fileName));
        dataSet.setCheckHeader(checkHeader);
        if (fileName.toLowerCase(Locale.ROOT).contains("test")) {
            dataSet.setType(DataSet.TEST);
        }
        store(projectId, dataSet);

        return dataSet;
    }

    protected DataSet createDataSet(final String projectId, final String dataSetId) {
        final var dataSet = new DataSet(dataSetId);
        dataSet.setPath(getS3Path(projectId, dataSet.getName()));
        return dataSet;
    }

    public void deleteDataSet(final String sessionKey, final String projectId, final String dataSetId) {
        final var fessConfig = ComponentUtil.getFessConfig();
        final var minioClient = createClient(fessConfig);

        final var dataSet = getDataSet(fessConfig, minioClient, projectId, dataSetId);
        if (dataSet.getSchema() != null) {
            final var destinationFrame = dataSet.getSchema().destinationFrame;
            h2oHelper.deleteFrame(sessionKey, destinationFrame).execute(deleteFrameResponse -> {
                if (logger.isDebugEnabled()) {
                    logger.debug("deleteFrameResponse: {}", deleteFrameResponse);
                }
                if (deleteFrameResponse.code() == 200) {
                    logger.info("Delete frame: {}", keyToString(destinationFrame));
                } else {
                    logger.warn("Failed to delete {}", deleteFrameResponse);
                }
            }, t -> logger.warn("Failed to delete frame {}", keyToString(destinationFrame), t));
        }

        final var name = StringCodecUtil.decode(dataSetId);
        final var dataPath = new DeleteObject(getDataPath(projectId, name));
        final var configPath = new DeleteObject(getDataSetConfigPath(projectId, dataSetId));
        try {
            final var results =
                    minioClient.removeObjects(RemoveObjectsArgs.builder().bucket(fessConfig.getStorageBucket())
                            .objects(Lists.newArrayList(dataPath, configPath)).build());
            for (final Result<DeleteError> result : results) {
                logger.warn("Failed to delete {}", result.get());
            }
        } catch (final Exception e) {
            throw new StorageException("Failed to delete data files.", e);
        }
    }

    public void loadDataSetSchema(final String sessionKey, final String projectId, final DataSet dataSet) {
        loadDataSetSchema(sessionKey, projectId, dataSet, () -> {});
    }

    public void loadDataSetSchema(final String sessionKey, final String projectId, final DataSet dataSet, final Runnable chain) {
        final var workingJob = createWorkingJob(dataSet.getName(), "Parse Schema", 0.2f);
        store(sessionKey, projectId, workingJob);
        h2oHelper.importFiles(sessionKey, dataSet.getPath())
                .execute(
                        importResponse -> {
                            if (logger.isDebugEnabled()) {
                                logger.debug("importFiles: {}", importResponse);
                            }
                            if (importResponse.code() == 200) {
                                final var parseSetup = new ParseSetupV3();
                                parseSetup.sourceFrames =
                                        Arrays.stream(importResponse.body().destinationFrames).map(FrameKeyV3::new)
                                                .toArray(n -> new FrameKeyV3[n]);
                                parseSetup.checkHeader = dataSet.getCheckHeader();
                                h2oHelper.setupParse(sessionKey, parseSetup).execute(
                                        setupResponse -> {
                                            if (logger.isDebugEnabled()) {
                                                logger.debug("setupParse: {}", setupResponse);
                                            }
                                            if (setupResponse.code() == 200) {
                                                final var meta = h2oHelper.convert(setupResponse.body());
                                                meta.destinationFrame = new FrameKeyV3(getFrameName(projectId, dataSet.getId()) + ".hex");
                                                dataSet.setSchema(meta);
                                                store(projectId, dataSet);
                                                Arrays.stream(parseSetup.sourceFrames).map(H2oApi::keyToString).forEach(s -> {
                                                    h2oHelper.deleteFrame(sessionKey, s).execute(deleteResponse -> {
                                                        if (logger.isDebugEnabled()) {
                                                            logger.debug("deleteFrame: {}", deleteResponse);
                                                        }
                                                        chain.run();
                                                        finish(sessionKey, projectId, workingJob, null);
                                                    }, t -> {
                                                        logger.warn("Failed to delete frame: {}", s, t);
                                                        finish(sessionKey, projectId, workingJob, t);
                                                    });
                                                });
                                            } else {
                                                logger.warn("Failed to parse data: projectId:{}, dataSet:{}", projectId, dataSet);
                                                finish(sessionKey, projectId, workingJob, new H2oAccessException("Failed to access "
                                                        + setupResponse));
                                            }
                                        }, t -> {
                                            logger.warn("Failed to parse data: projectId:{}, dataSet:{}", projectId, dataSet, t);
                                            finish(sessionKey, projectId, workingJob, t);
                                        });
                            } else {
                                logger.warn("Failed to import data: projectId:{}, dataSet:{}", projectId, dataSet);
                                finish(sessionKey, projectId, workingJob, new H2oAccessException("Failed to access " + importResponse));
                            }
                        }, t -> {
                            logger.warn("Failed to import data: projectId:{}, dataSet:{}", projectId, dataSet, t);
                            finish(sessionKey, projectId, workingJob, t);
                        });
    }

    public void store(final String projectId, final DataSet dataSet) {
        if (logger.isDebugEnabled()) {
            logger.debug("Store projectId:{}, dataSet:{}", projectId, dataSet);
        }
        final var fessConfig = ComponentUtil.getFessConfig();
        final var minioClient = createClient(fessConfig);
        final var json = gson.toJson(dataSet);
        if (logger.isDebugEnabled()) {
            logger.debug("dataSet: {}", json);
        }
        final var objectName = getDataSetConfigPath(projectId, dataSet.getId());
        try (var bais = new ByteArrayInputStream(json.getBytes(Constants.UTF_8_CHARSET))) {
            minioClient.putObject(PutObjectArgs.builder().bucket(fessConfig.getStorageBucket()).object(objectName)
                    .stream(bais, -1, PutObjectArgs.MIN_MULTIPART_SIZE).build());
        } catch (final Exception e) {
            throw new StorageException("Failed to create " + objectName, e);
        }
    }

    public FrameV3 getColumnSummaries(final String sessionKey, final String projectId, final String frameId) {
        try {
            final var cacheKey = getFrameSummaryCacheKey(projectId, frameId);
            return (FrameV3) responseCache.get(cacheKey, () -> {
                final var response = h2oHelper.getFrameSummary(sessionKey, frameId).execute();
                if (logger.isDebugEnabled()) {
                    logger.debug("getFrameSummary: {}", response);
                }
                if (response.code() == 200) {
                    final var data = response.body();
                    if (data.frames.length == 1) {
                        final var frame = data.frames[0];
                        if (frame == null || frame.byteSize == 0L) {
                            throw new CacheNotFoundException();
                        }
                        return frame;
                    }
                }
                throw new CacheNotFoundException();
            });
        } catch (final Exception e) {
            if (e.getCause() instanceof CacheNotFoundException) {
                return null;
            }
            if (logger.isDebugEnabled()) {
                logger.debug("Failed to get data from cache.", e);
            }
            return null;
        }
    }

    public void createFrame(final String sessionKey, final String projectId, final DataSet dataSet, final Consumer<Response<ParseV3>> result) {
        final var workingJob = createWorkingJob(dataSet.getName(), "Parse Frame", 0.2f);
        store(sessionKey, projectId, workingJob);
        h2oHelper.importFiles(sessionKey, dataSet.getPath()).execute(importResponse -> {
            if (logger.isDebugEnabled()) {
                logger.debug("importFiles: {}", importResponse);
            }
            if (importResponse.code() == 200) {
                h2oHelper.parseFiles(sessionKey, dataSet.getSchema()).execute(parseResponse -> {
                    if (logger.isDebugEnabled()) {
                        logger.debug("parseRes: {}", parseResponse);
                    }
                    if (parseResponse.code() == 200) {
                        logger.info("Create frame: {}", keyToString(parseResponse.body().destinationFrame));
                        deleteJob(sessionKey, projectId, workingJob.key.name);
                        store(sessionKey, projectId, parseResponse.body().job);
                        result.accept(parseResponse);
                    } else {
                        logger.warn("Failed to parse data: dataSet:{}", dataSet);
                        finish(sessionKey, projectId, workingJob, new H2oAccessException("Failed to access " + parseResponse));
                    }
                }, t -> {
                    logger.warn("Failed to parse data: dataSet:{}", dataSet, t);
                    finish(sessionKey, projectId, workingJob, t);
                });
            } else {
                logger.warn("Failed to import data: dataSet:{}", dataSet);
                finish(sessionKey, projectId, workingJob, new H2oAccessException("Failed to access " + importResponse));
            }
        }, t -> {
            logger.warn("Failed to import data: dataSet:{}", dataSet, t);
            finish(sessionKey, projectId, workingJob, new H2oAccessException("Failed to access ", t));
        });
    }

    public void deleteFrame(final String sessionKey, final String projectId, final String frameId) {
        final var response = h2oHelper.deleteFrame(sessionKey, frameId).execute();
        if (logger.isDebugEnabled()) {
            logger.debug("deleteFrame: {}", response);
        }
        if (response.code() == 200) {
            logger.info("Deleted frame: {}", frameId);
        } else {
            throw new H2oAccessException("Failed to delete frame " + frameId + " : " + response);
        }
        responseCache.invalidate(getFrameSummaryCacheKey(projectId, frameId));
    }

    protected void deleteFrameQuietly(final String sessionKey, final String frameId) {
        h2oHelper.deleteFrame(sessionKey, frameId).execute(delteFrameResonse -> logger.info("Deleted frame: {}", frameId),
                t -> logger.warn("Failed to delete frame: {}", frameId, t));
    }

    public void runAutoML(final String sessionKey, final String projectId, final AutoMLBuildControlV99 buildControl,
            final AutoMLInputV99 inputSpec, final AutoMLBuildModelsV99 buildModels) {
        final var workingJob =
                createWorkingJob(buildControl.projectName + "@@" + inputSpec.responseColumn.columnName, "AutoML starting", 0.2f);
        store(sessionKey, projectId, workingJob);
        h2oHelper.runAutoML(sessionKey, buildControl, inputSpec, buildModels).execute(autoMLResponse -> {
            if (logger.isDebugEnabled()) {
                logger.debug("runAutoML: {}", autoMLResponse);
            }
            if (autoMLResponse.code() == 200) {
                logger.info("AutoML process started: {}", keyToString(autoMLResponse.body().job.dest));
                deleteJob(sessionKey, projectId, workingJob.key.name);
                store(sessionKey, projectId, autoMLResponse.body().job);
            } else {
                logger.warn("Failed to run AutoML: {}", autoMLResponse);
                finish(sessionKey, projectId, workingJob, new H2oAccessException("Failed to access " + autoMLResponse));
            }
        }, t -> {
            logger.warn("Failed to run AutoML.", t);
            finish(sessionKey, projectId, workingJob, t);
        });
    }

    protected JobV3[] getJobs(final String sessionKey, final String projectId) {
        return getJobs(sessionKey, projectId, true);
    }

    protected JobV3[] getJobs(final String sessionKey, final String projectId, final boolean update) {
        final var fessConfig = ComponentUtil.getFessConfig();
        final var minioClient = createClient(fessConfig);
        final var objectName = getJobsConfigPath(projectId);
        try (Reader reader =
                new InputStreamReader(minioClient.getObject(GetObjectArgs.builder().bucket(fessConfig.getStorageBucket())
                        .object(objectName).build()), Constants.UTF_8_CHARSET)) {
            final var jobs = gson.fromJson(reader, JobV3[].class);
            if (update) {
                jobLock.writeLock().lock();
                try {
                    final List<JobV3> list = new ArrayList<>();
                    for (final JobV3 job : jobs) {
                        if (JobV3.RUNNING.equals(job.status)) {
                            try {
                                final var response = h2oHelper.getJobs(sessionKey, keyToString(job.key)).execute(requestTimeout);
                                if (logger.isDebugEnabled()) {
                                    logger.debug("getJobs: {}", response);
                                }
                                if (response.code() == 200) {
                                    JobV3 target = null;
                                    for (final JobV3 j : response.body().jobs) {
                                        if (keyToString(job.key).equals(keyToString(j.key))) {
                                            target = j;
                                        }
                                    }
                                    if (target == null && job.getKind() == Kind.AUTO_ML && job.ready()) {
                                        job.status = JobV3.CANCELLED;
                                    }
                                    list.add(target != null ? target : job);
                                } else {
                                    list.add(job);
                                }
                            } catch (final Exception e) {
                                logger.warn("Failed to access job: {}", job.key, e);
                                list.add(job);
                            }
                        } else {
                            list.add(job);
                        }
                    }
                    store(projectId, list.toArray(n -> new JobV3[n]));
                } finally {
                    jobLock.writeLock().unlock();
                }
            }
            return jobs;
        } catch (final ErrorResponseException e) {
            final var code = e.errorResponse().code();
            if (NO_SUCH_KEY.equalsIgnoreCase(code) || NO_SUCH_OBJECT.equalsIgnoreCase(code)) {
                return new JobV3[0];
            }
            throw new StorageException("Failed to read " + objectName, e);
        } catch (final Exception e) {
            throw new StorageException("Failed to read " + objectName, e);
        }

    }

    public void store(final String sessionKey, final String projectId, final JobV3 job) {
        if (logger.isDebugEnabled()) {
            logger.debug("Insert job:{}", job);
        }
        if (job == null) {
            return;
        }

        jobLock.writeLock().lock();
        try {
            final var oldJobs = getJobs(sessionKey, projectId, false);
            for (var i = 0; i < oldJobs.length; i++) {
                if (oldJobs[i].key.name.equals(job.key.name)) {
                    oldJobs[i] = job;
                    store(projectId, oldJobs);
                    return;
                }
            }

            final var jobs = Arrays.copyOf(oldJobs, oldJobs.length + 1);
            jobs[jobs.length - 1] = job;
            store(projectId, jobs);
        } finally {
            jobLock.writeLock().unlock();
        }
    }

    public boolean deleteJob(final String sessionKey, final String projectId, final String jobId) {
        final var jobKey = new JobKeyV3(jobId);
        final var getJobResponse = h2oHelper.getJobs(sessionKey, jobKey).execute();
        if (logger.isDebugEnabled()) {
            logger.debug("getJobs: {}", getJobResponse);
        }
        if (getJobResponse.code() == 200) {
            final var job = getJobResponse.body().findJob(jobId);
            if (job != null && JobV3.RUNNING.equals(job.status)) {
                final var cancelJobResponse = h2oHelper.cancelJob(sessionKey, jobKey).execute();
                if (logger.isDebugEnabled()) {
                    logger.debug("cancelJob: {}", cancelJobResponse);
                }
                return false;
            }
        } else {
            logger.warn("Failed to get job: {}", getJobResponse);
        }

        jobLock.writeLock().lock();
        try {
            store(projectId,
                    Arrays.stream(getJobs(sessionKey, projectId, false)).filter(j -> !jobId.equals(keyToString(j.key)))
                            .toArray(n -> new JobV3[n]));
        } finally {
            jobLock.writeLock().unlock();
        }

        responseCache.invalidate(getLeaderboardsCacheKey(projectId));
        return true;
    }

    public synchronized void deleteAllJobs(final String sessionKey, final String projectId) {
        jobLock.writeLock().lock();
        try {
            final var jobs =
                    Arrays.stream(getJobs(sessionKey, projectId, false))
                            .filter(j -> j.getKind() == Kind.AUTO_ML && !JobV3.RUNNING.equals(j.status)).toArray(n -> new JobV3[n]);
            if (jobs.length > 0) {
                new Thread(() -> stream(jobs).of(
                        stream -> stream.forEach(job -> {
                            final var leaderboardId = keyToString(job.dest);
                            if (StringUtil.isNotBlank(leaderboardId)) {
                                final var leaderboard = getLeaderboard(sessionKey, projectId, leaderboardId);
                                if (leaderboard != null) {
                                    stream(leaderboard.models).of(
                                            st -> st.map(H2oApi::keyToString).filter(StringUtil::isNotBlank).forEach(modelId -> {
                                                try {
                                                    deleteModel(sessionKey, projectId, modelId);
                                                } catch (final Exception e) {
                                                    logger.warn("Failed to delete {} in {}", modelId, projectId, e);
                                                }
                                            }));
                                }
                            }
                        })), "DeleteModels").start();
            }
            store(projectId,
                    Arrays.stream(getJobs(sessionKey, projectId, false)).filter(j -> JobV3.RUNNING.equals(j.status))
                            .toArray(n -> new JobV3[n]));
        } finally {
            jobLock.writeLock().unlock();
        }

        responseCache.invalidate(getLeaderboardsCacheKey(projectId));
    }

    protected void store(final String projectId, final JobV3[] jobs) {
        final var fessConfig = ComponentUtil.getFessConfig();
        final var minioClient = createClient(fessConfig);
        final var json = gson.toJson(jobs);
        if (logger.isDebugEnabled()) {
            logger.debug("jobs: {}", json);
        }
        final var objectName = getJobsConfigPath(projectId);
        try (var bais = new ByteArrayInputStream(json.getBytes(Constants.UTF_8_CHARSET))) {
            minioClient.putObject(PutObjectArgs.builder().bucket(fessConfig.getStorageBucket()).object(objectName)
                    .stream(bais, -1, PutObjectArgs.MIN_MULTIPART_SIZE).build());
        } catch (final Exception e) {
            throw new StorageException("Failed to create " + objectName, e);
        }
    }

    public LeaderboardV99 getLeaderboard(final String sessionKey, final String projectId, final String leaderboardId) {
        try {
            final var cacheKey = getLeaderboardCacheKey(projectId, leaderboardId);
            return (LeaderboardV99) responseCache.get(cacheKey, () -> {
                final var response = h2oHelper.getLeaderboard(sessionKey, leaderboardId).execute();
                if (logger.isDebugEnabled()) {
                    logger.debug("getLeaderboard: {}", response);
                }
                if (response.code() == 200) {
                    return response.body();
                } else if (response.code() == 404) {
                    final var localLeaderboard = getLocalLeaderboard(sessionKey, projectId, leaderboardId);
                    if (localLeaderboard != null) {
                        return localLeaderboard;
                    }
                    throw new CacheNotFoundException();
                }
                logger.warn("Failed to read leaderboard: {}", response);
                throw new CacheNotFoundException();
            });
        } catch (final Exception e) {
            if (e.getCause() instanceof CacheNotFoundException) {
                return null;
            }
            if (logger.isDebugEnabled()) {
                logger.debug("Failed to get data from cache.", e);
            }
            return null;
        }
    }

    public void predict(final String sessionKey, final String projectId, final String frameId, final String modelId, final String name) {
        predict(sessionKey, projectId, frameId, modelId, name, d -> {});
    }

    public void predict(final String sessionKey, final String projectId, final String frameId, final String modelId, final String name,
            final Consumer<DataSet> consumer) {
        final var workingJob = createWorkingJob(name, "Export Prediction", 0.25f);
        store(sessionKey, projectId, workingJob);
        h2oHelper.predict(sessionKey, modelId, frameId).execute(
                predictResponse -> {
                    if (logger.isDebugEnabled()) {
                        logger.debug("predict: {}", predictResponse);
                    }
                    if (predictResponse.code() == 200) {
                        workingJob.progress = 0.5f;
                        store(sessionKey, projectId, workingJob);
                        final var modelMetricsListSchema = predictResponse.body();
                        final var predictionsFrameId = keyToString(modelMetricsListSchema.predictionsFrame);
                        final var destinationFrameId = "combind-" + predictionsFrameId;
                        h2oHelper.bindFrames(sessionKey, destinationFrameId, new String[] { predictionsFrameId, frameId }).execute(
                                bindFramesResponse -> {
                                    if (logger.isDebugEnabled()) {
                                        logger.debug("bindFrames: {}", bindFramesResponse);
                                    }
                                    if (bindFramesResponse.code() == 200) {
                                        workingJob.progress = 0.75f;
                                        store(sessionKey, projectId, workingJob);
                                        h2oHelper.exportFrame(sessionKey, new FrameKeyV3(destinationFrameId),
                                                getPredictCsvPath(projectId, name), true).execute(
                                                exportFrameResponse -> {
                                                    if (logger.isDebugEnabled()) {
                                                        logger.debug("exportFrame: {}", exportFrameResponse);
                                                    }
                                                    if (exportFrameResponse.code() == 200) {
                                                        final var dataSet =
                                                                createDataSet(projectId, StringCodecUtil.encodeUrlSafe(name + ".csv"));
                                                        dataSet.setType(DataSet.PREDICT);
                                                        store(projectId, dataSet);
                                                        consumer.accept(dataSet);
                                                        finish(sessionKey, projectId, workingJob, null);
                                                    } else {
                                                        logger.warn("Failed to export frame: {}", exportFrameResponse);
                                                        finish(sessionKey, projectId, workingJob, new H2oAccessException(
                                                                "Failed to access " + exportFrameResponse));
                                                    }
                                                    deleteFrameQuietly(sessionKey, destinationFrameId);
                                                    deleteFrameQuietly(sessionKey, predictionsFrameId);
                                                }, t -> {
                                                    logger.warn("Failed to export frame: {}", name, t);
                                                    finish(sessionKey, projectId, workingJob, t);
                                                    deleteFrameQuietly(sessionKey, destinationFrameId);
                                                    deleteFrameQuietly(sessionKey, predictionsFrameId);
                                                });
                                    } else {
                                        logger.warn("Failed to export frame: {}", bindFramesResponse);
                                        finish(sessionKey, projectId, workingJob, new H2oAccessException("Failed to access "
                                                + bindFramesResponse));
                                        deleteFrameQuietly(sessionKey, predictionsFrameId);
                                    }
                                }, t -> {
                                    logger.warn("Failed to export frame: {}", name, t);
                                    finish(sessionKey, projectId, workingJob, t);
                                    deleteFrameQuietly(sessionKey, predictionsFrameId);
                                });
                    } else {
                        logger.warn("Failed to export frame: {}", predictResponse);
                        finish(sessionKey, projectId, workingJob, new H2oAccessException("Failed to access " + predictResponse));
                    }
                }, t -> {
                    logger.warn("Failed to export frame: {}", name, t);
                    finish(sessionKey, projectId, workingJob, t);
                });
    }

    public void writeDataSet(final String sessionKey, final String projectId, final DataSet dataSet, final WrittenStreamOut out) {
        final var fessConfig = ComponentUtil.getFessConfig();
        final var minioClient = createClient(fessConfig);
        final var objectName = getDataPath(projectId, dataSet.getName());
        try (var in = minioClient.getObject(GetObjectArgs.builder().bucket(fessConfig.getStorageBucket()).object(objectName).build())) {
            out.write(in);
        } catch (final Exception e) {
            throw new StorageException("Failed to write " + objectName, e);
        }
    }

    public void exportFrame(final String sessionKey, final String projectId, final String frameId, final String name) {
        final var filename = name.toLowerCase().endsWith(".csv") ? name : name + ".csv";
        final var workingJob = createWorkingJob(filename, "Export Frame", 0.25f);
        store(sessionKey, projectId, workingJob);
        h2oHelper.exportFrame(sessionKey, new FrameKeyV3(frameId), getPredictCsvPath(projectId, filename), true).execute(
                exportFrameResponse -> {
                    if (logger.isDebugEnabled()) {
                        logger.debug("exportFrame: {}", exportFrameResponse);
                    }
                    if (exportFrameResponse.code() == 200) {
                        final var dataSet = createDataSet(projectId, StringCodecUtil.encodeUrlSafe(filename));
                        dataSet.setType(DataSet.PREDICT);
                        store(projectId, dataSet);
                        finish(sessionKey, projectId, workingJob, null);
                    } else {
                        logger.warn("Failed to export frame: {}", exportFrameResponse);
                        finish(sessionKey, projectId, workingJob, new H2oAccessException("Failed to access " + exportFrameResponse));
                    }
                }, t -> {
                    logger.warn("Failed to export frame: {}", name, t);
                    finish(sessionKey, projectId, workingJob, t);
                });
    }

    public void renewSession(final String sessionKey, final String projectId) {
        final var project = getProject(sessionKey, projectId);
        responseCache.invalidateAll();
        deleteAllJobs(sessionKey, projectId);
        Arrays.stream(getFrames(sessionKey, project, (x, y) -> x.endsWith(y + ".hex"))).forEach(frameId -> {
            try {
                final var deleteFrameResponse = h2oHelper.deleteFrame(sessionKey, frameId).execute();
                if (logger.isDebugEnabled()) {
                    logger.debug("deleteFrame: {}", deleteFrameResponse);
                }
                if (deleteFrameResponse.code() != 200) {
                    logger.warn("Failed to delete {}: {}", frameId, deleteFrameResponse);
                }
            } catch (final Exception e) {
                logger.warn("Failed to delete {}", frameId, e);
            }
        });
        h2oHelper.closeSession(sessionKey);
    }

    public void deleteProject(final String sessionKey, final String projectId) {
        h2oHelper.closeSession(sessionKey);

        final var fessConfig = ComponentUtil.getFessConfig();
        final var minioClient = createClient(fessConfig);
        final var path = projectFolderName + "/" + projectId + "/";
        for (final Result<Item> result : minioClient.listObjects(ListObjectsArgs.builder().bucket(fessConfig.getStorageBucket())
                .prefix(path).recursive(true).build())) {
            try {
                final var item = result.get();
                final var objectName = item.objectName();
                if (logger.isDebugEnabled()) {
                    logger.debug("objectName: {}", objectName);
                }
                minioClient.removeObject(RemoveObjectArgs.builder().bucket(fessConfig.getStorageBucket()).object(objectName).build());
            } catch (final Exception e) {
                logger.warn("Failed to remove an object from {}.", path, e);
            }
        }
    }

    public void changeColumnType(final String sessionKey, final String projectId, final String frameId, final int index,
            final String columnType, final long from, final long to) {
        final var type = convertColumnType(columnType);
        if (type == null) {
            if (logger.isDebugEnabled()) {
                logger.debug("Unknown column type: {}/{}/{}/{}", projectId, frameId, index, columnType);
            }
            return;
        }
        final var response = h2oHelper.changeColumnType(sessionKey, new FrameKeyV3(frameId), type, index, from, to).execute();
        if (logger.isDebugEnabled()) {
            logger.debug("changeColumnType: {}", response);
        }
        if (response.code() != 200) {
            throw new H2oAccessException("Failed to change Column " + index + " in " + frameId);
        }
    }

    public String convertColumnType(final String columnType) {
        switch (columnType) {
        case "String":
        case "string":
        case "character":
            return "character";
        case "Enum":
        case "enum":
        case "factor":
            return "factor";
        case "Numeric":
        case "real":
        case "numeric":
            return "numeric";
        default:
            break;
        }
        return null;
    }

    public FrameV3 getFrameData(final String sessionKey, final FramesV3 params) {
        final var response = h2oHelper.getFrameData(sessionKey, params).execute();
        if (logger.isDebugEnabled()) {
            logger.debug("getFrameData: {}", response);
        }
        if (response.code() == 200) {
            final var frames = response.body();
            for (final FrameV3 frame : frames.frames) {
                if (params.frameId.name.equals(frame.frameId.name)) {
                    return frame;
                }
            }
        } else if (response.code() == 404) {
            return null;
        }
        logger.warn("Failed to read leaderboard: {}", response);
        return null;
    }

    public ColV3 getFrameColumnData(final String sessionKey, final FramesV3 params) {
        try {
            final var cacheKey = params.toString();
            final var colData =
                    (ColV3) responseCache.get(cacheKey, () -> {
                        final var response = h2oHelper.getFrameColumnData(sessionKey, params).execute();
                        if (logger.isDebugEnabled()) {
                            logger.debug("getFrameColumnData: {}", response);
                        }
                        if (response.code() == 200) {
                            final var frames = response.body();
                            if (frames.frames != null && frames.frames.length > 0 && frames.frames[0] != null
                                    && frames.frames[0].columns.length > 0) {
                                final var frame = frames.frames[0];
                                final var col = frame.columns[0];
                                col.setRows(frame.rows);
                                return col;
                            }
                        } else if (response.code() == 404) {
                            throw new CacheNotFoundException();
                        }
                        logger.warn("Failed to read leaderboard: {}", response);
                        throw new CacheNotFoundException();
                    });
            return colData;
        } catch (final Exception e) {
            if (e.getCause() instanceof CacheNotFoundException) {
                return null;
            }
            if (logger.isDebugEnabled()) {
                logger.debug("Failed to get data from cache.", e);
            }
            return null;

        }
    }

    public ModelSchemaBaseV3 getModel(final String sessionKey, final String projectId, final String leaderboardId, final String modelId) {
        if (StringUtil.isBlank(modelId)) {
            return null;
        }
        try {
            final var cacheKey = getModelCacheKey(projectId, modelId);
            return (ModelSchemaBaseV3) responseCache.get(cacheKey, () -> {
                final var response = h2oHelper.getModel(sessionKey, new ModelKeyV3(modelId)).execute();
                if (logger.isDebugEnabled()) {
                    logger.debug("getModel: {}", response);
                }
                if (response.code() == 200) {
                    final var models = response.body();
                    for (final ModelSchemaBaseV3 model : models.models) {
                        if (modelId.equals(model.modelId.name)) {
                            return model;
                        }
                    }
                } else if (response.code() == 404) {
                    final var model = getLocalModel(sessionKey, projectId, leaderboardId, modelId);
                    if (model != null) {
                        return model;
                    }
                    throw new CacheNotFoundException();
                }
                logger.warn("Failed to read leaderboard: {}", response);
                throw new CacheNotFoundException();
            });
        } catch (final Exception e) {
            if (e.getCause() instanceof CacheNotFoundException) {
                return null;
            }
            if (logger.isDebugEnabled()) {
                logger.debug("Failed to get data from cache.", e);
            }
            return null;
        }
    }

    public void writeMojo(final String sessionKey, final String projectId, final String modelId, final WrittenStreamOut out) {
        h2oHelper.writeMojo(sessionKey, modelId, in -> {
            try {
                out.write(in);
            } catch (final IOException e) {
                throw new IORuntimeException(e);
            }
        }, e -> logger.warn("Failed to write {} in {}", modelId, projectId, e));
    }

    public void writeGenModel(final String sessionKey, final String projectId, final String modelId, final WrittenStreamOut out) {
        h2oHelper.writeGenModel(sessionKey, modelId, in -> {
            try {
                out.write(in);
            } catch (final IOException e) {
                throw new IORuntimeException(e);
            }
        }, e -> logger.warn("Failed to write {} in {}", modelId, projectId, e));
    }

    public void writeServing(final String sessionKey, final String projectId, final String modelId, final WrittenStreamOut out) {
        h2oHelper.writeMojo(sessionKey, modelId, in -> {
            try (var zos = new ZipOutputStream(new BufferedOutputStream(out.stream()))) {
                // Dockerfile
                zos.putNextEntry(new ZipEntry("serving/Dockerfile"));
                final var dockerfilePath = ResourceUtil.getEnvPath("fione", "resources", "Dockerfile.serving");
                try (var fis = Files.newInputStream(dockerfilePath)) {
                    CopyUtil.copy(fis, zos);
                }
                // fione-serving.jar
                zos.putNextEntry(new ZipEntry("serving/fione-serving.jar"));
                final var libPath = ResourceUtil.getEnvPath("fione", "lib");
                final var jarPaths = Files.list(libPath).filter(f -> {
                    final var fileName = f.getFileName().toString();
                    return fileName.startsWith("fione-serving-") && fileName.endsWith("jar");
                }).toArray(n -> new Path[n]);
                if (jarPaths.length == 0) {
                    throw new FioneSystemException("fione-serving.jar is not found.");
                }
                try (var fis = Files.newInputStream(jarPaths[0])) {
                    CopyUtil.copy(fis, zos);
                }
                // mojo
                zos.putNextEntry(new ZipEntry("serving/model.zip"));
                CopyUtil.copy(in, zos);
            } catch (final IOException e) {
                throw new IORuntimeException(e);
            }
        }, e -> logger.warn("Failed to write {} in {}", modelId, projectId, e));
    }

    public void deleteModel(final String sessionKey, final String projectId, final String modelId) {
        final var response = h2oHelper.deleteModel(sessionKey, new ModelKeyV3(modelId)).execute();
        if (logger.isDebugEnabled()) {
            logger.debug("deleteFrame: {}", response);
        }
        if (response.code() == 200) {
            logger.info("Deleted frame: {}", modelId);
        } else {
            throw new H2oAccessException("Failed to delete model " + modelId + " : " + response);
        }

        responseCache.invalidate(getLeaderboardsCacheKey(projectId));
        responseCache.invalidate(getModelCacheKey(projectId, modelId));
    }

    public void importModel(final String sessionKey, final String projectId, final String leaderboardId, final String modelId) {
        final var workingJob = createWorkingJob(modelId, "Import Model", 0.5f);
        store(sessionKey, projectId, workingJob);
        h2oHelper.importModel(sessionKey, modelId, getS3ModelPath(projectId, leaderboardId, modelId)).execute(importModelResponse -> {
            if (logger.isDebugEnabled()) {
                logger.debug("importModel: {}", importModelResponse);
            }
            if (importModelResponse.code() == 200) {
                finish(sessionKey, projectId, workingJob, null);
            } else {
                logger.warn("Failed to import frame: {}", importModelResponse);
                finish(sessionKey, projectId, workingJob, new H2oAccessException("Failed to access " + importModelResponse));
            }
            responseCache.invalidate(getModelCacheKey(projectId, modelId));
        }, t -> {
            logger.warn("Failed to import model: {}", modelId, t);
            finish(sessionKey, projectId, workingJob, t);
        });
    }

    public void exportModel(final String sessionKey, final String projectId, final String leaderboardId, final String modelId) {
        final var model = getModel(sessionKey, projectId, leaderboardId, modelId);
        if (model == null) {
            throw new H2oAccessException(modelId + " is not found in " + projectId);
        }

        final var json = modelHelper.serialize(model);
        if (logger.isDebugEnabled()) {
            logger.debug("model: {}", json);
        }

        final var workingJob = createWorkingJob(modelId, "Export Model", 0.2f);
        store(sessionKey, projectId, workingJob);
        try {
            store(sessionKey, projectId, leaderboardId, model);
            finish(sessionKey, projectId, workingJob, null);
        } catch (final Exception e) {
            logger.warn("Failed to export frame: {}/{}/{}", projectId, leaderboardId, modelId, e);
            finish(sessionKey, projectId, workingJob, new H2oAccessException("Failed to access " + modelId));
        }
    }

    public void exportAllModels(final String sessionKey, final String projectId, final String leaderboardId) {
        final var leaderboard = getLeaderboard(sessionKey, projectId, leaderboardId);
        if (leaderboard == null) {
            throw new H2oAccessException(leaderboardId + " is not found in " + projectId);
        }

        new Thread(
                () -> {
                    final var counter = new AtomicInteger(0);
                    final var workingJob = createWorkingJob(leaderboardId, "Export All Models", 0.0f);
                    store(sessionKey, projectId, workingJob);

                    store(projectId, leaderboard);

                    workingJob.progress = 0.1f;
                    store(sessionKey, projectId, workingJob);

                    final var size = leaderboard.models.length;
                    Arrays.stream(leaderboard.models).map(m -> m.name).forEach(modelId -> {
                        final var model = getModel(sessionKey, projectId, leaderboardId, modelId);
                        if (model == null) {
                            logger.warn("{} is not found in {}", modelId, projectId);
                            return;
                        }

                        try {
                            store(sessionKey, projectId, leaderboardId, model);
                        } catch (final Exception e) {
                            logger.warn("Failed to store model: {} : {} : {}", projectId, leaderboardId, model, e);
                        }

                        final var current = counter.addAndGet(1);
                        workingJob.progress = (float) current / (float) size * 0.9f + 0.1f;
                        store(sessionKey, projectId, workingJob);
                    });

                    workingJob.progress = 1.0f;
                    if (counter.get() == size) {
                        finish(sessionKey, projectId, workingJob, null);
                    } else {
                        finish(sessionKey, projectId, workingJob, new H2oAccessException("Failed to export " + (size - counter.get())
                                + " models."));
                    }
                }, "ExportAllModels").start();
    }

    protected void store(final String projectId, final LeaderboardV99 leaderboard) {
        final var fessConfig = ComponentUtil.getFessConfig();
        final var minioClient = createClient(fessConfig);
        final var json = gson.toJson(leaderboard);
        if (logger.isDebugEnabled()) {
            logger.debug("model: {}", json);
        }
        final var objectName = getLeaderboardConfigPath(projectId, leaderboard.projectName);
        try (var bais = new ByteArrayInputStream(json.getBytes(Constants.UTF_8_CHARSET))) {
            final var bucketName = fessConfig.getStorageBucket();
            minioClient.putObject(PutObjectArgs.builder().bucket(bucketName).object(objectName)
                    .stream(bais, -1, PutObjectArgs.MIN_MULTIPART_SIZE).build());
        } catch (final Exception e) {
            throw new StorageException("Failed to create " + objectName, e);
        }
    }

    protected void store(final String sessionKey, final String projectId, final String leaderboardId, final ModelSchemaBaseV3 model) {
        final var fessConfig = ComponentUtil.getFessConfig();
        final var minioClient = createClient(fessConfig);
        final var json = modelHelper.serialize(model);
        if (logger.isDebugEnabled()) {
            logger.debug("model: {}", json);
        }
        final var modelId = keyToString(model.modelId);
        final var objectName = getModelConfigPath(projectId, leaderboardId, modelId);
        try (var bais = new ByteArrayInputStream(json.getBytes(Constants.UTF_8_CHARSET))) {
            final var bucketName = fessConfig.getStorageBucket();
            minioClient.putObject(PutObjectArgs.builder().bucket(bucketName).object(objectName)
                    .stream(bais, -1, PutObjectArgs.MIN_MULTIPART_SIZE).build());
        } catch (final Exception e) {
            throw new StorageException("Failed to create " + objectName, e);
        }

        try {
            final var exportModelResponse =
                    h2oHelper.exportModel(sessionKey, modelId, getS3ModelPath(projectId, leaderboardId, modelId)).execute();
            if (logger.isDebugEnabled()) {
                logger.debug("exportModel: {}", exportModelResponse);
            }
            if (exportModelResponse.code() != 200) {
                throw new StorageException("Failed to export frame: " + exportModelResponse);
            }
        } catch (final Exception e) {
            throw new StorageException("Failed to export model: " + modelId, e);
        }

        if (model instanceof ModelSchemaV3) {
            @SuppressWarnings("rawtypes")
            final var output = ((ModelSchemaV3) model).output;
            if (output != null && output.crossValidationModels != null) {
                for (final ModelKeyV3 key : output.crossValidationModels) {
                    try {
                        var subModel = getLocalModel(sessionKey, projectId, leaderboardId, keyToString(key));
                        if (subModel == null) {
                            subModel = getModel(sessionKey, projectId, leaderboardId, keyToString(key));
                            store(sessionKey, projectId, leaderboardId, subModel);
                        }
                    } catch (final Exception e) {
                        logger.warn("Failed to store sub-model: {}", key, e);
                    }
                }
            }
        }
    }

    protected InputStream openStorageObject(final MinioClient minioClient, final String bucketName, final String objectName) {
        for (var i = 0; i < 60; i++) {
            try {
                return minioClient.getObject(GetObjectArgs.builder().bucket(bucketName).object(objectName).build());
            } catch (final ErrorResponseException e) {
                if (!NO_SUCH_OBJECT.equalsIgnoreCase(e.errorResponse().code())) {
                    throw new StorageException("Failed to access " + objectName, e);
                }
            } catch (final Exception e) {
                throw new StorageException("Failed to access " + objectName, e);
            }
            ThreadUtil.sleepQuietly(1000L);
        }
        throw new StorageException(objectName + " does not exist");
    }

    public void filterColumns(final String sessionKey, final String projectId, final DataSet dataSet, final Map<String, String> columnMap) {
        final var fessConfig = ComponentUtil.getFessConfig();
        final var minioClient = createClient(fessConfig);
        final var objectName = getDataPath(projectId, dataSet.getName());
        final var tempObjectName = objectName + ".tmp";
        final var csvConfig = new CsvConfig(',', '"', '"');
        csvConfig.setIgnoreEmptyLines(true);
        try (final var csvReader =
                new CsvReader(new InputStreamReader(openStorageObject(minioClient, fessConfig.getStorageBucket(), objectName),
                        Constants.UTF_8_CHARSET), csvConfig)) {
            final Map<String, Integer> indexMap = new HashMap<>();
            final var headerList = csvReader.readValues();
            for (var i = 0; i < headerList.size(); i++) {
                final var name = headerList.get(i);
                if (columnMap.containsKey(name)) {
                    indexMap.put(columnMap.get(name), i);
                }
            }
            if (indexMap.isEmpty()) {
                if (logger.isDebugEnabled()) {
                    logger.debug("columns do not exist: {}", columnMap);
                }
                return;
            }

            try (final var pipedOut = new PipedOutputStream(); final var pipedIn = new PipedInputStream()) {
                final var pipeWriter =
                        new Thread(() -> {
                            try {
                                minioClient.putObject(PutObjectArgs.builder().bucket(fessConfig.getStorageBucket()).object(tempObjectName)
                                        .stream(pipedIn, -1, PutObjectArgs.MIN_MULTIPART_SIZE).build());
                            } catch (final Exception e) {
                                logger.warn("Failed to write {}.", tempObjectName, e);
                            }
                        }, "Filtercolumns");

                pipedIn.connect(pipedOut);
                pipeWriter.start();

                try (final var csvWriter = new CsvWriter(new OutputStreamWriter(pipedOut), csvConfig)) {
                    final var indices = columnMap.values().stream().collect(Collectors.toList());
                    csvWriter.writeValues(indices);
                    List<String> list;
                    while ((list = csvReader.readValues()) != null) {
                        final var l = list;
                        final var valueList = indices.stream().map(s -> {
                            if (indexMap.containsKey(s)) {
                                final int index = indexMap.get(s);
                                if (index < l.size()) {
                                    return l.get(index);
                                }
                            }
                            return StringUtil.EMPTY;
                        }).collect(Collectors.toList());
                        csvWriter.writeValues(valueList);
                    }
                }
                pipeWriter.join();
            }
        } catch (final Exception e) {
            throw new StorageException("Failed to write " + objectName, e);
        }

        try {
            if (logger.isDebugEnabled()) {
                logger.debug("copying {} to {}.", tempObjectName, objectName);
            }
            minioClient.copyObject(CopyObjectArgs.builder()
                    .source(CopySource.builder().bucket(fessConfig.getStorageBucket()).object(objectName).build())
                    .bucket(fessConfig.getStorageBucket()).object(tempObjectName).build());
            if (logger.isDebugEnabled()) {
                logger.debug("removing {}.", tempObjectName);
            }
            minioClient.removeObject(RemoveObjectArgs.builder().bucket(fessConfig.getStorageBucket()).object(tempObjectName).build());
        } catch (final Exception e) {
            throw new StorageException("Failed to update " + objectName, e);
        }
    }

    protected JobV3 createWorkingJob(final String target, final String description, final float progress) {
        final var job = new JobV3();
        job.key = new JobKeyV3(UuidUtil.create());
        job.key.type = "Key<Job>";
        job.description = description;
        job.status = JobV3.RUNNING;
        job.progress = progress;
        job.startTime = System.currentTimeMillis();
        job.msec = 0L;
        job.dest = new KeyV3(target);
        job.exception = null;
        job.stacktrace = null;
        job.readyForView = true;
        return job;
    }

    protected void finish(final String sessionKey, final String projectId, final JobV3 job, final Throwable t) {
        job.progress = 1.0f;
        job.msec = System.currentTimeMillis() - job.startTime;
        if (t == null) {
            job.status = JobV3.DONE;
        } else {
            job.status = JobV3.FAILED;
            job.exception = t.getMessage();
            try (var writer = new StringWriter()) {
                t.printStackTrace(new PrintWriter(writer, true));
                writer.flush();
                job.stacktrace = writer.toString();
            } catch (final IOException e) {
                // ignore
            }
        }
        store(sessionKey, projectId, job);
    }

    public void executeModule(final String sessionKey, final String projectId, final PythonModule pythonModule,
            final Map<String, Object> params) {
        final var workingJob = createWorkingJob(pythonModule.getId(), pythonModule.getName(), 0.1f);
        store(sessionKey, projectId, workingJob);
        final BlockingQueue<String> queue = new LinkedBlockingQueue<>(10);
        try {
            new Thread(() -> {
                try {
                    pythonModule.execute(params, progress -> {
                        if (logger.isDebugEnabled()) {
                            logger.debug("MODULE OUTPUT: {}", progress);
                        }
                        if (StringUtil.isBlank(progress) || !progress.startsWith("FIONE:")) {
                            return;
                        }
                        queue.add(progress);
                    });
                    finish(sessionKey, projectId, workingJob, null);
                } catch (final Exception e) {
                    logger.warn("Failed to execute module: projectId:{}, params:{}", projectId, params, e);
                    finish(sessionKey, projectId, workingJob, e);
                } finally {
                    queue.add(FIONE_END);
                }
            }, "ExecuteModule").start();
            new Thread(() -> {
                final var objectMapper = new ObjectMapper();
                while (true) {
                    final String progress;
                    try {
                        progress = queue.take();
                    } catch (final InterruptedException e) {
                        logger.debug("Interrupted.", e);
                        break;
                    }
                    if (logger.isDebugEnabled()) {
                        logger.debug("Module Response: {}", progress);
                    }
                    if (FIONE_END.equals(progress)) {
                        break;
                    }
                    final var values = StringUtils.split(progress, ":", 2);
                    if (values.length != 2) {
                        continue;
                    }
                    try {
                        final var response = objectMapper.readValue(values[1], new TypeReference<Map<String, Object>>() {
                        });
                        processModuleResponse(sessionKey, projectId, workingJob, response);
                    } catch (final Exception e) {
                        logger.warn("Failed to process {}", values[1], e);
                    }
                }
            }, "ExecuteModuleReceiver").start();
        } catch (final Exception e) {
            logger.warn("Failed to execute module: projectId:{}, params:{}", projectId, params, e);
            finish(sessionKey, projectId, workingJob, e);
        }
    }

    protected void processModuleResponse(final String sessionKey, final String projectId, final JobV3 workingJob,
            final Map<String, Object> params) {
        if (logger.isDebugEnabled()) {
            logger.debug("response params: {}", params);
        }
        final var responseType = (String) params.get("type");
        switch (responseType) {
        case "progress":
            processProgressModuleResponse(sessionKey, projectId, workingJob, params);
            break;
        case "leaderboard":
            processLeaderboardModuleResponse(sessionKey, projectId, workingJob, params);
            break;
        case "model":
            processModelModuleResponse(sessionKey, projectId, workingJob, params);
            break;
        case "ini_file":
            processIniFileModuleResponse(sessionKey, projectId, workingJob, params);
            break;
        default:
            logger.warn("Unknown type: {} = {}", responseType, params);
            break;
        }
    }

    protected void processIniFileModuleResponse(final String sessionKey, final String projectId, final JobV3 workingJob,
            final Map<String, Object> params) {
        if (params.containsKey("progress")) {
            workingJob.progress = ((Double) params.get("progress")).floatValue();
        }
        if (params.containsKey("content")) {
            workingJob.iniData = (String) params.get("content");
            store(sessionKey, projectId, workingJob);
        }
    }

    protected void processProgressModuleResponse(final String sessionKey, final String projectId, final JobV3 workingJob,
            final Map<String, Object> params) {
        if (params.containsKey("message")) {
            workingJob.progressMsg = (String) params.get("message");
        }
        if (params.containsKey("progress")) {
            workingJob.progress = ((Double) params.get("progress")).floatValue();
            store(sessionKey, projectId, workingJob);
        }
    }

    protected void processLeaderboardModuleResponse(final String sessionKey, final String projectId, final JobV3 workingJob,
            final Map<String, Object> params) {
        final var leaderboardId = (String) params.get("leaderboard_id");
        var leaderboard = getLocalLeaderboard(sessionKey, projectId, leaderboardId);
        if (leaderboard != null) {
            deleteLeaderboard(sessionKey, projectId, leaderboardId);
        }

        leaderboard = new LeaderboardV99();
        leaderboard.projectName = leaderboardId;
        store(projectId, leaderboard);
    }

    protected void processModelModuleResponse(final String sessionKey, final String projectId, final JobV3 workingJob,
            final Map<String, Object> params) {
        final var leaderboardId = (String) params.get("leaderboard_id");
        var leaderboard = getLocalLeaderboard(sessionKey, projectId, leaderboardId);
        if (leaderboard == null) {
            leaderboard = new LeaderboardV99();
            leaderboard.projectName = leaderboardId;
        }

        final var modelId = (String) params.get("model_id");
        responseCache.invalidate(getModelCacheKey(projectId, modelId));
        final var model = getModel(sessionKey, projectId, leaderboardId, modelId);
        if (model == null) {
            throw new H2oAccessException("Model " + modelId + " is not found.");
        }

        final var size = leaderboard.models == null ? 0 : leaderboard.models.length;
        final var newModels = new ModelKeyV3[size + 1];
        var i = 0;
        while (i < size) {
            newModels[i] = leaderboard.models[i];
            i++;
        }
        newModels[i] = model.modelId;
        leaderboard.models = newModels;
        store(projectId, leaderboard);
        store(sessionKey, projectId, leaderboardId, model);
    }

    public void deleteLeaderboard(final String sessionKey, final String projectId, final String leaderboardId) {
        final var fessConfig = ComponentUtil.getFessConfig();
        final var minioClient = createClient(fessConfig);
        final var leaderboardDir = projectFolderName + "/" + projectId + "/model/" + StringCodecUtil.encodeUrlSafe(leaderboardId) + "/";
        final List<DeleteObject> objectNameList = new ArrayList<>();
        try {
            for (final Result<Item> result : minioClient.listObjects(ListObjectsArgs.builder().bucket(fessConfig.getStorageBucket())
                    .prefix(leaderboardDir).recursive(true).build())) {
                final var item = result.get();
                final var objectName = item.objectName();
                objectNameList.add(new DeleteObject(objectName));
            }
            objectNameList.add(new DeleteObject(getLeaderboardConfigPath(projectId, leaderboardId)));
            final var results =
                    minioClient.removeObjects(RemoveObjectsArgs.builder().bucket(fessConfig.getStorageBucket()).objects(objectNameList)
                            .build());
            for (final Result<DeleteError> result : results) {
                logger.warn("Failed to delete {}", result.get());
            }
        } catch (final Exception e) {
            throw new StorageException("Failed to delete " + leaderboardDir, e);
        }

        responseCache.invalidate(getLeaderboardsCacheKey(projectId));
        responseCache.invalidate(getLeaderboardCacheKey(projectId, leaderboardId));
    }

    public String[] getLeaderboardIds(final String sessionKey, final String projectId) {
        try {
            final var cacheKey = getLeaderboardsCacheKey(projectId);
            return (String[]) responseCache.get(cacheKey, () -> {
                final List<String> idList = new ArrayList<>();
                final var response = h2oHelper.getLeaderboards(sessionKey).execute();
                if (logger.isDebugEnabled()) {
                    logger.debug("getLeaderboards: {}", response);
                }
                if (response.code() == 200) {
                    final var leaderboards = response.body();
                    final var prefix = StringCodecUtil.decode(projectId);
                    for (final LeaderboardV99 leaderboard : leaderboards.leaderboards) {
                        final var projectName = leaderboard.projectName;
                        if (projectName.startsWith(prefix)) {
                            idList.add(projectName);
                        }
                    }
                }

                stream(getLocalLeaderboardIds(projectId)).of(stream -> stream.filter(s -> !idList.contains(s)).forEach(idList::add));
                return idList.toArray(n -> new String[n]);
            });
        } catch (final Exception e) {
            if (e.getCause() instanceof CacheNotFoundException) {
                return StringUtil.EMPTY_STRINGS;
            }
            if (logger.isDebugEnabled()) {
                logger.debug("Failed to get data from cache.", e);
            }
            return StringUtil.EMPTY_STRINGS;
        }
    }

    public String[] getLocalLeaderboardIds(final String projectId) {
        final var fessConfig = ComponentUtil.getFessConfig();
        final var leaderboardDir = projectFolderName + "/" + projectId + "/model/";
        final List<String> list = new ArrayList<>();
        try {
            final var minioClient = createClient(fessConfig);
            for (final Result<Item> result : minioClient.listObjects(ListObjectsArgs.builder().bucket(fessConfig.getStorageBucket())
                    .prefix(leaderboardDir).recursive(false).build())) {
                final var item = result.get();
                final var objectName = item.objectName();
                if (logger.isDebugEnabled()) {
                    logger.debug("objectName: {}", objectName);
                }
                if (!objectName.endsWith(".json")) {
                    if (logger.isDebugEnabled()) {
                        logger.debug("Skipped: {}", objectName);
                    }
                    continue;
                }
                final var values = objectName.split("/");
                list.add(StringCodecUtil.decode(values[values.length - 1].replaceFirst(".json$", StringUtil.EMPTY)));
            }
        } catch (final Exception e) {
            if (logger.isDebugEnabled()) {
                logger.debug("Failed to access " + fessConfig.getStorageEndpoint(), e);
            }
        }
        return list.toArray(n -> new String[n]);
    }

    protected LeaderboardV99 getLocalLeaderboard(final String sessionKey, final String projectId, final String leaderboardId) {
        final var fessConfig = ComponentUtil.getFessConfig();
        final var minioClient = createClient(fessConfig);
        final var objectName = getLeaderboardConfigPath(projectId, leaderboardId);
        try (Reader reader =
                new InputStreamReader(minioClient.getObject(GetObjectArgs.builder().bucket(fessConfig.getStorageBucket())
                        .object(objectName).build()), Constants.UTF_8_CHARSET)) {
            final var leaderboard = gson.fromJson(reader, LeaderboardV99.class);
            leaderboard.setInLocal(true);
            return leaderboard;
        } catch (final ErrorResponseException e) {
            final var code = e.errorResponse().code();
            if (NO_SUCH_KEY.equalsIgnoreCase(code) || NO_SUCH_OBJECT.equalsIgnoreCase(code)) {
                return null;
            }
            throw new StorageException("Failed to read " + objectName, e);
        } catch (final Exception e) {
            throw new StorageException("Failed to read " + objectName, e);
        }
    }

    protected ModelSchemaBaseV3 getLocalModel(final String sessionKey, final String projectId, final String leaderboardId,
            final String modelId) {
        final var fessConfig = ComponentUtil.getFessConfig();
        final var minioClient = createClient(fessConfig);
        final var objectName = getModelConfigPath(projectId, leaderboardId, modelId);
        try (Reader reader =
                new InputStreamReader(minioClient.getObject(GetObjectArgs.builder().bucket(fessConfig.getStorageBucket())
                        .object(objectName).build()), Constants.UTF_8_CHARSET)) {
            final var model = modelHelper.deserialize(reader);
            model.setInLocal(true);
            return model;
        } catch (final ErrorResponseException e) {
            final var code = e.errorResponse().code();
            if (NO_SUCH_KEY.equalsIgnoreCase(code) || NO_SUCH_OBJECT.equalsIgnoreCase(code)) {
                return null;
            }
            throw new StorageException("Failed to read " + objectName, e);
        } catch (final Exception e) {
            throw new StorageException("Failed to read " + objectName, e);
        }
    }

    protected String getPredictCsvPath(final String projectId, final String name) {
        final var fessConfig = ComponentUtil.getFessConfig();
        return "s3a://" + fessConfig.getStorageBucket() + "/" + projectFolderName + "/" + projectId + "/data/" + name
                + (name.endsWith(".csv") ? StringUtil.EMPTY : ".csv");
    }

    protected String getDataPath(final String projectId, final String fileName) {
        return projectFolderName + "/" + projectId + "/data/" + fileName;
    }

    protected String getProjectConfigPath(final String projectId) {
        return projectFolderName + "/" + projectId + "/project.json";
    }

    protected String getJobsConfigPath(final String projectId) {
        return projectFolderName + "/" + projectId + "/jobs.json";
    }

    protected String getDataSetConfigPath(final String projectId, final String dataSetId) {
        return projectFolderName + "/" + projectId + "/config/" + dataSetId + "_dataset.json";
    }

    protected String getS3Path(final String projectId, final String fileName) {
        final var fessConfig = ComponentUtil.getFessConfig();
        return "s3://" + fessConfig.getStorageBucket() + "/" + projectFolderName + "/" + projectId + "/data/" + fileName;
    }

    protected String getLeaderboardConfigPath(final String projectId, final String leaderboardId) {
        return projectFolderName + "/" + projectId + "/model/" + StringCodecUtil.encodeUrlSafe(leaderboardId) + ".json";
    }

    protected String getModelConfigPath(final String projectId, final String leaderboardId, final String modelId) {
        return projectFolderName + "/" + projectId + "/model/" + StringCodecUtil.encodeUrlSafe(leaderboardId) + "/" + modelId + ".json";
    }

    protected String getS3ModelPath(final String projectId, final String leaderboardId, final String modelId) {
        final var fessConfig = ComponentUtil.getFessConfig();
        return "s3a://" + fessConfig.getStorageBucket() + "/" + projectFolderName + "/" + projectId + "/model/"
                + StringCodecUtil.encodeUrlSafe(leaderboardId) + "/" + modelId;
    }

    private String getFrameSummaryCacheKey(final String projectId, final String frameId) {
        return "frameSummary@" + projectId + "," + frameId;
    }

    private String getLeaderboardCacheKey(final String projectId, final String leaderboardId) {
        return "leaderboard@" + projectId + "," + leaderboardId;
    }

    private String getModelCacheKey(final String projectId, final String modelId) {
        return "model@" + projectId + "," + modelId;
    }

    private String getLeaderboardsCacheKey(final String projectId) {
        return "leaderboads@" + projectId;
    }

}
