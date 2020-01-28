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
package org.codelibs.fione.app.web.admin.automl;

import static org.codelibs.fione.h2o.bindings.H2oApi.keyToString;

import java.io.InputStream;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Map.Entry;

import javax.servlet.http.HttpServletRequest;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.codelibs.core.lang.StringUtil;
import org.codelibs.fess.annotation.Secured;
import org.codelibs.fess.app.web.admin.user.SearchForm;
import org.codelibs.fess.util.RenderDataUtil;
import org.codelibs.fione.app.web.base.FioneAdminAction;
import org.codelibs.fione.entity.DataSet;
import org.codelibs.fione.entity.Project;
import org.codelibs.fione.h2o.bindings.builder.AutoMLBuildControlBuilder;
import org.codelibs.fione.h2o.bindings.builder.AutoMLBuildModelsBuilder;
import org.codelibs.fione.h2o.bindings.builder.AutoMLInputBuilder;
import org.codelibs.fione.h2o.bindings.builder.AutoMLStoppingCriteriaBuilder;
import org.codelibs.fione.h2o.bindings.pojos.AutoMLBuildControlV99;
import org.codelibs.fione.h2o.bindings.pojos.AutoMLBuildModelsV99;
import org.codelibs.fione.h2o.bindings.pojos.AutoMLCustomParameterV99;
import org.codelibs.fione.h2o.bindings.pojos.AutoMLInputV99;
import org.codelibs.fione.h2o.bindings.pojos.Automlapischemas3AutoMLBuildSpecAutoMLMetricProvider;
import org.codelibs.fione.h2o.bindings.pojos.Automlapischemas3AutoMLBuildSpecScopeProvider;
import org.codelibs.fione.h2o.bindings.pojos.FrameKeyV3;
import org.codelibs.fione.h2o.bindings.pojos.FrameV3;
import org.codelibs.fione.h2o.bindings.pojos.FramesV3;
import org.codelibs.fione.h2o.bindings.pojos.JobV3;
import org.codelibs.fione.h2o.bindings.pojos.JobV3.Kind;
import org.codelibs.fione.h2o.bindings.pojos.LeaderboardV99;
import org.codelibs.fione.h2o.bindings.pojos.ModelSchemaBaseV3;
import org.codelibs.fione.h2o.bindings.pojos.ParseV3;
import org.codelibs.fione.h2o.bindings.pojos.ScoreKeeperStoppingMetric;
import org.codelibs.fione.taglib.FioneFunctions;
import org.codelibs.fione.util.StringCodecUtil;
import org.lastaflute.web.Execute;
import org.lastaflute.web.UrlChain;
import org.lastaflute.web.response.ActionResponse;
import org.lastaflute.web.response.HtmlResponse;
import org.lastaflute.web.ruts.process.ActionRuntime;
import org.lastaflute.web.util.LaRequestUtil;

/**
 * @author shinsuke
 */
public class AdminAutomlAction extends FioneAdminAction {

    private static final String DATA_COLUMN_OFFSET = "data.column_offset";

    private static final String DATA_ROW_OFFSET = "data.row_offset";

    private static final String DETAILS = "details";

    public static final String ROLE = "admin-automl";

    private static final Logger logger = LogManager.getLogger(AdminAutomlAction.class);

    // ===================================================================================
    //                                                                               Hook
    //                                                                              ======
    @Override
    protected void setupHtmlData(final ActionRuntime runtime) {
        super.setupHtmlData(runtime);
        runtime.registerData("helpLink", systemHelper.getHelpLink("automl"));
    }

    @Override
    protected String getActionRole() {
        return ROLE;
    }

    // ===================================================================================
    //                                                                             Execute
    //                                                                      ==============
    @Execute
    @Secured({ ROLE, ROLE + VIEW })
    public HtmlResponse index() {
        return asListHtml();
    }

    @Execute
    @Secured({ ROLE, ROLE + VIEW })
    public HtmlResponse list() {
        return asListHtml();
    }

    @Execute
    @Secured({ ROLE })
    public HtmlResponse newproject() {
        saveToken();
        return asNewProjectHtml();
    }

    @Execute
    @Secured({ ROLE })
    public HtmlResponse createproject(final CreateProjectForm form) {
        validate(form, messages -> {}, this::asNewProjectHtml);
        verifyToken(this::asNewProjectHtml);
        final String projectId = StringCodecUtil.encodeUrlSafe(form.name);
        if (projectHelper.projectExists(projectId)) {
            throw validationError(messages -> messages.addErrorsProjectExists(GLOBAL, form.name), this::asListHtml);
        }
        final Project project = new Project(projectId);
        project.setName(form.name);
        try {
            projectHelper.store(project);
            saveMessage(messages -> messages.addSuccessCreatedProject(GLOBAL, form.name));
        } catch (final Exception e) {
            logger.warn("Failed to add " + project.getId(), e);
            throw validationError(messages -> messages.addErrorsFailedToCreateProject(GLOBAL, form.name), this::asNewProjectHtml);
        }
        return redirectDetailsHtml(project.getId(), null, null);
    }

