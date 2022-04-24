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
package org.codelibs.fione.app.web.admin.easyml;

import static org.codelibs.fione.h2o.bindings.H2oApi.keyToString;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.codelibs.core.lang.StringUtil;
import org.codelibs.fess.annotation.Secured;
import org.codelibs.fess.util.RenderDataUtil;
import org.codelibs.fione.Constants;
import org.codelibs.fione.app.web.base.FioneAdminAction;
import org.codelibs.fione.entity.DataSet;
import org.codelibs.fione.entity.Project;
import org.codelibs.fione.h2o.bindings.builder.AutoMLBuildControlBuilder;
import org.codelibs.fione.h2o.bindings.builder.AutoMLBuildModelsBuilder;
import org.codelibs.fione.h2o.bindings.builder.AutoMLInputBuilder;
import org.codelibs.fione.h2o.bindings.builder.AutoMLStoppingCriteriaBuilder;
import org.codelibs.fione.h2o.bindings.pojos.AutoMLCustomParameterV99;
import org.codelibs.fione.h2o.bindings.pojos.Automlapischemas3AutoMLBuildSpecAutoMLMetricProvider;
import org.codelibs.fione.h2o.bindings.pojos.Automlapischemas3AutoMLBuildSpecScopeProvider;
import org.codelibs.fione.h2o.bindings.pojos.ColV3;
import org.codelibs.fione.h2o.bindings.pojos.FrameV3;
import org.codelibs.fione.h2o.bindings.pojos.JobV3;
import org.codelibs.fione.h2o.bindings.pojos.JobV3.Kind;
import org.codelibs.fione.h2o.bindings.pojos.LeaderboardV99;
import org.codelibs.fione.h2o.bindings.pojos.ScoreKeeperStoppingMetric;
import org.codelibs.fione.util.StringCodecUtil;
import org.lastaflute.di.util.tiger.Maps;
import org.lastaflute.web.Execute;
import org.lastaflute.web.response.ActionResponse;
import org.lastaflute.web.response.HtmlResponse;
import org.lastaflute.web.ruts.process.ActionRuntime;
import org.lastaflute.web.util.LaRequestUtil;

public class AdminEasymlAction extends FioneAdminAction {

    public static final String ROLE = "admin-easyml";

    private static final Logger logger = LogManager.getLogger(AdminEasymlAction.class);

    // ===================================================================================
    //                                                                               Hook
    //                                                                              ======
    @Override
    protected void setupHtmlData(final ActionRuntime runtime) {
        super.setupHtmlData(runtime);
        runtime.registerData("helpLink", systemHelper.getHelpLink("easyml"));
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
        return redirectWith(getClass(), moreUrl("dataset"));
    }

    @Execute
    @Secured({ ROLE, ROLE + VIEW })
    public HtmlResponse dataset() {
        saveToken();
        return asListHtml();
    }

    @Execute
    @Secured({ ROLE })
    public HtmlResponse uploaddataset(final DataSetForm form) {
        validate(form, messages -> {}, this::asListHtml);
        verifyToken(this::asListHtml);
        final var projectId = StringCodecUtil.encodeUrlSafe(form.name);
        final var sessionKey = getSessionKey();
        if (projectHelper.projectExists(sessionKey, projectId)) {
            throw validationError(messages -> messages.addErrorsProjectExists(GLOBAL, form.name), this::asListHtml);
        }
        final var project = new Project(projectId);
        project.setName(form.name);
        try (var in = form.file.getInputStream()) {
            projectHelper.store(project);
            final var fileName = StringCodecUtil.normalize(form.file.getFileName());
            final var dataSet = projectHelper.addDataSet(sessionKey, project.getId(), fileName, in, 0);
            projectHelper.loadDataSetSchema(sessionKey, projectId, dataSet);
            saveMessage(messages -> messages.addSuccessCreatedProject(GLOBAL, form.name));
        } catch (final Exception e) {
            logger.warn("Failed to create " + project.getId(), e);
            throw validationError(messages -> messages.addErrorsFailedToCreateProject(GLOBAL, form.name), this::asListHtml);
        }
        return redirectJobHtml(project.getId());
    }

