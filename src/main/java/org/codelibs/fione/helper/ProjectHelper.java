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
import org.codelibs.fione.h2o.bindings.pojos.FramesListV3;
import org.codelibs.fione.h2o.bindings.pojos.FramesV3;
import org.codelibs.fione.h2o.bindings.pojos.JobKeyV3;
import org.codelibs.fione.h2o.bindings.pojos.JobV3;
import org.codelibs.fione.h2o.bindings.pojos.JobV3.Kind;
import org.codelibs.fione.h2o.bindings.pojos.JobsV3;
import org.codelibs.fione.h2o.bindings.pojos.KeyV3;
import org.codelibs.fione.h2o.bindings.pojos.LeaderboardV99;
import org.codelibs.fione.h2o.bindings.pojos.LeaderboardsV99;
import org.codelibs.fione.h2o.bindings.pojos.ModelExportV3;
import org.codelibs.fione.h2o.bindings.pojos.ModelKeyV3;
import org.codelibs.fione.h2o.bindings.pojos.ModelMetricsListSchemaV3;
import org.codelibs.fione.h2o.bindings.pojos.ModelOutputSchemaV3;
import org.codelibs.fione.h2o.bindings.pojos.ModelSchemaBaseV3;
import org.codelibs.fione.h2o.bindings.pojos.ModelSchemaV3;
import org.codelibs.fione.h2o.bindings.pojos.ModelsV3;
import org.codelibs.fione.h2o.bindings.pojos.ParseV3;
import org.codelibs.fione.h2o.bindings.pojos.RapidsSchemaV3;
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

import io.minio.ErrorCode;
import io.minio.MinioClient;
import io.minio.PutObjectOptions;
import io.minio.Result;
import io.minio.errors.ErrorResponseException;
import io.minio.messages.DeleteError;
import io.minio.messages.Item;
import retrofit2.Response;

public class ProjectHelper {