    @Execute
    @Secured({ ROLE, ROLE + VIEW })
    public HtmlResponse details(final String projectId) {
        final String token = doubleSubmitManager.saveToken(myTokenGroupType());
        try {
            final Project project = projectHelper.getProject(projectId);
            final String frameId = LaRequestUtil.getOptionalRequest().map(req -> {
                final String fid = req.getParameter(FRAME_ID);
                if (fid != null) {
                    for (final String id : project.getFrameIds()) {
                        if (fid.equals(id)) {
                            return id;
                        }
                    }
                }
                if (project.getFrameIds().length > 0) {
                    return project.getFrameIds()[0];
                }
                return null;
            }).orElse(null);
            final FrameV3 columnSummaries = frameId != null ? projectHelper.getColumnSummaries(projectId, frameId) : null;

            final String leaderboardId = LaRequestUtil.getOptionalRequest().map(req -> {
                final String mid = req.getParameter(LEADERBOARD_ID);
                String lastId = null;
                for (final JobV3 id : project.getJobs()) {
                    if (id.getKind() == Kind.AUTO_ML && "DONE".equals(id.status)) {
                        final String destId = keyToString(id.dest);
                        if (mid != null && mid.equals(destId)) {
                            return destId;
                        }
                        lastId = destId;
                    }
                }
                if (lastId != null) {
                    return lastId;
                }
                return null;
            }).orElse(null);
            final LeaderboardV99 leaderboard = leaderboardId != null ? projectHelper.getLeaderboard(projectId, leaderboardId) : null;

            return asHtml(path_AdminAutoml_AdminAutomlDetailsJsp).renderWith(data -> {
                RenderDataUtil.register(data, "token", token);
                RenderDataUtil.register(data, "project", project);
                RenderDataUtil.register(data, "frameId", frameId);
                RenderDataUtil.register(data, "leaderboardId", leaderboardId);
                RenderDataUtil.register(data, "autoReload", project.hasRunningJobs());
                if (columnSummaries != null) {
                    RenderDataUtil.register(data, "columnSummaries", columnSummaries);
                }
                if (leaderboard != null) {
                    RenderDataUtil.register(data, "leaderboard", leaderboard);
                }
            });
        } catch (final Exception e) {
            logger.warn("Failed to read " + projectId, e);
            throw validationError(messages -> messages.addErrorsFailedToLoadProject(GLOBAL, StringCodecUtil.decode(projectId)),
                    this::asListHtml);
        }
    }

    @Execute
    @Secured({ ROLE, ROLE + VIEW })
    public HtmlResponse dataview(final String projectId) {
        final String token = doubleSubmitManager.saveToken(myTokenGroupType());
        try {
            final Project project = projectHelper.getProject(projectId);
            final String frameId = LaRequestUtil.getOptionalRequest().map(req -> {
                final String fid = req.getParameter(FRAME_ID);
                if (fid != null) {
                    for (final String id : project.getFrameIds()) {
                        if (fid.equals(id)) {
                            return id;
                        }
                    }
                }
                if (project.getFrameIds().length > 0) {
                    return project.getFrameIds()[0];
                }
                return null;
            }).orElse(null);
            final FrameV3 columnSummaries = frameId != null ? projectHelper.getColumnSummaries(projectId, frameId) : null;

            final String leaderboardId = LaRequestUtil.getOptionalRequest().map(req -> {
                final String mid = req.getParameter(LEADERBOARD_ID);
                String lastId = null;
                for (final JobV3 id : project.getJobs()) {
                    if (id.getKind() == Kind.AUTO_ML && "DONE".equals(id.status)) {
                        final String destId = keyToString(id.dest);
                        if (mid != null && mid.equals(destId)) {
                            return destId;
                        }
                        lastId = destId;
                    }
                }
                if (lastId != null) {
                    return lastId;
                }
                return null;
            }).orElse(null);

            final FramesV3 dataQuery = LaRequestUtil.getOptionalRequest().map(req -> {
                if (frameId == null) {
                    return null;
                }
                final FramesV3 params = new FramesV3();
                params.frameId = new FrameKeyV3(frameId);
                params.column = null;
                params.rowOffset = getParamAsLong(req, DATA_ROW_OFFSET, 0L);
                if (params.rowOffset < 0) {
                    params.rowOffset = 0L;
                }
                params.rowCount = 20;
                params.columnOffset = getParamAsInt(req, DATA_COLUMN_OFFSET, 0);
                if (params.columnOffset < 0) {
                    params.columnOffset = 0;
                }
                params.columnCount = 10;
                params.fullColumnCount = -1;
                params.findCompatibleModels = false;
                params.path = null;
                params.force = false;
                params.numParts = -1;
                params.compression = null;
                params.separator = 44;
                params._excludeFields = null;
                if (params.columnOffset + params.columnCount > columnSummaries.totalColumnCount) {
                    params.columnCount = columnSummaries.totalColumnCount - params.columnOffset;
                }
                return params;
            }).orElse(null);
            final FrameV3 frameData = dataQuery != null ? projectHelper.getFrameData(dataQuery) : null;

            return asHtml(path_AdminAutoml_AdminAutomlDataJsp).renderWith(data -> {
                RenderDataUtil.register(data, "token", token);
                RenderDataUtil.register(data, "project", project);
                RenderDataUtil.register(data, "frameId", frameId);
                RenderDataUtil.register(data, "leaderboardId", leaderboardId);
                if (columnSummaries != null) {
                    RenderDataUtil.register(data, "columnSummaries", columnSummaries);
                }
                if (frameData != null) {
                    RenderDataUtil.register(data, "frameData", frameData);
                }
            });
        } catch (final Exception e) {
            logger.warn("Failed to read " + projectId, e);
            throw validationError(messages -> messages.addErrorsFailedToLoadProject(GLOBAL, StringCodecUtil.decode(projectId)),
                    this::asListHtml);
        }
    }