    @Execute
    @Secured({ ROLE, ROLE + VIEW })
    public HtmlResponse job(final String projectId) {
        final var sessionKey = getSessionKey();
        final var project = projectHelper.getProject(sessionKey, projectId);
        if (project == null) {
            return redirectWith(getClass(), moreUrl("dataset"));
        }
        final var jobs = project.getJobs();
        for (final JobV3 job : jobs) {
            if ("RUNNING".equals(job.status)) {
                return asJobHtml(project);
            }
        }
        final var dataSets = project.getDataSets();
        final var dataSet = findDataSet(dataSets);
        if (dataSet == null) {
            // TODO no dataset
            return redirectWith(getClass(), moreUrl("dataset"));
        }
        if (dataSet.getSchema() == null) {
            projectHelper.loadDataSetSchema(sessionKey, projectId, dataSet);
            return asJobHtml(project);
        }
        final var columnSummaries = getColumnSummaries(projectId, project);
        if (columnSummaries == null) {
            projectHelper.createFrame(sessionKey, projectId, dataSet, result -> {});
            return asJobHtml(project);
        }
        for (var i = jobs.length - 1; i >= 0; i--) {
            final var job = jobs[i];
            if (job.getKind() == Kind.AUTO_ML) {
                final var leaderboardId = keyToString(job.dest);
                final var leaderboard = projectHelper.getLeaderboard(sessionKey, projectId, leaderboardId);
                if (leaderboard != null) {
                    return redirectSummaryHtml(projectId, dataSet.getId(), leaderboardId);
                }
            }
        }
        return redirectTrainHtml(projectId, dataSet.getId());
    }

    protected DataSet findDataSet(final DataSet[] dataSets) {
        if (dataSets == null || dataSets.length == 0) {
            return null;
        }
        for (final DataSet dataSet : dataSets) {
            if (dataSet.getSchema() != null && DataSet.TRAIN.equals(dataSet.getType())) {
                return dataSet;
            }
        }
        for (final DataSet dataSet : dataSets) {
            if (DataSet.TRAIN.equals(dataSet.getType())) {
                return dataSet;
            }
        }
        return dataSets[0];
    }

    @Execute
    @Secured({ ROLE, ROLE + VIEW })
    public HtmlResponse train(final String projectId) {
        final var dataSetId = LaRequestUtil.getOptionalRequest().map(req -> req.getParameter(DATASET_ID)).orElse(null);
        if (StringUtil.isBlank(dataSetId)) {
            throw validationError(messages -> messages.addErrorsDatasetIsNotFound(GLOBAL, "?"), this::asListHtml);
        }
        return asTrainHtml(projectId, dataSetId);
    }