    private static final Logger logger = LogManager.getLogger(ProjectHelper.class);

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
        final FessConfig fessConfig = ComponentUtil.getFessConfig();
        final CacheBuilder<Object, Object> cacheBuilder = CacheBuilder.newBuilder();
        if (ManagedHotdeploy.isHotdeploy()) {
            cacheBuilder.expireAfterWrite(10, TimeUnit.SECONDS);
        } else {
            cacheBuilder.expireAfterWrite(fessConfig.getSystemPropertyAsInt("fione.api.cache.expire", 1), TimeUnit.MINUTES);
        }
        responseCache = cacheBuilder.build();
    }

    public Project[] getProjects() {
        final FessConfig fessConfig = ComponentUtil.getFessConfig();
        final List<Project> list = new ArrayList<>();
        try {
            final MinioClient minioClient = createClient(fessConfig);
            for (final Result<Item> result : minioClient.listObjects(fessConfig.getStorageBucket(), projectFolderName + "/", false)) {
                final Item item = result.get();
                final String objectName = item.objectName();
                if (logger.isDebugEnabled()) {
                    logger.debug("objectName: {}", objectName);
                }
                final String[] values = objectName.split("/");
                if (values.length == 2) {
                    final Project project = new Project(values[1]);
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
            return new MinioClient(fessConfig.getStorageEndpoint(), fessConfig.getStorageAccessKey(), fessConfig.getStorageSecretKey());
        } catch (final Exception e) {
            throw new StorageException("Failed to create MinioClient: " + fessConfig.getStorageEndpoint(), e);
        }
    }

    public void store(final Project project) {
        if (logger.isDebugEnabled()) {
            logger.debug("Store project:{}", project);
        }
        final FessConfig fessConfig = ComponentUtil.getFessConfig();
        final MinioClient minioClient = createClient(fessConfig);
        final String json = gson.toJson(project);
        if (logger.isDebugEnabled()) {
            logger.debug("project: {}", json);
        }
        final String objectName = getProjectConfigPath(project.getId());
        try (ByteArrayInputStream bais = new ByteArrayInputStream(json.getBytes(Constants.UTF_8_CHARSET))) {
            final String bucketName = fessConfig.getStorageBucket();
            if (!minioClient.bucketExists(bucketName)) {
                minioClient.makeBucket(bucketName);
                logger.info("Create bucket {}.", bucketName);
            }
            minioClient.putObject(bucketName, objectName, bais, new PutObjectOptions(-1, PutObjectOptions.MIN_MULTIPART_SIZE));
        } catch (final Exception e) {
            throw new StorageException("Failed to create " + objectName, e);
        }
    }

    public Project getProject(final String projectId) {
        return getProject(projectId, true);
    }

    protected Project getProject(final String projectId, final boolean loadParams) {
        final FessConfig fessConfig = ComponentUtil.getFessConfig();
        final MinioClient minioClient = createClient(fessConfig);
        final String objectName = getProjectConfigPath(projectId);
        try (Reader reader =
                new InputStreamReader(minioClient.getObject(fessConfig.getStorageBucket(), objectName), Constants.UTF_8_CHARSET)) {
            final Project project = gson.fromJson(reader, Project.class);
            if (loadParams) {
                project.setDataSets(getDataSets(fessConfig, minioClient, projectId));
                project.setFrameIds(getFrames(project));
                project.setJobs(getJobs(projectId));
            }
            return project;
        } catch (final Exception e) {
            throw new StorageException("Failed to read " + objectName, e);
        }
    }

    public boolean projectExists(final String projectId) {
        try {
            return getProject(projectId, false) != null;
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

    protected String[] getFrames(final Project project) {
        return getFrames(project, String::startsWith);
    }

    protected String[] getFrames(final Project project, final BiPredicate<String, String> condition) {
        final List<String> frameIdList = new ArrayList<>();
        Arrays.stream(project.getDataSets()).map(d -> getFrameName(project.getId(), d.getId())).forEach(baseName -> {
            try {
                final Response<FramesListV3> response = h2oHelper.getFrames(baseName).execute(requestTimeout);
                if (logger.isDebugEnabled()) {
                    logger.debug("getFrames: {}", response);
                }
                if (response.code() == 200) {
                    for (final FrameBaseV3 frame : response.body().frames) {
                        final String frameId = keyToString(frame.frameId);
                        if (frameId != null && condition.test(frameId, baseName)) {
                            frameIdList.add(frameId);
                        }
                    }
                } else {
                    logger.warn("Failed to get frames: {}", response);
                }
            } catch (final Exception e) {
                final String msg = e.getMessage();
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
        final FessConfig fessConfig = ComponentUtil.getFessConfig();
        final MinioClient minioClient = createClient(fessConfig);
        return getDataSets(fessConfig, minioClient, projectId);
    }

    protected DataSet[] getDataSets(final FessConfig fessConfig, final MinioClient minioClient, final String projectId) {
        final String prefix = projectFolderName + "/" + projectId + "/data/";
        final List<DataSet> list = new ArrayList<>();
        for (final Result<Item> result : minioClient.listObjects(fessConfig.getStorageBucket(), prefix, false)) {
            try {
                final Item item = result.get();
                final String objectName = item.objectName();
                final String[] values = objectName.split("/");
                if (values.length == 4) {
                    final String dataSetId = StringCodecUtil.encodeUrlSafe(values[3]);
                    final DataSet dataSet = getDataSet(fessConfig, minioClient, projectId, dataSetId);
                    list.add(dataSet);
                }
            } catch (final Exception e) {
                logger.warn("Failed to read dataset", e);
            }
        }
        return list.toArray(n -> new DataSet[n]);
    }

    public DataSet getDataSet(final String projectId, final String dataSetId) {
        final FessConfig fessConfig = ComponentUtil.getFessConfig();
        final MinioClient minioClient = createClient(fessConfig);
        return getDataSet(fessConfig, minioClient, projectId, dataSetId);
    }

    protected DataSet getDataSet(final FessConfig fessConfig, final MinioClient minioClient, final String projectId, final String dataSetId) {
        final String objectName = getDataSetConfigPath(projectId, dataSetId);
        try (Reader reader =
                new InputStreamReader(minioClient.getObject(fessConfig.getStorageBucket(), objectName), Constants.UTF_8_CHARSET)) {
            return gson.fromJson(reader, DataSet.class);
        } catch (final Exception e) {
            if (logger.isDebugEnabled()) {
                logger.warn("Failed to read " + objectName, e);
            }
        }
        return createDataSet(projectId, dataSetId);
    }

    public DataSet addDataSet(final String projectId, final String fileName, final InputStream in) {
        final FessConfig fessConfig = ComponentUtil.getFessConfig();
        final MinioClient minioClient = createClient(fessConfig);
        final String objectName = getDataPath(projectId, fileName);
        try {
            minioClient.putObject(fessConfig.getStorageBucket(), objectName, in, new PutObjectOptions(-1,
                    PutObjectOptions.MIN_MULTIPART_SIZE));
        } catch (final Exception e) {
            throw new StorageException("Failed to store " + objectName, e);
        }

        final DataSet dataSet = createDataSet(projectId, StringCodecUtil.encodeUrlSafe(fileName));
        if (fileName.toLowerCase(Locale.ROOT).contains("test")) {
            dataSet.setType(DataSet.TEST);
        }
        store(projectId, dataSet);

        return dataSet;
    }

    protected DataSet createDataSet(final String projectId, final String dataSetId) {
        final DataSet dataSet = new DataSet(dataSetId);
        dataSet.setPath(getS3Path(projectId, dataSet.getName()));
        return dataSet;
    }

    public void deleteDataSet(final String projectId, final String dataSetId) {
        final FessConfig fessConfig = ComponentUtil.getFessConfig();
        final MinioClient minioClient = createClient(fessConfig);

        final DataSet dataSet = getDataSet(fessConfig, minioClient, projectId, dataSetId);
        if (dataSet.getSchema() != null) {
            final FrameKeyV3 destinationFrame = dataSet.getSchema().destinationFrame;
            h2oHelper.deleteFrame(destinationFrame).execute(deleteFrameResponse -> {
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

        final String name = StringCodecUtil.decode(dataSetId);
        final String dataPath = getDataPath(projectId, name);
        final String configPath = getDataSetConfigPath(projectId, dataSetId);
        try {
            final Iterable<Result<DeleteError>> results =
                    minioClient.removeObjects(fessConfig.getStorageBucket(), Lists.newArrayList(dataPath, configPath));
            for (final Result<DeleteError> result : results) {
                logger.warn("Failed to delete {}", result.get());
            }
        } catch (final Exception e) {
            throw new StorageException("Failed to delete data files.", e);
        }
    }

    public void loadDataSetSchema(final String projectId, final DataSet dataSet) {
        loadDataSetSchema(projectId, dataSet, () -> {});
    }

    public void loadDataSetSchema(final String projectId, final DataSet dataSet, final Runnable chain) {
        final JobV3 workingJob = createWorkingJob(dataSet.getName(), "Parse Schema", 0.2f);
        store(projectId, workingJob);
        h2oHelper.importFiles(dataSet.getPath()).execute(importResponse -> {
            if (logger.isDebugEnabled()) {
                logger.debug("importFiles: {}", importResponse);
            }
            if (importResponse.code() == 200) {
                final String[] frames = importResponse.body().destinationFrames;
                h2oHelper.setupParse(frames).execute(setupResponse -> {
                    if (logger.isDebugEnabled()) {
                        logger.debug("setupParse: {}", setupResponse);
                    }
                    if (setupResponse.code() == 200) {
                        final ParseV3 meta = h2oHelper.convert(setupResponse.body());
                        meta.destinationFrame = new FrameKeyV3(getFrameName(projectId, dataSet.getId()) + ".hex");
                        dataSet.setSchema(meta);
                        store(projectId, dataSet);
                        h2oHelper.deleteFrame(frames[0]).execute(deleteResponse -> {
                            if (logger.isDebugEnabled()) {
                                logger.debug("deleteFrame: {}", deleteResponse);
                            }
                            chain.run();
                            finish(projectId, workingJob, null);
                        }, t -> {
                            logger.warn("Failed to delete frame: {}", frames[0], t);
                            finish(projectId, workingJob, t);
                        });
                    } else {
                        logger.warn("Failed to parse data: projectId:{}, dataSet:{}", projectId, dataSet);
                        finish(projectId, workingJob, new H2oAccessException("Failed to access " + setupResponse));
                    }
                }, t -> {
                    logger.warn("Failed to parse data: projectId:{}, dataSet:{}", projectId, dataSet, t);
                    finish(projectId, workingJob, t);
                });
            } else {
                logger.warn("Failed to import data: projectId:{}, dataSet:{}", projectId, dataSet);
                finish(projectId, workingJob, new H2oAccessException("Failed to access " + importResponse));
            }
        }, t -> {
            logger.warn("Failed to import data: projectId:{}, dataSet:{}", projectId, dataSet, t);
            finish(projectId, workingJob, t);
        });
    }

    public void store(final String projectId, final DataSet dataSet) {
        if (logger.isDebugEnabled()) {
            logger.debug("Store projectId:{}, dataSet:{}", projectId, dataSet);
        }
        final FessConfig fessConfig = ComponentUtil.getFessConfig();
        final MinioClient minioClient = createClient(fessConfig);
        final String json = gson.toJson(dataSet);
        if (logger.isDebugEnabled()) {
            logger.debug("dataSet: {}", json);
        }
        final String objectName = getDataSetConfigPath(projectId, dataSet.getId());
        try (ByteArrayInputStream bais = new ByteArrayInputStream(json.getBytes(Constants.UTF_8_CHARSET))) {
            minioClient.putObject(fessConfig.getStorageBucket(), objectName, bais, new PutObjectOptions(-1,
                    PutObjectOptions.MIN_MULTIPART_SIZE));
        } catch (final Exception e) {
            throw new StorageException("Failed to create " + objectName, e);
        }
    }

    public FrameV3 getColumnSummaries(final String projectId, final String frameId) {
        try {
            final String cacheKey = getFrameSummaryCacheKey(projectId, frameId);
            return (FrameV3) responseCache.get(cacheKey, () -> {
                final Response<FramesV3> response = h2oHelper.getFrameSummary(frameId).execute();
                if (logger.isDebugEnabled()) {
                    logger.debug("getFrameSummary: {}", response);
                }
                if (response.code() == 200) {
                    final FramesV3 data = response.body();
                    if (data.frames.length == 1) {
                        final FrameV3 frame = data.frames[0];
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

    public void createFrame(final String projectId, final DataSet dataSet, final Consumer<Response<ParseV3>> result) {
        final JobV3 workingJob = createWorkingJob(dataSet.getName(), "Parse Frame", 0.2f);
        store(projectId, workingJob);
        h2oHelper.importFiles(dataSet.getPath()).execute(importResponse -> {
            if (logger.isDebugEnabled()) {
                logger.debug("importFiles: {}", importResponse);
            }
            if (importResponse.code() == 200) {
                h2oHelper.parseFiles(dataSet.getSchema()).execute(parseResponse -> {
                    if (logger.isDebugEnabled()) {
                        logger.debug("parseRes: {}", parseResponse);
                    }
                    if (parseResponse.code() == 200) {
                        logger.info("Create frame: {}", keyToString(parseResponse.body().destinationFrame));
                        deleteJob(projectId, workingJob.key.name);
                        store(projectId, parseResponse.body().job);
                        result.accept(parseResponse);
                    } else {
                        logger.warn("Failed to parse data: dataSet:{}", dataSet);
                        finish(projectId, workingJob, new H2oAccessException("Failed to access " + parseResponse));
                    }
                }, t -> {
                    logger.warn("Failed to parse data: dataSet:{}", dataSet, t);
                    finish(projectId, workingJob, t);
                });
            } else {
                logger.warn("Failed to import data: dataSet:{}", dataSet);
                finish(projectId, workingJob, new H2oAccessException("Failed to access " + importResponse));
            }
        }, t -> {
            logger.warn("Failed to import data: dataSet:{}", dataSet, t);
            finish(projectId, workingJob, new H2oAccessException("Failed to access ", t));
        });
    }

    public void deleteFrame(final String projectId, final String frameId) {
        final Response<FramesV3> response = h2oHelper.deleteFrame(frameId).execute();
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

    protected void deleteFrameQuietly(final String frameId) {
        h2oHelper.deleteFrame(frameId).execute(delteFrameResonse -> logger.info("Deleted frame: {}", frameId),
                t -> logger.warn("Failed to delete frame: {}", frameId, t));
    }

    public void runAutoML(final String projectId, final AutoMLBuildControlV99 buildControl, final AutoMLInputV99 inputSpec,
            final AutoMLBuildModelsV99 buildModels) {
        final JobV3 workingJob =
                createWorkingJob(buildControl.projectName + "@@" + inputSpec.responseColumn.columnName, "AutoML starting", 0.2f);
        store(projectId, workingJob);
        h2oHelper.runAutoML(buildControl, inputSpec, buildModels).execute(autoMLResponse -> {
            if (logger.isDebugEnabled()) {
                logger.debug("runAutoML: {}", autoMLResponse);
            }
            if (autoMLResponse.code() == 200) {
                logger.info("AutoML process started: {}", keyToString(autoMLResponse.body().job.dest));
                deleteJob(projectId, workingJob.key.name);
                store(projectId, autoMLResponse.body().job);
            } else {
                logger.warn("Failed to run AutoML: {}", autoMLResponse);
                finish(projectId, workingJob, new H2oAccessException("Failed to access " + autoMLResponse));
            }
        }, t -> {
            logger.warn("Failed to run AutoML.", t);
            finish(projectId, workingJob, t);
        });
    }

    protected JobV3[] getJobs(final String projectId) {
        return getJobs(projectId, true);
    }

    protected JobV3[] getJobs(final String projectId, final boolean update) {
        final FessConfig fessConfig = ComponentUtil.getFessConfig();
        final MinioClient minioClient = createClient(fessConfig);
        final String objectName = getJobsConfigPath(projectId);
        try (Reader reader =
                new InputStreamReader(minioClient.getObject(fessConfig.getStorageBucket(), objectName), Constants.UTF_8_CHARSET)) {
            final JobV3[] jobs = gson.fromJson(reader, JobV3[].class);
            if (update) {
                jobLock.writeLock().lock();
                try {
                    final List<JobV3> list = new ArrayList<>();
                    for (final JobV3 job : jobs) {
                        if (JobV3.RUNNING.equals(job.status)) {
                            try {
                                final Response<JobsV3> response = h2oHelper.getJobs(keyToString(job.key)).execute(requestTimeout);
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
            final ErrorCode code = e.errorResponse().errorCode();
            if (code == ErrorCode.NO_SUCH_KEY || code == ErrorCode.NO_SUCH_OBJECT) {
                return new JobV3[0];
            }
            throw new StorageException("Failed to read " + objectName, e);
        } catch (final Exception e) {
            throw new StorageException("Failed to read " + objectName, e);
        }

    }

    public void store(final String projectId, final JobV3 job) {
        if (logger.isDebugEnabled()) {
            logger.debug("Insert job:{}", job);
        }
        if (job == null) {
            return;
        }

        jobLock.writeLock().lock();
        try {
            final JobV3[] oldJobs = getJobs(projectId, false);
            for (int i = 0; i < oldJobs.length; i++) {
                if (oldJobs[i].key.name.equals(job.key.name)) {
                    oldJobs[i] = job;
                    store(projectId, oldJobs);
                    return;
                }
            }

            final JobV3[] jobs = Arrays.copyOf(oldJobs, oldJobs.length + 1);
            jobs[jobs.length - 1] = job;
            store(projectId, jobs);
        } finally {
            jobLock.writeLock().unlock();
        }
    }

    public void deleteJob(final String projectId, final String jobId) {
        jobLock.writeLock().lock();
        try {
            store(projectId,
                    Arrays.stream(getJobs(projectId, false)).filter(j -> !jobId.equals(keyToString(j.key))).toArray(n -> new JobV3[n]));
        } finally {
            jobLock.writeLock().unlock();
        }

        final JobKeyV3 jobKey = new JobKeyV3(jobId);
        h2oHelper.getJobs(jobKey).execute(getJobResponse -> {
            if (logger.isDebugEnabled()) {
                logger.debug("getJobs: {}", getJobResponse);
            }
            if (getJobResponse.code() == 200) {
                final JobV3 job = getJobResponse.body().findJob(jobId);
                if (job != null && JobV3.RUNNING.equals(job.status)) {
                    final Response<JobsV3> cancelJobResponse = h2oHelper.cancelJob(jobKey).execute();
                    if (logger.isDebugEnabled()) {
                        logger.debug("cancelJob: {}", cancelJobResponse);
                    }
                }
            } else {
                logger.warn("Failed to get job: {}", getJobResponse);
            }
        }, t -> logger.warn("Failed to get job: {}", jobId, t));

        responseCache.invalidate(getLeaderboardsCacheKey(projectId));
    }

    public synchronized void deleteAllJobs(final String projectId) {
        jobLock.writeLock().lock();
        try {
            final JobV3[] jobs =
                    Arrays.stream(getJobs(projectId, false)).filter(j -> j.getKind() == Kind.AUTO_ML && !JobV3.RUNNING.equals(j.status))
                            .toArray(n -> new JobV3[n]);
            if (jobs.length > 0) {
                new Thread(() -> stream(jobs).of(
                        stream -> stream.forEach(job -> {
                            final String leaderboardId = keyToString(job.dest);
                            if (StringUtil.isNotBlank(leaderboardId)) {
                                final LeaderboardV99 leaderboard = getLeaderboard(projectId, leaderboardId);
                                if (leaderboard != null) {
                                    stream(leaderboard.models).of(
                                            st -> st.map(H2oApi::keyToString).filter(StringUtil::isNotBlank).forEach(modelId -> {
                                                try {
                                                    deleteModel(projectId, modelId);
                                                } catch (final Exception e) {
                                                    logger.warn("Failed to delete {} in {}", modelId, projectId, e);
                                                }
                                            }));
                                }
                            }
                        })), "DeleteModels").start();
            }
            store(projectId, Arrays.stream(getJobs(projectId, false)).filter(j -> JobV3.RUNNING.equals(j.status))
                    .toArray(n -> new JobV3[n]));
        } finally {
            jobLock.writeLock().unlock();
        }

        responseCache.invalidate(getLeaderboardsCacheKey(projectId));
    }

    protected void store(final String projectId, final JobV3[] jobs) {
        final FessConfig fessConfig = ComponentUtil.getFessConfig();
        final MinioClient minioClient = createClient(fessConfig);
        final String json = gson.toJson(jobs);
        if (logger.isDebugEnabled()) {
            logger.debug("jobs: {}", json);
        }
        final String objectName = getJobsConfigPath(projectId);
        try (ByteArrayInputStream bais = new ByteArrayInputStream(json.getBytes(Constants.UTF_8_CHARSET))) {
            minioClient.putObject(fessConfig.getStorageBucket(), objectName, bais, new PutObjectOptions(-1,
                    PutObjectOptions.MIN_MULTIPART_SIZE));
        } catch (final Exception e) {
            throw new StorageException("Failed to create " + objectName, e);
        }
    }

    public LeaderboardV99 getLeaderboard(final String projectId, final String leaderboardId) {
        try {
            final String cacheKey = getLeaderboardCacheKey(projectId, leaderboardId);
            return (LeaderboardV99) responseCache.get(cacheKey, () -> {
                final Response<LeaderboardV99> response = h2oHelper.getLeaderboard(leaderboardId).execute();
                if (logger.isDebugEnabled()) {
                    logger.debug("getLeaderboard: {}", response);
                }
                if (response.code() == 200) {
                    return response.body();
                } else if (response.code() == 404) {
                    final LeaderboardV99 localLeaderboard = getLocalLeaderboard(projectId, leaderboardId);
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

    public void predict(final String projectId, final String frameId, final String modelId, final String name) {
        predict(projectId, frameId, modelId, name, d -> {});
    }

    public void predict(final String projectId, final String frameId, final String modelId, final String name,
            final Consumer<DataSet> consumer) {
        final JobV3 workingJob = createWorkingJob(name, "Export Prediction", 0.25f);
        store(projectId, workingJob);
        h2oHelper.predict(modelId, frameId).execute(
                predictResponse -> {
                    if (logger.isDebugEnabled()) {
                        logger.debug("predict: {}", predictResponse);
                    }
                    if (predictResponse.code() == 200) {
                        workingJob.progress = 0.5f;
                        store(projectId, workingJob);
                        final ModelMetricsListSchemaV3 modelMetricsListSchema = predictResponse.body();
                        final String predictionsFrameId = keyToString(modelMetricsListSchema.predictionsFrame);
                        final String destinationFrameId = "combind-" + predictionsFrameId;
                        h2oHelper.bindFrames(destinationFrameId, new String[] { predictionsFrameId, frameId }).execute(
                                bindFramesResponse -> {
                                    if (logger.isDebugEnabled()) {
                                        logger.debug("bindFrames: {}", bindFramesResponse);
                                    }
                                    if (bindFramesResponse.code() == 200) {
                                        workingJob.progress = 0.75f;
                                        store(projectId, workingJob);
                                        h2oHelper.exportFrame(new FrameKeyV3(destinationFrameId), getPredictCsvPath(projectId, name), true)
                                                .execute(
                                                        exportFrameResponse -> {
                                                            if (logger.isDebugEnabled()) {
                                                                logger.debug("exportFrame: {}", exportFrameResponse);
                                                            }
                                                            if (exportFrameResponse.code() == 200) {
                                                                final DataSet dataSet =
                                                                        createDataSet(projectId,
                                                                                StringCodecUtil.encodeUrlSafe(name + ".csv"));
                                                                dataSet.setType(DataSet.PREDICT);
                                                                store(projectId, dataSet);
                                                                consumer.accept(dataSet);
                                                                finish(projectId, workingJob, null);
                                                            } else {
                                                                logger.warn("Failed to export frame: {}", exportFrameResponse);
                                                                finish(projectId, workingJob, new H2oAccessException("Failed to access "
                                                                        + exportFrameResponse));
                                                            }
                                                            deleteFrameQuietly(destinationFrameId);
                                                            deleteFrameQuietly(predictionsFrameId);
                                                        }, t -> {
                                                            logger.warn("Failed to export frame: {}", name, t);
                                                            finish(projectId, workingJob, t);
                                                            deleteFrameQuietly(destinationFrameId);
                                                            deleteFrameQuietly(predictionsFrameId);
                                                        });
                                    } else {
                                        logger.warn("Failed to export frame: {}", bindFramesResponse);
                                        finish(projectId, workingJob, new H2oAccessException("Failed to access " + bindFramesResponse));
                                        deleteFrameQuietly(predictionsFrameId);
                                    }
                                }, t -> {
                                    logger.warn("Failed to export frame: {}", name, t);
                                    finish(projectId, workingJob, t);
                                    deleteFrameQuietly(predictionsFrameId);
                                });
                    } else {
                        logger.warn("Failed to export frame: {}", predictResponse);
                        finish(projectId, workingJob, new H2oAccessException("Failed to access " + predictResponse));
                    }
                }, t -> {
                    logger.warn("Failed to export frame: {}", name, t);
                    finish(projectId, workingJob, t);
                });
    }

    public void writeDataSet(final String projectId, final DataSet dataSet, final WrittenStreamOut out) {
        final FessConfig fessConfig = ComponentUtil.getFessConfig();
        final MinioClient minioClient = createClient(fessConfig);
        final String objectName = getDataPath(projectId, dataSet.getName());
        try (InputStream in = minioClient.getObject(fessConfig.getStorageBucket(), objectName)) {
            out.write(in);
        } catch (final Exception e) {
            throw new StorageException("Failed to write " + objectName, e);
        }
    }

    public void exportFrame(final String projectId, final String frameId, final String name) {
        final String filename = name.toLowerCase().endsWith(".csv") ? name : name + ".csv";
        final JobV3 workingJob = createWorkingJob(filename, "Export Frame", 0.25f);
        store(projectId, workingJob);
        h2oHelper.exportFrame(new FrameKeyV3(frameId), getPredictCsvPath(projectId, filename), true).execute(exportFrameResponse -> {
            if (logger.isDebugEnabled()) {
                logger.debug("exportFrame: {}", exportFrameResponse);
            }
            if (exportFrameResponse.code() == 200) {
                final DataSet dataSet = createDataSet(projectId, StringCodecUtil.encodeUrlSafe(filename));
                dataSet.setType(DataSet.PREDICT);
                store(projectId, dataSet);
                finish(projectId, workingJob, null);
            } else {
                logger.warn("Failed to export frame: {}", exportFrameResponse);
                finish(projectId, workingJob, new H2oAccessException("Failed to access " + exportFrameResponse));
            }
        }, t -> {
            logger.warn("Failed to export frame: {}", name, t);
            finish(projectId, workingJob, t);
        });
    }

    public void renewSession(final String projectId) {
        final Project project = getProject(projectId);
        responseCache.invalidateAll();
        deleteAllJobs(projectId);
        Arrays.stream(getFrames(project, (x, y) -> x.endsWith(y + ".hex"))).forEach(frameId -> {
            try {
                final Response<FramesV3> deleteFrameResponse = h2oHelper.deleteFrame(frameId).execute();
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
        h2oHelper.closeSession();
    }

    public void deleteProject(final String projectId) {
        h2oHelper.closeSession();

        final FessConfig fessConfig = ComponentUtil.getFessConfig();
        final MinioClient minioClient = createClient(fessConfig);
        final String path = projectFolderName + "/" + projectId + "/";
        for (final Result<Item> result : minioClient.listObjects(fessConfig.getStorageBucket(), path, true)) {
            try {
                final Item item = result.get();
                final String objectName = item.objectName();
                if (logger.isDebugEnabled()) {
                    logger.debug("objectName: {}", objectName);
                }
                minioClient.removeObject(fessConfig.getStorageBucket(), objectName);
            } catch (final Exception e) {
                logger.warn("Failed to remove an object from {}.", path, e);
            }
        }
    }

    public void changeColumnType(final String projectId, final String frameId, final int index, final String columnType, final long from,
            final long to) {
        final String type = convertColumnType(columnType);
        if (type == null) {
            if (logger.isDebugEnabled()) {
                logger.debug("Unknown column type: {}/{}/{}/{}", projectId, frameId, index, columnType);
            }
            return;
        }
        final Response<RapidsSchemaV3> response = h2oHelper.changeColumnType(new FrameKeyV3(frameId), type, index, from, to).execute();
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

    public FrameV3 getFrameData(final FramesV3 params) {
        final Response<FramesV3> response = h2oHelper.getFrameData(params).execute();
        if (logger.isDebugEnabled()) {
            logger.debug("getFrameData: {}", response);
        }
        if (response.code() == 200) {
            final FramesV3 frames = response.body();
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

    public ColV3 getFrameColumnData(final FramesV3 params) {
        try {
            final String cacheKey = params.toString();
            final ColV3 colData =
                    (ColV3) responseCache.get(cacheKey, () -> {
                        final Response<FramesV3> response = h2oHelper.getFrameColumnData(params).execute();
                        if (logger.isDebugEnabled()) {
                            logger.debug("getFrameColumnData: {}", response);
                        }
                        if (response.code() == 200) {
                            final FramesV3 frames = response.body();
                            if (frames.frames != null && frames.frames.length > 0 && frames.frames[0] != null
                                    && frames.frames[0].columns.length > 0) {
                                final FrameV3 frame = frames.frames[0];
                                final ColV3 col = frame.columns[0];
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

    public ModelSchemaBaseV3 getModel(final String projectId, final String leaderboardId, final String modelId) {
        if (StringUtil.isBlank(modelId)) {
            return null;
        }
        try {
            final String cacheKey = getModelCacheKey(projectId, modelId);
            return (ModelSchemaBaseV3) responseCache.get(cacheKey, () -> {
                final Response<ModelsV3> response = h2oHelper.getModel(new ModelKeyV3(modelId)).execute();
                if (logger.isDebugEnabled()) {
                    logger.debug("getModel: {}", response);
                }
                if (response.code() == 200) {
                    final ModelsV3 models = response.body();
                    for (final ModelSchemaBaseV3 model : models.models) {
                        if (modelId.equals(model.modelId.name)) {
                            return model;
                        }
                    }
                } else if (response.code() == 404) {
                    final ModelSchemaBaseV3 model = getLocalModel(projectId, leaderboardId, modelId);
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

    public void writeMojo(final String projectId, final String modelId, final WrittenStreamOut out) {
        h2oHelper.writeMojo(modelId, in -> {
            try {
                out.write(in);
            } catch (final IOException e) {
                throw new IORuntimeException(e);
            }
        }, e -> logger.warn("Failed to write {} in {}", modelId, projectId, e));
    }

    public void writeGenModel(final String projectId, final String modelId, final WrittenStreamOut out) {
        h2oHelper.writeGenModel(modelId, in -> {
            try {
                out.write(in);
            } catch (final IOException e) {
                throw new IORuntimeException(e);
            }
        }, e -> logger.warn("Failed to write {} in {}", modelId, projectId, e));
    }

    public void writeServing(final String projectId, final String modelId, final WrittenStreamOut out) {
        h2oHelper.writeMojo(modelId, in -> {
            try (ZipOutputStream zos = new ZipOutputStream(new BufferedOutputStream(out.stream()))) {
                // Dockerfile
                zos.putNextEntry(new ZipEntry("serving/Dockerfile"));
                final Path dockerfilePath = ResourceUtil.getEnvPath("fione", "resources", "Dockerfile.serving");
                try (InputStream fis = Files.newInputStream(dockerfilePath)) {
                    CopyUtil.copy(fis, zos);
                }
                // fione-serving.jar
                zos.putNextEntry(new ZipEntry("serving/fione-serving.jar"));
                final Path libPath = ResourceUtil.getEnvPath("fione", "lib");
                final Path[] jarPaths = Files.list(libPath).filter(f -> {
                    final String fileName = f.getFileName().toString();
                    return fileName.startsWith("fione-serving-") && fileName.endsWith("jar");
                }).toArray(n -> new Path[n]);
                if (jarPaths.length == 0) {
                    throw new FioneSystemException("fione-serving.jar is not found.");
                }
                try (InputStream fis = Files.newInputStream(jarPaths[0])) {
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

    public void deleteModel(final String projectId, final String modelId) {
        final Response<ModelsV3> response = h2oHelper.deleteModel(new ModelKeyV3(modelId)).execute();
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

    public void importModel(final String projectId, final String leaderboardId, final String modelId) {
        final JobV3 workingJob = createWorkingJob(modelId, "Import Model", 0.5f);
        store(projectId, workingJob);
        h2oHelper.importModel(modelId, getS3ModelPath(projectId, leaderboardId, modelId)).execute(importModelResponse -> {
            if (logger.isDebugEnabled()) {
                logger.debug("importModel: {}", importModelResponse);
            }
            if (importModelResponse.code() == 200) {
                finish(projectId, workingJob, null);
            } else {
                logger.warn("Failed to import frame: {}", importModelResponse);
                finish(projectId, workingJob, new H2oAccessException("Failed to access " + importModelResponse));
            }
            responseCache.invalidate(getModelCacheKey(projectId, modelId));
        }, t -> {
            logger.warn("Failed to import model: {}", modelId, t);
            finish(projectId, workingJob, t);
        });
    }

    public void exportModel(final String projectId, final String leaderboardId, final String modelId) {
        final ModelSchemaBaseV3 model = getModel(projectId, leaderboardId, modelId);
        if (model == null) {
            throw new H2oAccessException(modelId + " is not found in " + projectId);
        }

        final String json = modelHelper.serialize(model);
        if (logger.isDebugEnabled()) {
            logger.debug("model: {}", json);
        }

        final JobV3 workingJob = createWorkingJob(modelId, "Export Model", 0.2f);
        store(projectId, workingJob);
        try {
            store(projectId, leaderboardId, model);
            finish(projectId, workingJob, null);
        } catch (Exception e) {
            logger.warn("Failed to export frame: {}/{}/{}", projectId, leaderboardId, modelId, e);
            finish(projectId, workingJob, new H2oAccessException("Failed to access " + modelId));
        }
    }

    public void exportAllModels(final String projectId, final String leaderboardId) {
        final LeaderboardV99 leaderboard = getLeaderboard(projectId, leaderboardId);
        if (leaderboard == null) {
            throw new H2oAccessException(leaderboardId + " is not found in " + projectId);
        }

        new Thread(() -> {
            final AtomicInteger counter = new AtomicInteger(0);
            final JobV3 workingJob = createWorkingJob(leaderboardId, "Export All Models", 0.0f);
            store(projectId, workingJob);

            store(projectId, leaderboard);

            workingJob.progress = 0.1f;
            store(projectId, workingJob);

            final int size = leaderboard.models.length;
            Arrays.stream(leaderboard.models).map(m -> m.name).forEach(modelId -> {
                final ModelSchemaBaseV3 model = getModel(projectId, leaderboardId, modelId);
                if (model == null) {
                    logger.warn("{} is not found in {}", modelId, projectId);
                    return;
                }

                try {
                    store(projectId, leaderboardId, model);
                } catch (Exception e) {
                    logger.warn("Failed to store model: {} : {} : {}", projectId, leaderboardId, model, e);
                }

                final int current = counter.addAndGet(1);
                workingJob.progress = (float) current / (float) size * 0.9f + 0.1f;
                store(projectId, workingJob);
            });

            workingJob.progress = 1.0f;
            if (counter.get() == size) {
                finish(projectId, workingJob, null);
            } else {
                finish(projectId, workingJob, new H2oAccessException("Failed to export " + (size - counter.get()) + " models."));
            }
        }, "ExportAllModels").start();
    }

    protected void store(final String projectId, final LeaderboardV99 leaderboard) {
        final FessConfig fessConfig = ComponentUtil.getFessConfig();
        final MinioClient minioClient = createClient(fessConfig);
        final String json = gson.toJson(leaderboard);
        if (logger.isDebugEnabled()) {
            logger.debug("model: {}", json);
        }
        final String objectName = getLeaderboardConfigPath(projectId, leaderboard.projectName);
        try (ByteArrayInputStream bais = new ByteArrayInputStream(json.getBytes(Constants.UTF_8_CHARSET))) {
            final String bucketName = fessConfig.getStorageBucket();
            minioClient.putObject(bucketName, objectName, bais, new PutObjectOptions(-1, PutObjectOptions.MIN_MULTIPART_SIZE));
        } catch (final Exception e) {
            throw new StorageException("Failed to create " + objectName, e);
        }
    }

    protected void store(final String projectId, final String leaderboardId, final ModelSchemaBaseV3 model) {
        final FessConfig fessConfig = ComponentUtil.getFessConfig();
        final MinioClient minioClient = createClient(fessConfig);
        final String json = modelHelper.serialize(model);
        if (logger.isDebugEnabled()) {
            logger.debug("model: {}", json);
        }
        final String modelId = keyToString(model.modelId);
        final String objectName = getModelConfigPath(projectId, leaderboardId, modelId);
        try (ByteArrayInputStream bais = new ByteArrayInputStream(json.getBytes(Constants.UTF_8_CHARSET))) {
            final String bucketName = fessConfig.getStorageBucket();
            minioClient.putObject(bucketName, objectName, bais, new PutObjectOptions(-1, PutObjectOptions.MIN_MULTIPART_SIZE));
        } catch (final Exception e) {
            throw new StorageException("Failed to create " + objectName, e);
        }

        try {
            final Response<ModelExportV3> exportModelResponse =
                    h2oHelper.exportModel(modelId, getS3ModelPath(projectId, leaderboardId, modelId)).execute();
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
            final ModelOutputSchemaV3 output = ((ModelSchemaV3) model).output;
            if (output != null && output.crossValidationModels != null) {
                for (final ModelKeyV3 key : output.crossValidationModels) {
                    try {
                        ModelSchemaBaseV3 subModel = getLocalModel(projectId, leaderboardId, keyToString(key));
                        if (subModel == null) {
                            subModel = getModel(projectId, leaderboardId, keyToString(key));
                            store(projectId, leaderboardId, subModel);
                        }
                    } catch (Exception e) {
                        logger.warn("Failed to store sub-model: {}", key, e);
                    }
                }
            }
        }
    }

    protected InputStream openStorageObject(final MinioClient minioClient, final String bucketName, final String objectName) {
        for (int i = 0; i < 60; i++) {
            try {
                return minioClient.getObject(bucketName, objectName);
            } catch (final ErrorResponseException e) {
                if (e.errorResponse().errorCode() != ErrorCode.NO_SUCH_OBJECT) {
                    throw new StorageException("Failed to access " + objectName, e);
                }
            } catch (final Exception e) {
                throw new StorageException("Failed to access " + objectName, e);
            }
            ThreadUtil.sleepQuietly(1000L);
        }
        throw new StorageException(objectName + " does not exist");
    }

    public void filterColumns(final String projectId, final DataSet dataSet, final Map<String, String> columnMap) {
        final FessConfig fessConfig = ComponentUtil.getFessConfig();
        final MinioClient minioClient = createClient(fessConfig);
        final String objectName = getDataPath(projectId, dataSet.getName());
        final String tempObjectName = objectName + ".tmp";
        final CsvConfig csvConfig = new CsvConfig(',', '"', '"');
        csvConfig.setIgnoreEmptyLines(true);
        try (final CsvReader csvReader =
                new CsvReader(new InputStreamReader(openStorageObject(minioClient, fessConfig.getStorageBucket(), objectName),
                        Constants.UTF_8_CHARSET), csvConfig)) {
            final Map<String, Integer> indexMap = new HashMap<>();
            final List<String> headerList = csvReader.readValues();
            for (int i = 0; i < headerList.size(); i++) {
                final String name = headerList.get(i);
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

            try (final PipedOutputStream pipedOut = new PipedOutputStream(); final PipedInputStream pipedIn = new PipedInputStream()) {
                final Thread pipeWriter =
                        new Thread(() -> {
                            try {
                                minioClient.putObject(fessConfig.getStorageBucket(), tempObjectName, pipedIn, new PutObjectOptions(-1,
                                        PutObjectOptions.MIN_MULTIPART_SIZE));
                            } catch (final Exception e) {
                                logger.warn("Failed to write {}.", tempObjectName, e);
                            }
                        }, "Filtercolumns");

                pipedIn.connect(pipedOut);
                pipeWriter.start();

                try (final CsvWriter csvWriter = new CsvWriter(new OutputStreamWriter(pipedOut), csvConfig)) {
                    final List<String> indices = columnMap.values().stream().collect(Collectors.toList());
                    csvWriter.writeValues(indices);
                    List<String> list;
                    while ((list = csvReader.readValues()) != null) {
                        final List<String> l = list;
                        final List<String> valueList = indices.stream().map(s -> {
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
            minioClient.copyObject(fessConfig.getStorageBucket(), objectName, null, null, fessConfig.getStorageBucket(), tempObjectName,
                    null, null);
            if (logger.isDebugEnabled()) {
                logger.debug("removing {}.", tempObjectName);
            }
            minioClient.removeObject(fessConfig.getStorageBucket(), tempObjectName);
        } catch (final Exception e) {
            throw new StorageException("Failed to update " + objectName, e);
        }
    }

    protected JobV3 createWorkingJob(final String target, final String description, final float progress) {
        final JobV3 job = new JobV3();
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

    protected void finish(final String projectId, final JobV3 job, final Throwable t) {
        job.progress = 1.0f;
        job.msec = System.currentTimeMillis() - job.startTime;
        if (t == null) {
            job.status = JobV3.DONE;
        } else {
            job.status = JobV3.FAILED;
            job.exception = t.getMessage();
            try (StringWriter writer = new StringWriter()) {
                t.printStackTrace(new PrintWriter(writer, true));
                writer.flush();
                job.stacktrace = writer.toString();
            } catch (final IOException e) {
                // ignore
            }
        }
        store(projectId, job);
    }

    public void executeModule(final String projectId, final PythonModule pythonModule, final Map<String, Object> params) {
        final JobV3 workingJob = createWorkingJob(pythonModule.getId(), pythonModule.getName(), 0.1f);
        store(projectId, workingJob);
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
                    finish(projectId, workingJob, null);
                } catch (final Exception e) {
                    logger.warn("Failed to execute module: projectId:{}, params:{}", projectId, params, e);
                    finish(projectId, workingJob, e);
                } finally {
                    queue.add("END:{}");
                }
            }, "ExecuteModule").start();
            new Thread(() -> {
                final ObjectMapper objectMapper = new ObjectMapper();
                while (true) {
                    final String progress;
                    try {
                        progress = queue.take();
                    } catch (InterruptedException e) {
                        logger.debug("Interrupted.", e);
                        break;
                    }
                    if (logger.isDebugEnabled()) {
                        logger.debug("Module Response: {}", progress);
                    }
                    if (progress.startsWith("END:")) {
                        break;
                    }
                    final String[] values = StringUtils.split(progress, ":", 2);
                    if (values.length != 2) {
                        continue;
                    }
                    try {
                        final Map<String, Object> response = objectMapper.readValue(values[1], new TypeReference<Map<String, Object>>() {
                        });
                        processModuleResponse(projectId, workingJob, response);
                    } catch (Exception e) {
                        logger.warn("Failed to process {}", values[1], e);
                    }
                }
            }, "ExecuteModuleReceiver").start();
        } catch (final Exception e) {
            logger.warn("Failed to execute module: projectId:{}, params:{}", projectId, params, e);
            finish(projectId, workingJob, e);
        }
    }

    protected void processModuleResponse(String projectId, JobV3 workingJob, Map<String, Object> params) {
        if (logger.isDebugEnabled()) {
            logger.debug("response params: {}", params);
        }
        String responseType = (String) params.get("type");
        switch (responseType) {
        case "progress":
            processProgressModuleResponse(projectId, workingJob, params);
            break;
        case "leaderboard":
            processLeaderboardModuleResponse(projectId, workingJob, params);
            break;
        case "model":
            processModelModuleResponse(projectId, workingJob, params);
            break;
        default:
            logger.warn("Unknown type: {} = {}", responseType, params);
            break;
        }
    }

    protected void processProgressModuleResponse(String projectId, JobV3 workingJob, Map<String, Object> params) {
        if (params.containsKey("message")) {
            workingJob.progressMsg = (String) params.get("message");
        }
        if (params.containsKey("progress")) {
            workingJob.progress = (float) Double.parseDouble((String) params.get("progress"));
            store(projectId, workingJob);
        }
    }

    protected void processLeaderboardModuleResponse(String projectId, JobV3 workingJob, Map<String, Object> params) {
        final String leaderboardId = (String) params.get("leaderboard_id");
        LeaderboardV99 leaderboard = getLocalLeaderboard(projectId, leaderboardId);
        if (leaderboard != null) {
            deleteLeaderboard(projectId, leaderboardId);
        }

        leaderboard = new LeaderboardV99();
        leaderboard.projectName = leaderboardId;
        store(projectId, leaderboard);
    }

    protected void processModelModuleResponse(String projectId, JobV3 workingJob, Map<String, Object> params) {
        final String leaderboardId = (String) params.get("leaderboard_id");
        LeaderboardV99 leaderboard = getLocalLeaderboard(projectId, leaderboardId);
        if (leaderboard == null) {
            leaderboard = new LeaderboardV99();
            leaderboard.projectName = leaderboardId;
        }

        final String modelId = (String) params.get("model_id");
        responseCache.invalidate(getModelCacheKey(projectId, modelId));
        final ModelSchemaBaseV3 model = getModel(projectId, leaderboardId, modelId);
        if (model == null) {
            throw new H2oAccessException("Model " + modelId + " is not found.");
        }

        final int size = leaderboard.models == null ? 0 : leaderboard.models.length;
        ModelKeyV3[] newModels = new ModelKeyV3[size + 1];
        int i = 0;
        while (i < size) {
            newModels[i] = leaderboard.models[i];
            i++;
        }
        newModels[i] = model.modelId;
        leaderboard.models = newModels;
        store(projectId, leaderboard);
        store(projectId, leaderboardId, model);
    }

    public void deleteLeaderboard(final String projectId, final String leaderboardId) {
        final FessConfig fessConfig = ComponentUtil.getFessConfig();
        final MinioClient minioClient = createClient(fessConfig);
        final String leaderboardDir = projectFolderName + "/" + projectId + "/model/" + StringCodecUtil.encodeUrlSafe(leaderboardId) + "/";
        final List<String> objectNameList = new ArrayList<>();
        try {
            for (final Result<Item> result : minioClient.listObjects(fessConfig.getStorageBucket(), leaderboardDir, true)) {
                final Item item = result.get();
                final String objectName = item.objectName();
                objectNameList.add(objectName);
            }
            objectNameList.add(getLeaderboardConfigPath(projectId, leaderboardId));
            final Iterable<Result<DeleteError>> results = minioClient.removeObjects(fessConfig.getStorageBucket(), objectNameList);
            for (final Result<DeleteError> result : results) {
                logger.warn("Failed to delete {}", result.get());
            }
        } catch (final Exception e) {
            throw new StorageException("Failed to delete " + leaderboardDir, e);
        }

        responseCache.invalidate(getLeaderboardsCacheKey(projectId));
        responseCache.invalidate(getLeaderboardCacheKey(projectId, leaderboardId));
    }

    public String[] getLeaderboardIds(final String projectId) {
        try {
            final String cacheKey = getLeaderboardsCacheKey(projectId);
            return (String[]) responseCache.get(cacheKey, () -> {
                final List<String> idList = new ArrayList<>();
                final Response<LeaderboardsV99> response = h2oHelper.getLeaderboards().execute();
                if (logger.isDebugEnabled()) {
                    logger.debug("getLeaderboards: {}", response);
                }
                if (response.code() == 200) {
                    final LeaderboardsV99 leaderboards = response.body();
                    final String prefix = StringCodecUtil.decode(projectId);
                    for (LeaderboardV99 leaderboard : leaderboards.leaderboards) {
                        final String projectName = leaderboard.projectName;
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
        final FessConfig fessConfig = ComponentUtil.getFessConfig();
        final String leaderboardDir = projectFolderName + "/" + projectId + "/model/";
        final List<String> list = new ArrayList<>();
        try {
            final MinioClient minioClient = createClient(fessConfig);
            for (final Result<Item> result : minioClient.listObjects(fessConfig.getStorageBucket(), leaderboardDir, false)) {
                final Item item = result.get();
                final String objectName = item.objectName();
                if (logger.isDebugEnabled()) {
                    logger.debug("objectName: {}", objectName);
                }
                if (!objectName.endsWith(".json")) {
                    if (logger.isDebugEnabled()) {
                        logger.debug("Skipped: {}", objectName);
                    }
                    continue;
                }
                final String[] values = objectName.split("/");
                list.add(StringCodecUtil.decode(values[values.length - 1].replaceFirst(".json$", StringUtil.EMPTY)));
            }
        } catch (final Exception e) {
            if (logger.isDebugEnabled()) {
                logger.debug("Failed to access " + fessConfig.getStorageEndpoint(), e);
            }
        }
        return list.toArray(n -> new String[n]);
    }

    protected LeaderboardV99 getLocalLeaderboard(final String projectId, final String leaderboardId) {
        final FessConfig fessConfig = ComponentUtil.getFessConfig();
        final MinioClient minioClient = createClient(fessConfig);
        final String objectName = getLeaderboardConfigPath(projectId, leaderboardId);
        try (Reader reader =
                new InputStreamReader(minioClient.getObject(fessConfig.getStorageBucket(), objectName), Constants.UTF_8_CHARSET)) {
            final LeaderboardV99 leaderboard = gson.fromJson(reader, LeaderboardV99.class);
            leaderboard.setInLocal(true);
            return leaderboard;
        } catch (final ErrorResponseException e) {
            final ErrorCode code = e.errorResponse().errorCode();
            if (code == ErrorCode.NO_SUCH_KEY || code == ErrorCode.NO_SUCH_OBJECT) {
                return null;
            }
            throw new StorageException("Failed to read " + objectName, e);
        } catch (final Exception e) {
            throw new StorageException("Failed to read " + objectName, e);
        }
    }

    protected ModelSchemaBaseV3 getLocalModel(final String projectId, final String leaderboardId, final String modelId) {
        final FessConfig fessConfig = ComponentUtil.getFessConfig();
        final MinioClient minioClient = createClient(fessConfig);
        final String objectName = getModelConfigPath(projectId, leaderboardId, modelId);
        try (Reader reader =
                new InputStreamReader(minioClient.getObject(fessConfig.getStorageBucket(), objectName), Constants.UTF_8_CHARSET)) {
            final ModelSchemaBaseV3 model = modelHelper.deserialize(reader);
            model.setInLocal(true);
            return model;
        } catch (final ErrorResponseException e) {
            final ErrorCode code = e.errorResponse().errorCode();
            if (code == ErrorCode.NO_SUCH_KEY || code == ErrorCode.NO_SUCH_OBJECT) {
                return null;
            }
            throw new StorageException("Failed to read " + objectName, e);
        } catch (final Exception e) {
            throw new StorageException("Failed to read " + objectName, e);
        }
    }

    protected String getPredictCsvPath(final String projectId, final String name) {
        final FessConfig fessConfig = ComponentUtil.getFessConfig();
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
        final FessConfig fessConfig = ComponentUtil.getFessConfig();
        return "s3://" + fessConfig.getStorageBucket() + "/" + projectFolderName + "/" + projectId + "/data/" + fileName;
    }

    protected String getLeaderboardConfigPath(final String projectId, final String leaderboardId) {
        return projectFolderName + "/" + projectId + "/model/" + StringCodecUtil.encodeUrlSafe(leaderboardId) + ".json";
    }

    protected String getModelConfigPath(final String projectId, final String leaderboardId, final String modelId) {
        return projectFolderName + "/" + projectId + "/model/" + StringCodecUtil.encodeUrlSafe(leaderboardId) + "/" + modelId + ".json";
    }

    protected String getS3ModelPath(final String projectId, final String leaderboardId, final String modelId) {
        final FessConfig fessConfig = ComponentUtil.getFessConfig();
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