    @Execute
    @Secured({ ROLE })
    public HtmlResponse newdataset(final String projectId) {
        saveToken();
        return asNewDataHtml(projectId);
    }

    @Execute
    @Secured({ ROLE })
    public HtmlResponse uploaddataset(final UploadDataSetForm form) {
        validate(form, messages -> {}, () -> asNewDataHtml(form.projectId));
        verifyToken(() -> asNewDataHtml(form.projectId));
        final String fileName = StringCodecUtil.normalize(form.dataFile.getFileName());
        try (InputStream in = form.dataFile.getInputStream()) {
            final DataSet dataSet = projectHelper.addDataSet(form.projectId, fileName, in);
            projectHelper.loadDataSetSchema(form.projectId, dataSet);
            saveMessage(messages -> messages.addSuccessUploadedDataset(GLOBAL, fileName));
        } catch (final Exception e) {
            logger.warn("Failed to add " + form.dataFile.getFileName(), e);
            throw validationError(messages -> messages.addErrorsFailedToUploadDataset(GLOBAL, fileName),
                    () -> asNewDataHtml(form.projectId));
        }
        return redirectDetailsHtml(form.projectId, null, null);
    }

    @Execute
    @Secured({ ROLE })
    public HtmlResponse deletedataset(final DataSetForm form) {
        validate(form, messages -> {}, () -> redirectDetailsHtml(form.projectId, form.frameId, form.leaderboardId));
        verifyTokenKeep(() -> redirectDetailsHtml(form.projectId, form.frameId, form.leaderboardId));
        try {
            projectHelper.deleteDataSet(form.projectId, form.dataSetId);
            saveMessage(messages -> messages.addSuccessDeletingDataset(GLOBAL, form.dataSetId));
        } catch (final Exception e) {
            logger.warn("Failed to delete data: {}", form.dataSetId, e);
            throw validationError(messages -> messages.addErrorsFailedToDeleteDataset(GLOBAL, form.dataSetId), this::asListHtml);
        }
        return redirectDetailsHtml(form.projectId, form.frameId, form.leaderboardId);
    }

    @Execute
    @Secured({ ROLE, ROLE + VIEW })
    public ActionResponse downloaddataset(final DataSetForm form) {
        validate(form, messages -> {}, () -> redirectDetailsHtml(form.projectId, form.frameId, form.leaderboardId));
        verifyTokenKeep(() -> redirectDetailsHtml(form.projectId, form.frameId, form.leaderboardId));

        final DataSet dataSet = projectHelper.getDataSet(form.projectId, form.dataSetId);
        if (dataSet == null) {
            throw validationError(messages -> messages.addErrorsDatasetIsNotFound(GLOBAL, form.dataSetId), this::asListHtml);
        }

        return asStream(dataSet.getName()).contentTypeOctetStream().stream(out -> projectHelper.writeDataSet(form.projectId, dataSet, out));
    }

    @Execute
    @Secured({ ROLE })
    public HtmlResponse newframe(final String projectId, final String dataSetId) {
        saveToken();
        return asNewFrameHtml(projectId, dataSetId);
    }