    @Execute
    @Secured({ ROLE })
    public HtmlResponse runautoml(final TrainForm form) {
        validate(form, messages -> {}, () -> asTrainHtml(form.projectId, form.dataSetId));
        verifyToken(() -> asTrainHtml(form.projectId, form.dataSetId));

        final var sessionKey = getSessionKey();
        final var project = projectHelper.getProject(sessionKey, form.projectId);
        if (project == null) {
            throw validationError(messages -> messages.addErrorsProjectIsNotFound(GLOBAL, form.projectId), this::asListHtml);
        }
        final var dataSet = project.getDataSet(form.dataSetId);
        if (dataSet == null) {
            throw validationError(messages -> messages.addErrorsDatasetIsNotFound(GLOBAL, StringCodecUtil.decode(form.dataSetId)),
                    this::asListHtml);
        }
        final var schema = dataSet.getSchema();
        if (schema == null) {
            throw validationError(messages -> messages.addErrorsDatasetSchemaIsNotFound(GLOBAL, StringCodecUtil.decode(form.dataSetId)),
                    this::asListHtml);
        }
        form.columns.put(form.responseColumn, "on");
        form.columnTypes.put(form.responseColumn, Constants.REGRESSION_TYPE.equals(form.predictionType) ? "Numeric" : "Enum");
        try {
            final var columnSummaries = projectHelper.getColumnSummaries(sessionKey, form.projectId, form.frameId);
            final var ignoredColumns = Arrays.stream(columnSummaries.columns)
                    .filter(col -> !form.columns.containsKey(StringCodecUtil.encodeUrlSafe(col.label))).map(col -> col.label)
                    .toArray(n -> new String[n]);
            var updateColumnType = false;
            for (var i = 0; i < columnSummaries.columns.length; i++) {
                final var col = columnSummaries.columns[i];
                final var columnId = StringCodecUtil.encodeUrlSafe(col.label);
                if (!form.columns.containsKey(columnId)) {
                    continue;
                }
                final var columnType = form.columnTypes.get(columnId);
                if (columnType != null && !columnType.equals(convertSchemaColumnType(col.type))) {
                    projectHelper.changeColumnType(sessionKey, form.projectId, form.frameId, i, columnType, 0, columnSummaries.rows);
                    schema.columnTypes[i] = columnType;
                    updateColumnType = true;
                }
            }
            if (updateColumnType) {
                projectHelper.store(form.projectId, dataSet);
            }

            final var projectName = StringCodecUtil.normalize(StringCodecUtil.decode(form.projectId));
            final var responseColumn = StringCodecUtil.decode(form.responseColumn);

            final var buildControl = AutoMLBuildControlBuilder.create().projectName(projectName).nfolds(form.nfolds)
                    .balanceClasses(Boolean.parseBoolean(form.balanceClasses))
                    .stoppingCriteria(AutoMLStoppingCriteriaBuilder.create().seed(form.seed).maxModels(form.maxModels)
                            .maxRuntimeSecs(form.maxRuntimeSecs).maxRuntimeSecsPerModel(form.maxRuntimeSecsPerModel)
                            .stoppingRounds(form.stoppingRounds).stoppingMetric(ScoreKeeperStoppingMetric.valueOf(form.stoppingMetric))
                            .stoppingTolerance(form.stoppingTolerance).build())
                    .keepCrossValidationPredictions(Boolean.parseBoolean(form.keepCrossValidationPredictions))
                    .keepCrossValidationModels(Boolean.parseBoolean(form.keepCrossValidationModels))
                    .keepCrossValidationFoldAssignment(Boolean.parseBoolean(form.keepCrossValidationFoldAssignment)).build();
            final var input = AutoMLInputBuilder.create().trainingFrame(form.frameId).responseColumn(responseColumn, null)
                    .ignoredColumns(ignoredColumns)
                    .sortMetric(Automlapischemas3AutoMLBuildSpecAutoMLMetricProvider.valueOf(form.sortMetric)).build();
            final List<AutoMLCustomParameterV99> argParamList = new ArrayList<>();
            argParamList.add(new AutoMLCustomParameterV99(Automlapischemas3AutoMLBuildSpecScopeProvider.DeepLearning,
                    "max_categorical_features", form.maxCategoricalFeatures));
            final var buildModels =
                    AutoMLBuildModelsBuilder.create().algoParameters(argParamList.toArray(n -> new AutoMLCustomParameterV99[n])).build();

            projectHelper.runAutoML(sessionKey, form.projectId, buildControl, input, buildModels);
        } catch (final Exception e) {
            logger.warn("Failed to run AutoML.", e);
            throw validationError(messages -> messages.addErrorsFailedToStartBuild(GLOBAL),
                    () -> asTrainHtml(form.projectId, form.dataSetId));
        }

        return asJobHtml(project);
    }

