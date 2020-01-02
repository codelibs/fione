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

import java.io.ByteArrayInputStream;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.Reader;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

import javax.annotation.Resource;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.codelibs.fess.crawler.Constants;
import org.codelibs.fess.exception.StorageException;
import org.codelibs.fess.mylasta.direction.FessConfig;
import org.codelibs.fess.util.ComponentUtil;
import org.codelibs.fione.entity.DataSet;
import org.codelibs.fione.entity.Project;
import org.codelibs.fione.exception.H2oAccessException;
import org.codelibs.fione.h2o.bindings.H2oApi;
import org.codelibs.fione.h2o.bindings.pojos.AutoMLBuildControlV99;
import org.codelibs.fione.h2o.bindings.pojos.AutoMLBuildModelsV99;
import org.codelibs.fione.h2o.bindings.pojos.AutoMLInputV99;
import org.codelibs.fione.h2o.bindings.pojos.FrameBaseV3;
import org.codelibs.fione.h2o.bindings.pojos.FrameV3;
import org.codelibs.fione.h2o.bindings.pojos.FramesListV3;
import org.codelibs.fione.h2o.bindings.pojos.FramesV3;
import org.codelibs.fione.h2o.bindings.pojos.JobV3;
import org.codelibs.fione.h2o.bindings.pojos.JobsV3;
import org.codelibs.fione.h2o.bindings.pojos.ParseV3;
import org.codelibs.fione.util.StringCodecUtil;

import com.google.common.collect.Lists;
import com.google.gson.Gson;

import io.minio.MinioClient;
import io.minio.Result;
import io.minio.errors.ErrorResponseException;
import io.minio.messages.Item;
import retrofit2.Response;

public class ProjectHelper {
    private static final Logger logger = LogManager.getLogger(ProjectHelper.class);

    @Resource
    private H2oHelper h2oHelper;

    protected String projectFolderName = "fione";