    @Execute
    @Secured({ ROLE })
    public HtmlResponse createframe(final CreateFrameForm form) {
        validate(form, messages -> {}, () -> asNewFrameHtml(form.projectId, form.dataSetId));
        verifyToken(() -> asNewFrameHtml(form.projectId, form.dataSetId));
        final DataSet dataSet = projectHelper.getDataSet(form.projectId, form.dataSetId);
        if (dataSet == null) {
            throw validationError(messages -> messages.addErrorsDatasetIsNotFound(GLOBAL, form.dataSetId), this::asListHtml);
        }

        final ParseV3 schema = dataSet.getSchema();
        if (schema == null) {
            throw validationError(messages -> messages.addErrorsDatasetSchemaIsNotFound(GLOBAL, form.dataSetId), this::asListHtml);
        }
        for (int i = 0; i < schema.columnNames.length; i++) {
            final String value = form.columns.get(StringCodecUtil.encodeUrlSafe(schema.columnNames[i]));
            if (StringUtil.isNotBlank(value)) {
                schema.columnTypes[i] = value;
            }
        }
        try {
            projectHelper.createFrame(form.projectId, dataSet, result -> {});
            saveMessage(messages -> messages.addSuccessLoadDataset(GLOBAL, dataSet.getName()));
        } catch (final Exception e) {
            logger.warn("Failed to create frame: {}", dataSet, e);
            throw validationError(messages -> messages.addErrorsFailedToCreateFrame(GLOBAL, dataSet.getName()),
                    () -> asNewFrameHtml(form.projectId, form.dataSetId));
        }
        return redirectDetailsHtml(form.projectId, null, null);
    }

    @Execute
    @Secured({ ROLE })
    public HtmlResponse deleteframe(final FrameForm form) {
        validate(form, messages -> {}, () -> redirectDetailsHtml(form.projectId, form.frameId, form.leaderboardId));
        verifyTokenKeep(() -> redirectDetailsHtml(form.projectId, form.frameId, form.leaderboardId));
        try {
            projectHelper.deleteFrame(form.frameId);
            saveMessage(messages -> messages.addSuccessDeletedFrame(GLOBAL, form.frameId));
        } catch (final Exception e) {
            logger.warn("Failed to delete frame: {}", form.frameId, e);
            throw validationError(messages -> messages.addErrorsFailedToDeleteFrame(GLOBAL, form.frameId), this::asListHtml);
        }
        return redirectDetailsHtml(form.projectId, null, form.leaderboardId);
    }

    @Execute
    @Secured({ ROLE })
    public HtmlResponse deletejob(final JobForm form) {
        validate(form, messages -> {}, () -> redirectDetailsHtml(form.projectId, form.frameId, form.leaderboardId));
        verifyTokenKeep(() -> redirectDetailsHtml(form.projectId, form.frameId, form.leaderboardId));
        try {
            projectHelper.deleteJob(form.projectId, form.jobId);
            saveMessage(messages -> messages.addSuccessDeletedJob(GLOBAL, form.jobId));
        } catch (final Exception e) {
            logger.warn("Failed to delete frame: {}", form.jobId, e);
            throw validationError(messages -> messages.addErrorsFailedToDeleteJob(GLOBAL, form.jobId), this::asListHtml);
        }
        return redirectDetailsHtml(form.projectId, form.frameId, form.leaderboardId);
    }

    @Execute
    @Secured({ ROLE })
    public HtmlResponse loaddataset(final DataSetForm form) {
        validate(form, messages -> {}, () -> redirectDetailsHtml(form.projectId, form.frameId, form.leaderboardId));
        verifyTokenKeep(() -> redirectDetailsHtml(form.projectId, form.frameId, form.leaderboardId));
        try {
            final DataSet dataSet = projectHelper.getDataSet(form.projectId, form.dataSetId);
            if (dataSet == null) {
                throw validationError(messages -> messages.addErrorsDatasetIsNotFound(GLOBAL, form.dataSetId), this::asListHtml);
            }
            if (dataSet.getSchema() == null && DataSet.TRAIN.equals(dataSet.getType())) {
                final DataSet[] dataSets = projectHelper.getDataSets(form.projectId);
                if (dataSets.length > 1) {
                    dataSet.setType(DataSet.TEST);
                }
            }
            projectHelper.loadDataSetSchema(form.projectId, dataSet);
            saveMessage(messages -> messages.addSuccessLoadDataset(GLOBAL, StringCodecUtil.decode(form.dataSetId)));
        } catch (final Exception e) {
            logger.warn("Failed to load {} in {}.", form.dataSetId, form.projectId, e);
            throw validationError(messages -> messages.addErrorsFailedToLoadDataset(GLOBAL, StringCodecUtil.decode(form.dataSetId)),
                    this::asListHtml);
        }
        return redirectDetailsHtml(form.projectId, form.frameId, form.leaderboardId);
    }