    @Execute
    @Secured({ ROLE, ROLE + VIEW })
    public HtmlResponse summary(final String projectId) {
        final var dataSetId = LaRequestUtil.getOptionalRequest().map(req -> req.getParameter(DATASET_ID)).orElse(null);
        if (StringUtil.isBlank(dataSetId)) {
            throw validationError(messages -> messages.addErrorsDatasetIsNotFound(GLOBAL, "?"), this::asListHtml);
        }
        final var leaderboardId = LaRequestUtil.getOptionalRequest().map(req -> req.getParameter(LEADERBOARD_ID)).orElse(null);
        if (StringUtil.isBlank(leaderboardId)) {
            throw validationError(messages -> messages.addErrorsLeaderboardIsNotFound(GLOBAL), this::asListHtml);
        }
        return asSummaryHtml(projectId, dataSetId, leaderboardId);
    }

    private FrameV3 getColumnSummaries(final String projectId, final Project project) {
        for (final String frameId : project.getFrameIds()) {
            final var columnSummaries = projectHelper.getColumnSummaries(getSessionKey(), projectId, frameId);
            if (columnSummaries != null) {
                return columnSummaries;
            }
        }
        return null;
    }

    @Execute
    @Secured({ ROLE })
    public HtmlResponse prediction(final String projectId) {
        saveToken();
        final var dataSetId = LaRequestUtil.getOptionalRequest().map(req -> req.getParameter(DATASET_ID)).orElse(null);
        if (StringUtil.isBlank(dataSetId)) {
            throw validationError(messages -> messages.addErrorsDatasetIsNotFound(GLOBAL, "?"), this::asListHtml);
        }
        final var leaderboardId = LaRequestUtil.getOptionalRequest().map(req -> req.getParameter(LEADERBOARD_ID)).orElse(null);
        if (StringUtil.isBlank(leaderboardId)) {
            throw validationError(messages -> messages.addErrorsLeaderboardIsNotFound(GLOBAL), this::asListHtml);
        }
        return asPredictionHtml(projectId, dataSetId, leaderboardId);
    }

    @Execute
    @Secured({ ROLE })
    public HtmlResponse uploadprediction(final UploadPredictionForm form) {
        validate(form, messages -> {}, () -> asPredictionHtml(form.projectId, form.dataSetId, form.leaderboardId));
        verifyToken(() -> asPredictionHtml(form.projectId, form.dataSetId, form.leaderboardId));
        final var sessionKey = getSessionKey();
        final var project = projectHelper.getProject(sessionKey, form.projectId);
        if (project == null) {
            throw validationError(messages -> messages.addErrorsProjectIsNotFound(GLOBAL, form.projectId), this::asListHtml);
        }
        final var dataSet = project.getDataSet(form.dataSetId);
        if (dataSet == null) {
            throw validationError(messages -> messages.addErrorsDatasetIsNotFound(GLOBAL, StringCodecUtil.decode(form.dataSetId)),
                    this::asListHtml);
        }
        final var schema = dataSet.getSchema();
        if (schema == null) {
            throw validationError(messages -> messages.addErrorsDatasetSchemaIsNotFound(GLOBAL, StringCodecUtil.decode(form.dataSetId)),
                    this::asListHtml);
        }
        final var leaderboard = projectHelper.getLeaderboard(sessionKey, form.projectId, form.leaderboardId);
        if (leaderboard == null) {
            throw validationError(messages -> messages.addErrorsLeaderboardIsNotFound(GLOBAL), this::asListHtml);
        }
        final Map<String, String> columnTypeMap = new HashMap<>();
        final var columnNames = schema.getAvailableColumnNames();
        for (var i = 0; i < columnNames.length; i++) {
            columnTypeMap.put(columnNames[i], schema.columnTypes[i]);
        }
        final var fileName = StringCodecUtil.normalize(form.file.getFileName());
        try (var in = form.file.getInputStream()) {
            final var predictDataSet = projectHelper.addDataSet(sessionKey, form.projectId, fileName, in, 0);
            projectHelper.loadDataSetSchema(sessionKey, form.projectId, predictDataSet, () -> {
                final var predictSchema = predictDataSet.getSchema();
                final var predictColumnNames = predictSchema.getAvailableColumnNames();
                for (var i = 0; i < predictColumnNames.length; i++) {
                    if (columnTypeMap.containsKey(predictColumnNames[i])) {
                        final var columnType = columnTypeMap.get(predictColumnNames[i]);
                        if (!predictSchema.columnTypes[i].equals(columnType)) {
                            predictSchema.columnTypes[i] = columnType;
                        }
                    }
                }
                predictDataSet.setType(DataSet.TEST);
                projectHelper.store(form.projectId, predictDataSet);
                projectHelper.createFrame(sessionKey, form.projectId, predictDataSet, response -> {
                    projectHelper.predict(sessionKey, form.projectId, keyToString(response.body().destinationFrame),
                            keyToString(leaderboard.models[0]), form.name, d -> {
                                if (form.columnNames != null && form.columnNames.length > 0) {
                                    final Map<String, String> columnMap = new LinkedHashMap<>();
                                    Arrays.stream(form.columnNames).map(StringCodecUtil::decode).forEach(s -> columnMap.put(s, s));
                                    columnMap.put("predict", getResponseColumn(leaderboard.projectName));
                                    projectHelper.filterColumns(sessionKey, form.projectId, d, columnMap);
                                }
                            });
                });
            });
            saveMessage(messages -> messages.addSuccessUploadedDataset(GLOBAL, fileName));
        } catch (final Exception e) {
            logger.warn("Failed to add " + form.file.getFileName(), e);
            throw validationError(messages -> messages.addErrorsFailedToUploadDataset(GLOBAL, fileName), () -> {
                saveToken();
                return asPredictionHtml(form.projectId, form.dataSetId, form.leaderboardId);
            });
        }
        return asJobHtml(project);
    }

