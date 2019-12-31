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
import java.util.List;

import javax.annotation.Resource;

import org.apache.commons.codec.binary.Base64;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.codelibs.fess.crawler.Constants;
import org.codelibs.fess.exception.StorageException;
import org.codelibs.fess.mylasta.direction.FessConfig;
import org.codelibs.fess.util.ComponentUtil;
import org.codelibs.fione.entity.DataSet;
import org.codelibs.fione.entity.DataSet.Status;
import org.codelibs.fione.entity.Project;
import org.codelibs.fione.h2o.bindings.H2oApi;
import org.codelibs.fione.h2o.bindings.pojos.AutoMLBuildControlV99;
import org.codelibs.fione.h2o.bindings.pojos.AutoMLBuildModelsV99;
import org.codelibs.fione.h2o.bindings.pojos.AutoMLInputV99;
import org.codelibs.fione.h2o.bindings.pojos.FrameBaseV3;
import org.codelibs.fione.h2o.bindings.pojos.FrameV3;
import org.codelibs.fione.h2o.bindings.pojos.FramesListV3;
import org.codelibs.fione.h2o.bindings.pojos.FramesV3;
import org.codelibs.fione.h2o.bindings.pojos.ParseV3;

import com.google.gson.Gson;

import io.minio.MinioClient;
import io.minio.Result;
import io.minio.messages.Item;
import retrofit2.Response;

public class ProjectHelper {
    private static final Logger logger = LogManager.getLogger(ProjectHelper.class);

    @Resource
    private H2oHelper h2oHelper;

    protected String projectFolderName = "fione";

    protected final String projectJsonName = "project.json";

    protected final Gson gson = H2oApi.createGson();