    @Execute
    @Secured({ ROLE })
    public HtmlResponse datasettype(final DataSetForm form) {
        validate(form, messages -> {}, () -> redirectDetailsHtml(form.projectId, form.frameId, form.leaderboardId));
        verifyTokenKeep(() -> redirectDetailsHtml(form.projectId, form.frameId, form.leaderboardId));
        try {
            final DataSet dataSet = projectHelper.getDataSet(form.projectId, form.dataSetId);
            if (dataSet == null) {
                throw validationError(messages -> messages.addErrorsDatasetIsNotFound(GLOBAL, form.dataSetId), this::asListHtml);
            }
            dataSet.setType(LaRequestUtil.getOptionalRequest().map(req -> req.getParameter("datasettype")).orElse(DataSet.TRAIN));
            projectHelper.store(form.projectId, dataSet);
            saveMessage(messages -> messages.addSuccessUpdateDataset(GLOBAL, StringCodecUtil.decode(form.dataSetId)));
        } catch (final Exception e) {
            logger.warn("Failed to load {} in {}.", form.dataSetId, form.projectId, e);
            throw validationError(messages -> messages.addErrorsFailedToUpdateDataset(GLOBAL, StringCodecUtil.decode(form.dataSetId)),
                    this::asListHtml);
        }
        return redirectDetailsHtml(form.projectId, form.frameId, form.leaderboardId);
    }

    @Execute
    @Secured({ ROLE })
    public HtmlResponse setupml(final String projectId, final String frameId) {
        saveToken();
        return asSetupMlHtml(projectId, frameId);
    }

    @Execute
    @Secured({ ROLE })
    public HtmlResponse runautoml(final TrainForm form) {
        validate(form, messages -> {}, this::asNewProjectHtml);
        verifyToken(this::asNewProjectHtml);

        final Project project = projectHelper.getProject(form.projectId);
        if (project == null) {
            throw validationError(messages -> messages.addErrorsProjectIsNotFound(GLOBAL, form.projectId), this::asListHtml);
        }
        final String[] ignoredColumns =
                form.ignoredColumns.entrySet().stream().filter(e -> StringUtil.isNotBlank(e.getValue())).map(Entry<String, String>::getKey)
                        .toArray(n -> new String[n]);
        try {
            final AutoMLBuildControlV99 buildControl =
                    AutoMLBuildControlBuilder
                            .create()
                            .projectName(form.projectName)
                            .nfolds(form.nfolds)
                            .balanceClasses(Boolean.valueOf(form.balanceClasses))
                            .stoppingCriteria(
                                    AutoMLStoppingCriteriaBuilder.create().seed(form.seed).maxModels(form.maxModels)
                                            .maxRuntimeSecs(form.maxRuntimeSecs).maxRuntimeSecsPerModel(form.maxRuntimeSecsPerModel)
                                            .stoppingRounds(form.stoppingRounds)
                                            .stoppingMetric(ScoreKeeperStoppingMetric.valueOf(form.stoppingMetric))
                                            .stoppingTolerance(form.stoppingTolerance).build())
                            .keepCrossValidationPredictions(Boolean.valueOf(form.keepCrossValidationPredictions))
                            .keepCrossValidationModels(Boolean.valueOf(form.keepCrossValidationModels))
                            .keepCrossValidationFoldAssignment(Boolean.valueOf(form.keepCrossValidationFoldAssignment)).build();
            final AutoMLInputV99 input =
                    AutoMLInputBuilder.create().trainingFrame(form.frameId).responseColumn(form.responseColumn, null)
                            .ignoredColumns(ignoredColumns)
                            .sortMetric(Automlapischemas3AutoMLBuildSpecAutoMLMetricProvider.valueOf(form.sortMetric)).build();
            final List<AutoMLCustomParameterV99> argParamList = new ArrayList<>();
            argParamList.add(new AutoMLCustomParameterV99(Automlapischemas3AutoMLBuildSpecScopeProvider.DeepLearning,
                    "max_categorical_features", form.maxCategoricalFeatures));
            final AutoMLBuildModelsV99 buildModels =
                    AutoMLBuildModelsBuilder.create().algoParameters(argParamList.toArray(n -> new AutoMLCustomParameterV99[n])).build();

            projectHelper.runAutoML(form.projectId, buildControl, input, buildModels);
            saveMessage(messages -> messages.addSuccessBuildingModels(GLOBAL));
        } catch (final Exception e) {
            logger.warn("Failed to run AutoML.", e);
            throw validationError(messages -> messages.addErrorsFailedToStartBuild(GLOBAL),
                    () -> asSetupMlHtml(form.projectId, form.frameId));
        }
        return redirectDetailsHtml(form.projectId, form.frameId, null);
    }