    @Execute
    @Secured({ ROLE, ROLE + VIEW })
    public ActionResponse downloaddataset(final PredictDataSetForm form) { // TODO form
        validate(form, messages -> {}, () -> redirectSummaryHtml(form.projectId, form.dataSetId, form.leaderboardId));
        verifyTokenKeep(() -> redirectSummaryHtml(form.projectId, form.dataSetId, form.leaderboardId));

        final var dataSet = projectHelper.getDataSet(form.projectId, form.dataSetId);
        if (dataSet == null) {
            throw validationError(messages -> messages.addErrorsDatasetIsNotFound(GLOBAL, form.dataSetId), this::asListHtml);
        }

        return asStream(dataSet.getName()).contentTypeOctetStream()
                .stream(out -> projectHelper.writeDataSet(getSessionKey(), form.projectId, dataSet, out));
    }

    @Execute
    @Secured({ ROLE })
    public HtmlResponse deletedataset(final PredictDataSetForm form) {
        validate(form, messages -> {}, () -> redirectSummaryHtml(form.projectId, form.dataSetId, form.leaderboardId));
        verifyTokenKeep(() -> redirectSummaryHtml(form.projectId, form.dataSetId, form.leaderboardId));
        try {
            projectHelper.deleteDataSet(getSessionKey(), form.projectId, form.dataSetId);
            saveMessage(messages -> messages.addSuccessDeletingDataset(GLOBAL, form.dataSetId));
        } catch (final Exception e) {
            logger.warn("Failed to delete data: {}", form.dataSetId, e);
            throw validationError(messages -> messages.addErrorsFailedToDeleteDataset(GLOBAL, form.dataSetId), this::asListHtml);
        }
        return redirectSummaryHtml(form.projectId, null, form.leaderboardId);
    }

    // ===================================================================================
    //                                                                              JSP
    //                                                                           =========

    private HtmlResponse asListHtml() {
        return asHtml(path_AdminEasyml_AdminEasymlDatasetJsp).renderWith(data -> {
            RenderDataUtil.register(data, "projects", projectHelper.getProjects());
        }).useForm(DataSetForm.class);
    }

    private HtmlResponse asJobHtml(final Project project) {
        return asHtml(path_AdminEasyml_AdminEasymlJobJsp).renderWith(data -> {
            RenderDataUtil.register(data, "project", project);
        });
    }

