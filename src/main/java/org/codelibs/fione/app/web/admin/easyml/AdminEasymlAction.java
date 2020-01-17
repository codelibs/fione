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
package org.codelibs.fione.app.web.admin.easyml;

import java.io.InputStream;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

import javax.annotation.Resource;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.codelibs.core.lang.StringUtil;
import org.codelibs.fess.annotation.Secured;
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
import org.codelibs.fione.h2o.bindings.pojos.ColV3;
import org.codelibs.fione.h2o.bindings.pojos.FrameKeyV3;
import org.codelibs.fione.h2o.bindings.pojos.FrameV3;
import org.codelibs.fione.h2o.bindings.pojos.JobV3;
import org.codelibs.fione.h2o.bindings.pojos.ParseV3;
import org.codelibs.fione.h2o.bindings.pojos.ScoreKeeperStoppingMetric;
import org.codelibs.fione.helper.ProjectHelper;
import org.codelibs.fione.util.StringCodecUtil;
import org.lastaflute.web.Execute;
import org.lastaflute.web.UrlChain;
import org.lastaflute.web.response.HtmlResponse;
import org.lastaflute.web.ruts.process.ActionRuntime;

public class AdminEasymlAction extends FioneAdminAction {

    public static final String ROLE = "admin-easyml";

    private static final Logger logger = LogManager.getLogger(AdminEasymlAction.class);

    // ===================================================================================
    //                                                                           Attribute
    //                                                                           =========

    @Resource
    private ProjectHelper projectHelper;

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
        final String projectId = StringCodecUtil.encodeUrlSafe(form.name);
        if (projectHelper.projectExists(projectId)) {
            throw validationError(messages -> messages.addErrorsProjectExists(GLOBAL, form.name), this::asListHtml);
        }
        final Project project = new Project(projectId);
        project.setName(form.name);
        try (InputStream in = form.file.getInputStream()) {
            projectHelper.store(project);
            final String fileName = StringCodecUtil.normalize(form.file.getFileName());
            projectHelper.addDataSet(project.getId(), fileName, in);
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
        final Project project = projectHelper.getProject(projectId);
        if (project == null) {
            return redirectWith(getClass(), moreUrl("dataset"));
        }
        for (final JobV3 job : project.getJobs()) {
            if ("RUNNING".equals(job.status)) {
                return asJobHtml(project);
            }
        }
        final DataSet[] dataSets = project.getDataSets();
        final DataSet dataSet = findDataSet(dataSets);
        if (dataSet == null) {
            // TODO no dataset
            return redirectWith(getClass(), moreUrl("dataset"));
        }
        if (dataSet.getSchema() == null) {
            projectHelper.loadDataSetSchema(projectId, dataSet);
            return asJobHtml(project);
        }
        final FrameV3 columnSummaries = getColumnSummaries(projectId, project);
        if (columnSummaries == null) {
            projectHelper.createFrame(projectId, dataSet, result -> {});
            return asJobHtml(project);
        }
        return redirectTrainHtml(projectId, dataSet.getId());
    }

    protected DataSet findDataSet(final DataSet[] dataSets) {
        if (dataSets == null || dataSets.length == 0) {
            return null;
        }
        for (final DataSet dataSet : dataSets) {
            if ("train".equals(dataSet.getType())) {
                return dataSet;
            }
        }
        return dataSets[0];
    }

    @Execute
    @Secured({ ROLE, ROLE + VIEW })
    public HtmlResponse train(final String projectId, final String dataSetId) {
        saveToken();
        return asTrainHtml(projectId, dataSetId);
    }