    @Execute
    @Secured({ ROLE })
    public HtmlResponse prediction(final String projectId, final String frameId, final String leaderboardId) {
        saveToken();
        return asPredictionMlHtml(projectId, frameId, leaderboardId);
    }

    @Execute
    @Secured({ ROLE })
    public HtmlResponse predictframe(final PredictSettingForm form) {
        validate(form, messages -> {}, () -> asPredictionMlHtml(form.projectId, form.frameId, form.leaderboardId));
        verifyToken(this::asNewProjectHtml);

        try {
            projectHelper.predict(form.projectId, form.frameId, form.modelId, form.name);
            saveMessage(messages -> messages.addSuccessExportingFrame(GLOBAL, form.frameId, form.name));
        } catch (final Exception e) {
            logger.warn("Failed to run AutoML.", e);
            throw validationError(messages -> messages.addErrorsFailedToExportFrame(GLOBAL, form.frameId),
                    () -> asSetupMlHtml(form.projectId, form.frameId));
        }
        return redirectDetailsHtml(form.projectId, form.frameId, form.leaderboardId);
    }

    @Execute
    @Secured({ ROLE })
    public HtmlResponse deletealljobs(final JobForm form) {
        validate(form, messages -> {}, () -> redirectDetailsHtml(form.projectId, form.frameId, form.leaderboardId));
        verifyTokenKeep(() -> redirectDetailsHtml(form.projectId, form.frameId, form.leaderboardId));
        try {
            projectHelper.deleteAllJobs(form.projectId);
            saveMessage(messages -> messages.addSuccessDeletedAllJobs(GLOBAL));
        } catch (final Exception e) {
            logger.warn("Failed to delete frame: {}", form.jobId, e);
            throw validationError(messages -> messages.addErrorsFailedToDeleteJobs(GLOBAL), this::asListHtml);
        }
        return redirectDetailsHtml(form.projectId, form.frameId, form.leaderboardId);
    }

    @Execute
    @Secured({ ROLE })
    public HtmlResponse newsession(final ProjectForm form) {
        validate(form, messages -> {}, () -> redirectDetailsHtml(form.projectId, form.frameId, form.leaderboardId));
        verifyTokenKeep(() -> redirectDetailsHtml(form.projectId, form.frameId, form.leaderboardId));
        try {
            projectHelper.renewSession(form.projectId);
            saveMessage(messages -> messages.addSuccessRenewSession(GLOBAL));
        } catch (final Exception e) {
            logger.warn("Failed to renew session: {}", form.projectId, e);
            throw validationError(messages -> messages.addErrorsFailedToRenewSession(GLOBAL), this::asListHtml);
        }
        return redirectDetailsHtml(form.projectId, form.frameId, form.leaderboardId);
    }

    @Execute
    @Secured({ ROLE })
    public HtmlResponse deleteproject(final ProjectForm form) {
        validate(form, messages -> {}, () -> redirectDetailsHtml(form.projectId, form.frameId, form.leaderboardId));
        verifyTokenKeep(() -> redirectDetailsHtml(form.projectId, form.frameId, form.leaderboardId));
        try {
            projectHelper.deleteProject(form.projectId);
            saveMessage(messages -> messages.addSuccessDeletedProject(GLOBAL, StringCodecUtil.decode(form.projectId)));
        } catch (final Exception e) {
            logger.warn("Failed to delete project: {}", form.projectId, e);
            throw validationError(messages -> messages.addErrorsFailedToDeleteProject(GLOBAL, StringCodecUtil.decode(form.projectId)),
                    this::asListHtml);
        }
        return redirect(getClass());
    }

    @Execute
    @Secured({ ROLE })
    public HtmlResponse model(final String projectId, final String modelId) {
        final String token = doubleSubmitManager.saveToken(myTokenGroupType());

        final ModelSchemaBaseV3 model = projectHelper.getModel(projectId, modelId);

        return asHtml(path_AdminAutoml_AdminAutomlModelJsp).renderWith(
                data -> {
                    RenderDataUtil.register(data, "token", token);
                    RenderDataUtil.register(data, "projectId", projectId);
                    RenderDataUtil.register(data, "frameId", LaRequestUtil.getOptionalRequest().map(req -> req.getParameter(FRAME_ID))
                            .orElse(null));
                    RenderDataUtil.register(data, "leaderboardId",
                            LaRequestUtil.getOptionalRequest().map(req -> req.getParameter(LEADERBOARD_ID)).orElse(null));
                    RenderDataUtil.register(data, "model", model);
                });
    }