    private HtmlResponse asTrainHtml(final String projectId, final String dataSetId) {
        saveToken();
        final var sessionKey = getSessionKey();
        final var project = projectHelper.getProject(sessionKey, projectId);
        if (project == null) {
            throw validationError(messages -> messages.addErrorsProjectIsNotFound(GLOBAL, projectId), this::asListHtml);
        }
        final var dataSet = projectHelper.getDataSet(projectId, dataSetId);
        if (dataSet == null) {
            throw validationError(messages -> messages.addErrorsDatasetIsNotFound(GLOBAL, StringCodecUtil.decode(dataSetId)),
                    this::asListHtml);
        }
        final var schema = dataSet.getSchema();
        if (schema == null) {
            throw validationError(messages -> messages.addErrorsDatasetSchemaIsNotFound(GLOBAL, StringCodecUtil.decode(dataSetId)),
                    this::asListHtml);
        }
        final var frameId = projectHelper.getFrameName(projectId, dataSetId) + ".hex";
        final var columnSummaries = projectHelper.getColumnSummaries(sessionKey, projectId, frameId);
        return asHtml(path_AdminEasyml_AdminEasymlTrainJsp).useForm(TrainForm.class, setup -> {
            setup.setup(form -> {
                form.projectId = projectId;
                form.dataSetId = dataSetId;
                form.frameId = frameId;
                for (final ColV3 column : columnSummaries.columns) {
                    final var id = StringCodecUtil.encodeUrlSafe(column.label);
                    if (!column.label.toLowerCase(Locale.ROOT).endsWith("id")) {
                        form.columns.put(id, "on");
                        if (form.responseColumn == null) {
                            if ("int".equals(column.type)) {
                                if (column.mean > 0.0f && column.mean < 1.0f) {
                                    form.responseColumn = StringCodecUtil.encodeUrlSafe(column.label);
                                    form.predictionType = Constants.REGRESSION_TYPE;
                                }
                            } else if ("enum".equals(column.type) && (column.domainCardinality < 10)) {
                                form.responseColumn = StringCodecUtil.encodeUrlSafe(column.label);
                                if (column.domainCardinality > 2) {
                                    form.predictionType = Constants.MULTICLASS_TYPE;
                                } else {
                                    form.predictionType = Constants.BINARYCLASS_TYPE;
                                }
                            }
                        }
                    }
                    form.columnTypes.put(id, column.type);
                }
            });
        }).renderWith(data -> {
            RenderDataUtil.register(data, "project", project);
            registerColumnItems(schema, data, (maps, i) -> {
                if (i.intValue() < columnSummaries.columns.length) {
                    final var column = columnSummaries.columns[i];
                    maps.$("missing", Long.toString(column.missingCount));
                    maps.$("min", column.mins != null && column.mins.length > 0 ? Double.toString(column.mins[0]) : StringUtil.EMPTY);
                    maps.$("max", column.maxs != null && column.maxs.length > 0 ? Double.toString(column.maxs[0]) : StringUtil.EMPTY);
                    maps.$("mean", Double.toString(column.mean));
                    maps.$("cardinality", Integer.toString(column.domainCardinality));
                }
                return maps;
            });
            registerColumnTypeItems(data);
        });
    }