    @Execute
    @Secured({ ROLE })
    public HtmlResponse runautoml(final TrainForm form) {
        validate(form, messages -> {}, () -> asTrainHtml(form.projectId, form.dataSetId));
        verifyToken(() -> asTrainHtml(form.projectId, form.dataSetId));

        final Project project = projectHelper.getProject(form.projectId);
        if (project == null) {
            throw validationError(messages -> messages.addErrorsProjectIsNotFound(GLOBAL, form.projectId), this::asListHtml);
        }
        final DataSet dataSet = projectHelper.getDataSet(form.projectId, form.dataSetId);
        if (dataSet == null) {
            throw validationError(messages -> messages.addErrorsDatasetIsNotFound(GLOBAL, form.dataSetId), this::asListHtml);
        }
        final ParseV3 schema = dataSet.getSchema();
        if (schema == null) {
            throw validationError(messages -> messages.addErrorsDatasetSchemaIsNotFound(GLOBAL, form.dataSetId), this::asListHtml);
        }
        final Map<String, String> columnMap = new HashMap<>();
        for (int i = 0; i < schema.columnNames.length; i++) {
            columnMap.put(schema.columnNames[i], schema.columnTypes[i]);
        }
        form.columnTypes.entrySet().forEach(e -> columnMap.put(StringCodecUtil.decode(e.getKey()), e.getValue()));
        schema.columnNames =
                form.columns.entrySet().stream().filter(e -> StringUtil.isNotBlank(e.getValue()))
                        .map(e -> StringCodecUtil.decode(e.getKey())).toArray(n -> new String[n]);
        schema.columnTypes =
                Arrays.stream(schema.columnNames).map(s -> columnMap.containsKey(s) ? columnMap.get(s) : "String")
                        .toArray(n -> new String[n]);
        schema.numberColumns = schema.columnNames.length;
        final String trainFrameId = "easyml_" + form.frameId;
        schema.destinationFrame = new FrameKeyV3(trainFrameId);

        projectHelper.createFrame(
                form.projectId,
                dataSet,
                result -> {
                    final String projectName = StringCodecUtil.normalize(StringCodecUtil.decode(form.projectId));
                    final String responseColumn = StringCodecUtil.decode(form.responseColumn);

                    final AutoMLBuildControlV99 buildControl =
                            AutoMLBuildControlBuilder
                                    .create()
                                    .projectName(projectName)
                                    .nfolds(form.nfolds)
                                    .balanceClasses(Boolean.valueOf(form.balanceClasses))
                                    .stoppingCriteria(
                                            AutoMLStoppingCriteriaBuilder.create().seed(form.seed).maxModels(form.maxModels)
                                                    .maxRuntimeSecs(form.maxRuntimeSecs)
                                                    .maxRuntimeSecsPerModel(form.maxRuntimeSecsPerModel)
                                                    .stoppingRounds(form.stoppingRounds)
                                                    .stoppingMetric(ScoreKeeperStoppingMetric.valueOf(form.stoppingMetric))
                                                    .stoppingTolerance(form.stoppingTolerance).build())
                                    .keepCrossValidationPredictions(Boolean.valueOf(form.keepCrossValidationPredictions))
                                    .keepCrossValidationModels(Boolean.valueOf(form.keepCrossValidationModels))
                                    .keepCrossValidationFoldAssignment(Boolean.valueOf(form.keepCrossValidationFoldAssignment)).build();
                    final AutoMLInputV99 input =
                            AutoMLInputBuilder.create().trainingFrame(trainFrameId).responseColumn(responseColumn, null)
                                    .ignoredColumns(null)
                                    .sortMetric(Automlapischemas3AutoMLBuildSpecAutoMLMetricProvider.valueOf(form.sortMetric)).build();
                    final List<AutoMLCustomParameterV99> argParamList = new ArrayList<>();
                    argParamList.add(new AutoMLCustomParameterV99(Automlapischemas3AutoMLBuildSpecScopeProvider.DeepLearning,
                            "max_categorical_features", form.maxCategoricalFeatures));
                    final AutoMLBuildModelsV99 buildModels =
                            AutoMLBuildModelsBuilder.create().algoParameters(argParamList.toArray(n -> new AutoMLCustomParameterV99[n]))
                                    .build();

                    projectHelper.runAutoML(form.projectId, buildControl, input, buildModels);
                });

        return asJobHtml(project);
    }

    private FrameV3 getColumnSummaries(final String projectId, final Project project) {
        for (final String frameId : project.getFrameIds()) {
            final FrameV3 columnSummaries = projectHelper.getColumnSummaries(projectId, frameId);
            if (columnSummaries != null) {
                return columnSummaries;
            }
        }
        return null;
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
        final String frameId = projectHelper.getFrameName(projectId, dataSetId) + ".hex";
        final FrameV3 columnSummaries = projectHelper.getColumnSummaries(projectId, frameId);
        return asHtml(path_AdminEasyml_AdminEasymlTrainJsp).useForm(TrainForm.class, setup -> {
            setup.setup(form -> {
                form.projectId = projectId;
                form.dataSetId = dataSetId;
                form.frameId = frameId;
                for (final ColV3 column : columnSummaries.columns) {
                    final String id = StringCodecUtil.encodeUrlSafe(column.label);
                    if (!column.label.toLowerCase(Locale.ROOT).endsWith("id")) {
                        form.columns.put(id, "on");
                        if (form.responseColumn == null) {
                            if ("int".equals(column.type)) {
                                if (column.mean > 0.0f && column.mean < 1.0f) {
                                    form.responseColumn = StringCodecUtil.encodeUrlSafe(column.label);
                                }
                            } else if ("enum".equals(column.type)) {
                                if (column.domainCardinality < 10) {
                                    form.responseColumn = StringCodecUtil.encodeUrlSafe(column.label);
                                }
                            }
                        }
                    }
                    form.columnTypes.put(id, column.type);
                }
            });
        }).renderWith(data -> {
            registerColumnItems(schema, data, (maps, i) -> {
                if (i.intValue() < columnSummaries.columns.length) {
                    final ColV3 column = columnSummaries.columns[i.intValue()];
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

    private HtmlResponse redirectJobHtml(final String projectId) {
        final UrlChain moreUrl = moreUrl("job", projectId);
        return redirectWith(getClass(), moreUrl);
    }

    private HtmlResponse redirectTrainHtml(final String projectId, final String datasetId) {
        final UrlChain moreUrl = moreUrl("train", projectId, datasetId);
        return redirectWith(getClass(), moreUrl);
    }
}