    @Execute
    @Secured({ ROLE, ROLE + VIEW })
    public ActionResponse downloadmojo(final ModelForm form) {
        validate(form, messages -> {}, () -> redirectModelHtml(form.projectId, form.modelId, form.frameId, form.leaderboardId));
        verifyTokenKeep(() -> redirectModelHtml(form.projectId, form.modelId, form.frameId, form.leaderboardId));

        return asStream(form.modelId + ".zip").contentTypeOctetStream().stream(
                out -> projectHelper.writeMojo(form.projectId, form.modelId, out));
    }

    @Execute
    @Secured({ ROLE, ROLE + VIEW })
    public ActionResponse downloadgenmodel(final ModelForm form) {
        validate(form, messages -> {}, () -> redirectModelHtml(form.projectId, form.modelId, form.frameId, form.leaderboardId));
        verifyTokenKeep(() -> redirectModelHtml(form.projectId, form.modelId, form.frameId, form.leaderboardId));

        return asStream("h2o-genmodel.jar").contentTypeOctetStream().stream(
                out -> projectHelper.writeGenModel(form.projectId, form.modelId, out));
    }

    @Execute
    @Secured({ ROLE })
    public HtmlResponse deletemodel(final ModelForm form) {
        validate(form, messages -> {}, () -> redirectModelHtml(form.projectId, form.modelId, form.frameId, form.leaderboardId));
        verifyTokenKeep(() -> redirectModelHtml(form.projectId, form.modelId, form.frameId, form.leaderboardId));
        try {
            projectHelper.deleteModel(form.projectId, form.modelId);
            saveMessage(messages -> messages.addSuccessDeletedModel(GLOBAL, form.modelId));
        } catch (final Exception e) {
            logger.warn("Failed to delete model: {}", form.modelId, e);
            throw validationError(messages -> messages.addErrorsFailedToDeleteModel(GLOBAL, form.modelId), this::asListHtml);
        }
        return redirectDetailsHtml(form.projectId, form.frameId, form.leaderboardId);
    }

    @Execute
    @Secured({ ROLE })
    public ActionResponse exportmodel(final ModelForm form) {
        validate(form, messages -> {}, () -> redirectModelHtml(form.projectId, form.modelId, form.frameId, form.leaderboardId));
        verifyTokenKeep(() -> redirectModelHtml(form.projectId, form.modelId, form.frameId, form.leaderboardId));

        try {
            projectHelper.exportModel(form.projectId, form.leaderboardId, form.modelId);
            saveMessage(messages -> messages.addSuccessExportingModel(GLOBAL, form.modelId));
        } catch (final Exception e) {
            logger.warn("Failed to export model: {}", form.modelId, e);
            throw validationError(messages -> messages.addErrorsFailedToExportModel(GLOBAL, form.modelId), this::asListHtml);
        }
        return redirectModelHtml(form.projectId, form.modelId, form.frameId, form.leaderboardId);
    }

    @Execute
    @Secured({ ROLE })
    public ActionResponse exportallmodels(final LeaderboardForm form) {
        validate(form, messages -> {}, () -> redirectDetailsHtml(form.projectId, form.frameId, form.leaderboardId));
        verifyTokenKeep(() -> redirectDetailsHtml(form.projectId, form.frameId, form.leaderboardId));

        try {
            projectHelper.exportAllModels(form.projectId, form.leaderboardId);
            saveMessage(messages -> messages.addSuccessExportingAllModels(GLOBAL));
        } catch (final Exception e) {
            logger.warn("Failed to export models", e);
            throw validationError(messages -> messages.addErrorsFailedToExportModels(GLOBAL), this::asListHtml);
        }
        return redirectDetailsHtml(form.projectId, form.frameId, form.leaderboardId);
    }

    // ===================================================================================
    //                                                                              JSP
    //                                                                           =========

    private HtmlResponse asListHtml() {
        return asHtml(path_AdminAutoml_AdminAutomlJsp).renderWith(
                data -> RenderDataUtil.register(data, "projects", projectHelper.getProjects())).useForm(SearchForm.class);
    }

    private HtmlResponse asNewProjectHtml() {
        return asHtml(path_AdminAutoml_AdminAutomlNewprojectJsp).useForm(CreateProjectForm.class);
    }

    private HtmlResponse asNewDataHtml(final String projectId) {
        return asHtml(path_AdminAutoml_AdminAutomlNewdataJsp).useForm(UploadDataSetForm.class,
                setup -> setup.setup(form -> form.projectId = projectId));
    }

    private HtmlResponse asNewFrameHtml(final String projectId, final String dataSetId) {
        final DataSet dataSet = projectHelper.getDataSet(projectId, dataSetId);
        if (dataSet == null) {
            throw validationError(messages -> messages.addErrorsDatasetIsNotFound(GLOBAL, StringCodecUtil.decode(dataSetId)),
                    this::asListHtml);
        }
        final ParseV3 schema = dataSet.getSchema();
        if (schema == null) {
            throw validationError(messages -> messages.addErrorsDatasetSchemaIsNotFound(GLOBAL, StringCodecUtil.decode(dataSetId)),
                    this::asListHtml);
        }
        return asHtml(path_AdminAutoml_AdminAutomlNewframeJsp).useForm(CreateFrameForm.class, setup -> setup.setup(form -> {
            form.projectId = projectId;
            form.dataSetId = dataSetId;
        })).renderWith(data -> {
            registerColumnItems(schema, data, (maps, i) -> maps);
            registerColumnTypeItems(data);
        });
    }