    private Map<String, Object> getPredictionMetric(final String responseColumn, final FrameV3 columnSummaries,
            final LeaderboardV99 leaderboard) {
        final Map<String, Object> params = new HashMap<>();
        if (leaderboard.models == null || leaderboard.models.length == 0) {
            params.put("name", "Unknown");
            params.put("value", Double.NaN);
            params.put("accuracy", 0.0f);
            return params;
        }
        switch (leaderboard.sortMetric) {
        case "auc":
            params.put("name", "AUC");
            if (leaderboard.sortMetrics.length > 0) {
                params.put("value", leaderboard.sortMetrics[0]);
                final var accuracy = leaderboard.sortMetrics[0] * 2.0f - 1.0f;
                params.put("accuracy", Math.max(accuracy, 0.0f));
            } else {
                params.put("value", Double.NaN);
                params.put("accuracy", 0.0f);
            }
            return params;
        case "mean_per_class_error":
            params.put("name", "MPCE");
            if (leaderboard.sortMetrics.length > 0) {
                params.put("value", leaderboard.sortMetrics[0]);
                // TODO improve the following value...
                final var accuracy = (1.0f - leaderboard.sortMetrics[0]) * 2.0f - 1.0f;
                params.put("accuracy", Math.max(accuracy, 0.0f));
            } else {
                params.put("value", Double.NaN);
                params.put("accuracy", 0.0f);
            }
            return params;
        case "mean_residual_deviance":
            final var modelMetric = getTopModelMetric(leaderboard);
            if (modelMetric.containsKey("rmse") && modelMetric.containsKey("mae")) {
                params.put("name", "RMSE");
                params.put("value", modelMetric.get("rmse"));
                final var mean = getResponseColumnMean(responseColumn, columnSummaries);
                if (mean != null) {
                    final var mae = (Number) modelMetric.get("mae");
                    // TODO improve the following value...
                    params.put("accuracy", ((mean.doubleValue() - mae.doubleValue()) / mean.doubleValue() - 0.5f) * 2);
                } else {
                    params.put("accuracy", 0.0f);
                }
                return params;
            }
        default:
            params.put("name", leaderboard.sortMetric);
            params.put("accuracy", 0.0f);
            if (leaderboard.sortMetrics.length > 0) {
                params.put("value", leaderboard.sortMetrics[0]);
            } else {
                params.put("value", Double.NaN);
            }
            return params;
        }
    }

    private Map<String, Object> getTopModelMetric(final LeaderboardV99 leaderboard) {
        final Map<String, Object> params = new HashMap<>();
        for (var i = 0; i < leaderboard.table.columns.length; i++) {
            params.put(leaderboard.table.columns[i].name, leaderboard.table.data[i][0]);
        }
        return params;
    }

    private Double getResponseColumnMean(final String responseColumn, final FrameV3 columnSummaries) {
        for (final ColV3 col : columnSummaries.columns) {
            if (responseColumn.equals(col.label)) {
                return col.mean;
            }
        }
        return null;
    }

    private HtmlResponse asSummaryHtml(final String projectId, final String dataSetId, final String leaderboardId) {
        final var token = doubleSubmitManager.saveToken(myTokenGroupType());
        final var sessionKey = getSessionKey();
        final var project = projectHelper.getProject(sessionKey, projectId);
        if (project == null) {
            throw validationError(messages -> messages.addErrorsProjectIsNotFound(GLOBAL, projectId), this::asListHtml);
        }
        final var dataSet = projectHelper.getDataSet(projectId, dataSetId);
        if (dataSet == null) {
            throw validationError(messages -> messages.addErrorsDatasetIsNotFound(GLOBAL, StringCodecUtil.decode(dataSetId)),
                    this::asListHtml);
        }
        final var schema = dataSet.getSchema();
        if (schema == null) {
            throw validationError(messages -> messages.addErrorsDatasetSchemaIsNotFound(GLOBAL, StringCodecUtil.decode(dataSetId)),
                    this::asListHtml);
        }
        final var frameId = projectHelper.getFrameName(projectId, dataSetId) + ".hex";
        final var columnSummaries = projectHelper.getColumnSummaries(sessionKey, projectId, frameId);
        final var leaderboard = projectHelper.getLeaderboard(sessionKey, projectId, leaderboardId);
        if (leaderboard == null) {
            throw validationError(messages -> messages.addErrorsLeaderboardIsNotFound(GLOBAL), this::asListHtml);
        }
        return asHtml(path_AdminEasyml_AdminEasymlSummaryJsp).useForm(SummaryForm.class, setup -> {
            setup.setup(form -> {
                form.projectId = projectId;
                form.dataSetId = dataSetId;
                form.frameId = frameId;
            });
        }).renderWith(data -> {
            RenderDataUtil.register(data, "token", token);
            RenderDataUtil.register(data, "project", project);
            RenderDataUtil.register(data, "projectId", projectId);
            RenderDataUtil.register(data, "frameId", frameId);
            RenderDataUtil.register(data, "dataSetId", dataSetId);
            RenderDataUtil.register(data, "dataSets",
                    Arrays.stream(project.getDataSets()).filter(d -> DataSet.PREDICT.equals(d.getType())).toArray(n -> new DataSet[n]));
            RenderDataUtil.register(data, "leaderboardId", leaderboardId);
            RenderDataUtil.register(data, "columnSummaries", columnSummaries);
            RenderDataUtil.register(data, "leaderboard", leaderboard);
            final var responseColumn = getResponseColumn(leaderboard.projectName);
            RenderDataUtil.register(data, "responseColumn", responseColumn);
            RenderDataUtil.register(data, "predictionMetric", getPredictionMetric(responseColumn, columnSummaries, leaderboard));
        });
    }