    public Project[] getProjects() {
        final FessConfig fessConfig = ComponentUtil.getFessConfig();
        final List<Project> list = new ArrayList<>();
        try {
            final MinioClient minioClient = createClient(fessConfig);
            for (final Result<Item> result : minioClient.listObjects(fessConfig.getStorageBucket(), projectFolderName + "/", false)) {
                final Item item = result.get();
                final String objectName = item.objectName();
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
            project.setDataSets(parseDataSets(fessConfig, minioClient, projectId));
            return project;
        } catch (final Exception e) {
            throw new StorageException("Failed to read " + objectName, e);
        }
    }

    protected DataSet[] parseDataSets(final FessConfig fessConfig, final MinioClient minioClient, final String id) {
        final String prefix = projectFolderName + "/" + id + "/data/";
        final List<DataSet> list = new ArrayList<>();
        for (final Result<Item> result : minioClient.listObjects(fessConfig.getStorageBucket(), prefix, false)) {
            try {
                final Item item = result.get();
                final String objectName = item.objectName();
                final String[] values = objectName.split("/");
                if (values.length == 4) {
                    final String dataSetId = Base64.encodeBase64URLSafeString(values[3].getBytes(Constants.UTF_8_CHARSET));
                    final DataSet dataSet = createDataSet(fessConfig, minioClient, id, dataSetId);
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
        return createDataSet(fessConfig, minioClient, projectId, dataSetId);
    }

    private DataSet createDataSet(final FessConfig fessConfig, final MinioClient minioClient, final String projectId, final String dataSetId) {
        final String objectName = getDataSetConfigPath(projectId, dataSetId);
        try (Reader reader =
                new InputStreamReader(minioClient.getObject(fessConfig.getStorageBucket(), objectName), Constants.UTF_8_CHARSET)) {
            final DataSet dataSet = gson.fromJson(reader, DataSet.class);
            if (dataSet.getMeta() != null) {
                final Response<FramesListV3> response = h2oHelper.getFrames(dataSet.getMeta().sourceFrames[0]).execute();
                if (logger.isDebugEnabled()) {
                    logger.debug("getFrames: {}", response);
                }
                if (response.code() == 200) {
                    final FrameBaseV3[] frames = response.body().frames;
                    if (frames.length == 1) {
                        dataSet.setStatus(frames[0].isText ? Status.LOADED : Status.PARSED);
                    }
                }
            }
            return dataSet;
        } catch (final Exception e) {
            if (logger.isDebugEnabled()) {
                logger.debug("Failed to read " + objectName, e);
            }
            return new DataSet(dataSetId);
        }
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

        final DataSet dataSet = new DataSet();
        final String dataSetId = Base64.encodeBase64URLSafeString(fileName.getBytes(Constants.UTF_8_CHARSET));
        dataSet.setId(dataSetId);
        dataSet.setName(fileName);
        dataSet.setPath(getS3Path(projectId, fileName));
        store(projectId, dataSet);

        importFile(projectId, dataSet.getId());
    }

    protected void setupParse(final String projectId, final DataSet dataSet, final String[] sourceFrames) {
        h2oHelper.setupParse(sourceFrames).execute((call, res) -> {
            if (logger.isDebugEnabled()) {
                logger.debug("setupParse: {}", res);
            }
            if (res.code() == 200) {
                final ParseV3 meta = h2oHelper.convert(res.body());
                dataSet.setMeta(meta);
                store(projectId, dataSet);
            } else {
                logger.warn("Failed to parse data: projectId:{}, dataSet:{}", projectId, dataSet);
            }
        }, (call, t) -> {
            logger.warn("Failed to parse data: projectId:{}, dataSet:{}", projectId, dataSet, t);
        });
    }

    public void importFile(final String projectId, final String dataSetId) {
        final FessConfig fessConfig = ComponentUtil.getFessConfig();
        final MinioClient minioClient = createClient(fessConfig);
        final DataSet dataSet = createDataSet(fessConfig, minioClient, projectId, dataSetId);
        if (dataSet.getStatus() == Status.UNLOAD || dataSet.getMeta() == null) {
            h2oHelper.importFiles(dataSet.getPath()).execute((call, res) -> {
                if (logger.isDebugEnabled()) {
                    logger.debug("importFiles: {}", res);
                }
                if (res.code() == 200) {
                    if (dataSet.getMeta() == null) {
                        setupParse(projectId, dataSet, res.body().destinationFrames);
                    }
                } else {
                    logger.warn("Failed to import data: projectId:{}, dataSet:{}", projectId, dataSet);
                }
            }, (call, t) -> {
                logger.warn("Failed to import data: projectId:{}, dataSet:{}", projectId, dataSet, t);
            });
        }
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

    public FrameV3 getColumnSummaries(final DataSet dataSet) {
        final Response<FramesV3> response = h2oHelper.getFrameSummary(dataSet.getMeta().destinationFrame.name).execute();
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

    public void parseData(final String projectId, final String dataSetId) {
        final FessConfig fessConfig = ComponentUtil.getFessConfig();
        final MinioClient minioClient = createClient(fessConfig);
        final DataSet dataSet = createDataSet(fessConfig, minioClient, projectId, dataSetId);
        if (dataSet.getStatus() == Status.LOADED) {
            h2oHelper.parseFiles(dataSet.getMeta()).execute((call, res) -> {
                if (logger.isDebugEnabled()) {
                    logger.debug("importFiles: {}", res);
                }
                if (res.code() == 200) {
                    // TODO job
                } else {
                    logger.warn("Failed to parse data: projectId:{}, dataSet:{}, res:{}", projectId, dataSet, res);
                }
            }, (call, t) -> {
                logger.warn("Failed to parse data: projectId:{}, dataSet:{}", projectId, dataSet, t);
            });
        } else {
            // TODO status check
        }
    }

    public void runAutoML(final Project project, final AutoMLBuildControlV99 buildControl, final AutoMLInputV99 inputSpec,
            final AutoMLBuildModelsV99 buildModels) {
        h2oHelper.runAutoML(buildControl, inputSpec, buildModels).execute((call, res) -> {
            if (logger.isDebugEnabled()) {
                logger.debug("importFiles: {}", res);
            }
            if (res.code() == 200) {
                // TODO job
            } else {
                logger.warn("Failed to run AutoML: project:{}, res:{}", project, res);
            }
        }, (call, t) -> {
            logger.warn("Failed to run AutoML: project:{}", project, t);
        });
    }

    private String getDataPath(final String projectId, final String fileName) {
        return projectFolderName + "/" + projectId + "/data/" + fileName;
    }

    private String getProjectConfigPath(final String projectId) {
        return projectFolderName + "/" + projectId + "/" + projectJsonName;
    }

    private String getDataSetConfigPath(final String projectId, final String dataSetId) {
        return projectFolderName + "/" + projectId + "/config/" + dataSetId + "_dataset.json";
    }

    private String getS3Path(final String projectId, final String fileName) {
        final FessConfig fessConfig = ComponentUtil.getFessConfig();
        return "s3://" + fessConfig.getStorageBucket() + "/" + projectFolderName + "/" + projectId + "/data/" + fileName;
    }

}