    private HtmlResponse asSetupMlHtml(final String projectId, final String frameId) {
        final FrameV3 columnSummaries = projectHelper.getColumnSummaries(projectId, frameId);

        return asHtml(path_AdminAutoml_AdminAutomlRunmlJsp).useForm(TrainForm.class, setup -> setup.setup(form -> {
            form.projectId = projectId;
            form.frameId = frameId;
            form.projectName = StringCodecUtil.normalize(StringCodecUtil.decode(projectId));
        })).renderWith(data -> {
            final String[] columnItems = Arrays.stream(columnSummaries.columns).map(c -> c.label).toArray(n -> new String[n]);
            RenderDataUtil.register(data, "columnItems", columnItems);
            registerStoppingMetricItems(data);
            registerSortMetricItems(data);
        });
    }

    private HtmlResponse asPredictionMlHtml(final String projectId, final String frameId, final String leaderboardId) {
        final LeaderboardV99 leaderboard = leaderboardId != null ? projectHelper.getLeaderboard(projectId, leaderboardId) : null;
        if (leaderboard == null) {
            throw validationError(messages -> messages.addErrorsLeaderboardIsNotFound(GLOBAL), this::asListHtml);
        }
        final String[] modelIdItems = Arrays.stream(leaderboard.models).map(m -> m.name).toArray(n -> new String[n]);

        return asHtml(path_AdminAutoml_AdminAutomlPredictJsp).useForm(PredictSettingForm.class, setup -> setup.setup(form -> {
            form.projectId = projectId;
            form.frameId = frameId;
            form.leaderboardId = leaderboardId;
            form.modelId = LaRequestUtil.getOptionalRequest().map(req -> req.getParameter(MODEL_ID)).orElse(null);
            String frameName = FioneFunctions.frameName(frameId);
            final int pos = frameName.lastIndexOf('.');
            if (pos != -1) {
                frameName = frameName.substring(0, pos);
            }
            form.name = frameName + "_" + new SimpleDateFormat("yyyyMMddHHmmss").format(systemHelper.getCurrentTime());
        })).renderWith(data -> RenderDataUtil.register(data, "modelIdItems", modelIdItems));
    }

    private HtmlResponse redirectDetailsHtml(final String projectId, final String frameId, final String leaderboardId) {
        final UrlChain moreUrl = moreUrl(DETAILS, projectId);
        final List<String> params = new ArrayList<>();
        if (StringUtil.isNotBlank(frameId)) {
            params.add(FRAME_ID);
            params.add(frameId);
        }
        if (StringUtil.isNotBlank(leaderboardId)) {
            params.add(LEADERBOARD_ID);
            params.add(leaderboardId);
        }
        if (!params.isEmpty()) {
            final Object[] args = params.toArray(n -> new String[n]);
            moreUrl.params(args);
        }
        return redirectWith(getClass(), moreUrl);
    }

    private HtmlResponse redirectModelHtml(final String projectId, final String modelId, final String frameId, final String leaderboardId) {
        final UrlChain moreUrl = moreUrl("model", projectId, modelId);
        final List<String> params = new ArrayList<>();
        if (StringUtil.isNotBlank(frameId)) {
            params.add(FRAME_ID);
            params.add(frameId);
        }
        if (StringUtil.isNotBlank(leaderboardId)) {
            params.add(LEADERBOARD_ID);
            params.add(leaderboardId);
        }
        if (!params.isEmpty()) {
            final Object[] args = params.toArray(n -> new String[n]);
            moreUrl.params(args);
        }
        return redirectWith(getClass(), moreUrl);
    }

    private int getParamAsInt(final HttpServletRequest req, final String key, final int defautValue) {
        final String s = req.getParameter(key);
        if (StringUtil.isBlank(s)) {
            return defautValue;
        } else {
            try {
                return Integer.parseInt(s);
            } catch (final NumberFormatException e) {
                return defautValue;
            }
        }
    }

    private long getParamAsLong(final HttpServletRequest req, final String key, final long defautValue) {
        final String s = req.getParameter(key);
        if (StringUtil.isBlank(s)) {
            return defautValue;
        } else {
            try {
                return Long.parseLong(s);
            } catch (final NumberFormatException e) {
                return defautValue;
            }
        }
    }
}