    private HtmlResponse asPredictionHtml(final String projectId, final String dataSetId, final String leaderboardId) {
        final var sessionKey = getSessionKey();
        final var project = projectHelper.getProject(sessionKey, projectId);
        if (project == null) {
            throw validationError(messages -> messages.addErrorsProjectIsNotFound(GLOBAL, projectId), this::asListHtml);
        }
        final var leaderboard = projectHelper.getLeaderboard(sessionKey, projectId, leaderboardId);
        final String responseColumn;
        final String modelName;
        if (leaderboard != null) {
            responseColumn = getResponseColumn(leaderboard.projectName);
            if (leaderboard.models != null && leaderboard.models.length > 0) {
                modelName = "predict_" + leaderboard.models[0].name;
            } else {
                modelName = "predict_" + new SimpleDateFormat("yyyyMMddHHmmss").format(systemHelper.getCurrentTime());
            }
        } else {
            responseColumn = null;
            modelName = "predict_" + new SimpleDateFormat("yyyyMMddHHmmss").format(systemHelper.getCurrentTime());
        }
        return asHtml(path_AdminEasyml_AdminEasymlPredictJsp).useForm(UploadPredictionForm.class, setup -> setup.setup(form -> {
            form.projectId = projectId;
            form.dataSetId = dataSetId;
            form.leaderboardId = leaderboardId;
            form.name = modelName;
        })).renderWith(data -> {
            RenderDataUtil.register(data, "project", project);
            final List<Map<String, String>> columnList = new ArrayList<>();
            final var dataSet = project.getDataSet(dataSetId);
            if (dataSet != null) {
                final var schema = dataSet.getSchema();
                if (schema != null) {
                    Arrays.stream(schema.getAvailableColumnNames()).filter(s -> !s.equals(responseColumn))
                            .forEach(s -> columnList.add(Maps.map("label", s).$("value", StringCodecUtil.encodeUrlSafe(s)).$()));
                }
            }
            RenderDataUtil.register(data, "columnItems", columnList);
        });
    }

    private HtmlResponse redirectJobHtml(final String projectId) {
        final var moreUrl = moreUrl("job", projectId);
        return redirectWith(getClass(), moreUrl);
    }

    private HtmlResponse redirectTrainHtml(final String projectId, final String dataSetId) {
        final var moreUrl = moreUrl("train", projectId).params(DATASET_ID, dataSetId);
        return redirectWith(getClass(), moreUrl);
    }

    private HtmlResponse redirectSummaryHtml(final String projectId, final String dataSetId, final String leaderboardId) {
        if (dataSetId == null || leaderboardId == null) {
            final var project = projectHelper.getProject(getSessionKey(), projectId);
            if (project == null) {
                throw validationError(messages -> messages.addErrorsProjectIsNotFound(GLOBAL, projectId), this::asListHtml);
            }
            return asJobHtml(project);
        }
        final var moreUrl = moreUrl("summary", projectId).params(DATASET_ID, dataSetId, LEADERBOARD_ID, leaderboardId);
        return redirectWith(getClass(), moreUrl);
    }

}