    protected final Gson gson = H2oApi.createGson();

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
            minioClient.putObject(bucketName, objectName, bais, null, null, null, "application/json");
        } catch (final Exception e) {
            throw new StorageException("Failed to create " + objectName, e);
        }
    }

    public Project getProject(final String projectId) {
        final FessConfig fessConfig = ComponentUtil.getFessConfig();
        final MinioClient minioClient = createClient(fessConfig);
        final String objectName = getProjectConfigPath(projectId);
        try (Reader reader =
                new InputStreamReader(minioClient.getObject(fessConfig.getStorageBucket(), objectName), Constants.UTF_8_CHARSET)) {
            final Project project = gson.fromJson(reader, Project.class);
            project.setDataSets(getDataSets(fessConfig, minioClient, projectId));
            project.setFrameIds(getFrames(project));
            project.setJobs(getJobs(projectId));
            return project;
        } catch (final Exception e) {
            throw new StorageException("Failed to read " + objectName, e);
        }
    }

    protected String[] getFrames(final Project project) {
        final List<String> frameIdList = new ArrayList<>();
        for (final String baseName : Arrays.stream(project.getDataSets()).map(d -> d.getName().split("\\.")[0]).toArray(n -> new String[n])) {
            final Response<FramesListV3> response = h2oHelper.getFrames(baseName).execute();
            if (logger.isDebugEnabled()) {
                logger.debug("getFrames: {}", response);
            }
            if (response.code() == 200) {
                for (final FrameBaseV3 frame : response.body().frames) {
                    if (frame.frameId.name.startsWith(baseName)) {
                        frameIdList.add(frame.frameId.name);
                    }
                }
            } else {
                logger.warn("Failed to get frames: {}", response);
            }
        }
        return frameIdList.toArray(n -> new String[n]);
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

    public void addDataSet(final String projectId, final String fileName, final InputStream in) {
        final FessConfig fessConfig = ComponentUtil.getFessConfig();
        final MinioClient minioClient = createClient(fessConfig);
        final String objectName = getDataPath(projectId, fileName);
        try {
            minioClient.putObject(fessConfig.getStorageBucket(), objectName, in, null, null, null, "application/octet-stream");
        } catch (final Exception e) {
            throw new StorageException("Failed to store " + objectName, e);
        }

        final DataSet dataSet = createDataSet(projectId, StringCodecUtil.encodeUrlSafe(fileName));
        store(projectId, dataSet);

        loadDataSetSchema(projectId, dataSet);
    }

    protected DataSet createDataSet(final String projectId, final String dataSetId) {
        final DataSet dataSet = new DataSet(dataSetId);
        dataSet.setPath(getS3Path(projectId, dataSet.getName()));
        return dataSet;
    }

    public void deleteDataSet(final String projectId, final String dataSetId) {
        final FessConfig fessConfig = ComponentUtil.getFessConfig();

        final String name = StringCodecUtil.decode(dataSetId);
        h2oHelper.getFrames(name.split("\\.")[0]).execute(frameResponse -> {
            if (logger.isDebugEnabled()) {
                logger.debug("getFrames: {}", frameResponse);
            }
            if (frameResponse.code() == 200) {
                for (final FrameBaseV3 frame : frameResponse.body().frames) {
                    final Response<FramesV3> response = h2oHelper.deleteFrame(frame.frameId).execute();
                    if (logger.isDebugEnabled()) {
                        logger.debug("deleteFrame: {}", response);
                    }
                    if (frameResponse.code() == 200) {
                        logger.info("Delete frame: {}", frame.frameId);
                    } else {
                        logger.warn("Failed to delete {}", response);
                    }
                }
            } else {
                logger.warn("Failed to get frames: {}", frameResponse);
            }
        }, t -> logger.warn("Failed to get frames.", t));

        final MinioClient minioClient = createClient(fessConfig);
        final String dataPath = getDataPath(projectId, name);
        final String configPath = getDataSetConfigPath(projectId, dataSetId);
        try {
            minioClient.removeObjects(fessConfig.getStorageBucket(), Lists.newArrayList(dataPath, configPath));
        } catch (final Exception e) {
            throw new StorageException("Failed to delete data files.", e);
        }
    }

    public void loadDataSetSchema(final String projectId, final DataSet dataSet) {
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
                        dataSet.setSchema(meta);
                        store(projectId, dataSet);
                        h2oHelper.deleteFrame(frames[0]).execute(deleteResponse -> {
                            if (logger.isDebugEnabled()) {
                                logger.debug("deleteFrame: {}", deleteResponse);
                            }
                        }, t3 -> logger.warn("Failed to delete frame: {}", frames[0], t3));
                    } else {
                        logger.warn("Failed to parse data: projectId:{}, dataSet:{}", projectId, dataSet);
                    }
                }, t2 -> logger.warn("Failed to parse data: projectId:{}, dataSet:{}", projectId, dataSet, t2));
            } else {
                logger.warn("Failed to import data: projectId:{}, dataSet:{}", projectId, dataSet);
            }
        }, t1 -> logger.warn("Failed to import data: projectId:{}, dataSet:{}", projectId, dataSet, t1));
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
            minioClient.putObject(fessConfig.getStorageBucket(), objectName, bais, null, null, null, "application/json");
        } catch (final Exception e) {
            throw new StorageException("Failed to create " + objectName, e);
        }
    }

    public FrameV3 getColumnSummaries(final String frameId) {
        final Response<FramesV3> response = h2oHelper.getFrameSummary(frameId).execute();
        if (logger.isDebugEnabled()) {
            logger.debug("getFrameSummary: {}", response);
        }
        if (response.code() == 200) {
            final FramesV3 data = response.body();
            if (data.frames.length == 1) {
                return data.frames[0];
            }
        }
        return null;
    }

    public void createFrame(final String projectId, final DataSet dataSet) {
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
                        logger.info("Create frame: {}", parseResponse.body().destinationFrame.name);
                        insert(projectId, parseResponse.body().job);
                    } else {
                        logger.warn("Failed to parse data: dataSet:{}", dataSet);
                    }
                }, t2 -> logger.warn("Failed to parse data: dataSet:{}", dataSet, t2));
            } else {
                logger.warn("Failed to import data: dataSet:{}", dataSet);
            }
        }, t1 -> logger.warn("Failed to import data: dataSet:{}", dataSet, t1));

    }

    public void deleteFrame(final String frameId) {
        final Response<FramesV3> response = h2oHelper.deleteFrame(frameId).execute();
        if (logger.isDebugEnabled()) {
            logger.debug("deleteFrame: {}", response);
        }
        if (response.code() == 200) {
            logger.info("Deleted frame: {}", frameId);
        } else {
            throw new H2oAccessException("Failed to delete frame " + frameId + " : " + response);
        }
    }

    public void runAutoML(final String projectId, final AutoMLBuildControlV99 buildControl, final AutoMLInputV99 inputSpec,
            final AutoMLBuildModelsV99 buildModels) {
        h2oHelper.runAutoML(buildControl, inputSpec, buildModels).execute(autoMLResponse -> {
            if (logger.isDebugEnabled()) {
                logger.debug("runAutoML: {}", autoMLResponse);
            }
            if (autoMLResponse.code() == 200) {
                logger.info("AutoML process started: {}", autoMLResponse.body().job.dest.name);
                insert(projectId, autoMLResponse.body().job);
            } else {
                logger.warn("Failed to run AutoML: {}", autoMLResponse);
            }
        }, t -> logger.warn("Failed to run AutoML.", t));
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
                final List<JobV3> list = new ArrayList<>();
                for (final JobV3 job : jobs) {
                    if ("RUNNING".equals(job.status)) {
                        final Response<JobsV3> response = h2oHelper.getJobs(job.key.name).execute();
                        if (logger.isDebugEnabled()) {
                            logger.debug("getJobs: {}", response);
                        }
                        if (response.code() == 200) {
                            JobV3 target = null;
                            for (final JobV3 j : response.body().jobs) {
                                if (job.key.name.equals(j.key.name)) {
                                    target = j;
                                }
                            }
                            list.add(target != null ? target : job);
                        } else {
                            list.add(job);
                        }
                    } else {
                        list.add(job);
                    }
                }
                new Thread(() -> store(projectId, list.toArray(n -> new JobV3[n])), "UpdateJobs").start();
            }
            return jobs;
        } catch (final ErrorResponseException e) {
            final String code = e.errorResponse().code();
            if ("NoSuchKey".equals(code)) {
                return new JobV3[0];
            }
            throw new StorageException("Failed to read " + objectName, e);
        } catch (final Exception e) {
            throw new StorageException("Failed to read " + objectName, e);
        }

    }

    public void insert(final String projectId, final JobV3 job) {
        if (logger.isDebugEnabled()) {
            logger.debug("Insert job:{}", job);
        }
        final JobV3[] oldJobs = getJobs(projectId, false);
        final JobV3[] jobs = Arrays.copyOf(oldJobs, oldJobs.length + 1);
        jobs[jobs.length - 1] = job;
        store(projectId, jobs);
    }

    public void deleteJob(final String projectId, final String jobId) {
        store(projectId, Arrays.stream(getJobs(projectId, false)).filter(j -> !jobId.equals(j.key.name)).toArray(n -> new JobV3[n]));
    }

    protected synchronized void store(final String projectId, final JobV3[] jobs) {
        final FessConfig fessConfig = ComponentUtil.getFessConfig();
        final MinioClient minioClient = createClient(fessConfig);
        final String json = gson.toJson(jobs);
        if (logger.isDebugEnabled()) {
            logger.debug("jobs: {}", json);
        }
        final String objectName = getJobsConfigPath(projectId);
        try (ByteArrayInputStream bais = new ByteArrayInputStream(json.getBytes(Constants.UTF_8_CHARSET))) {
            minioClient.putObject(fessConfig.getStorageBucket(), objectName, bais, null, null, null, "application/json");
        } catch (final Exception e) {
            throw new StorageException("Failed to create " + objectName, e);
        }
    }

    private String getDataPath(final String projectId, final String fileName) {
        return projectFolderName + "/" + projectId + "/data/" + fileName;
    }

    private String getProjectConfigPath(final String projectId) {
        return projectFolderName + "/" + projectId + "/project.json";
    }

    private String getJobsConfigPath(final String projectId) {
        return projectFolderName + "/" + projectId + "/jobs.json";
    }

    private String getDataSetConfigPath(final String projectId, final String dataSetId) {
        return projectFolderName + "/" + projectId + "/config/" + dataSetId + "_dataset.json";
    }

    private String getS3Path(final String projectId, final String fileName) {
        final FessConfig fessConfig = ComponentUtil.getFessConfig();
        return "s3://" + fessConfig.getStorageBucket() + "/" + projectFolderName + "/" + projectId + "/data/" + fileName;
    }

}
