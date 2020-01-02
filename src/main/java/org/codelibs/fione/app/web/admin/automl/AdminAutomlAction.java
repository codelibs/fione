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

import java.io.InputStream;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Map;

import javax.annotation.Resource;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.codelibs.core.collection.Maps;
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
import org.codelibs.fione.h2o.bindings.pojos.AutoMLInputV99;
import org.codelibs.fione.h2o.bindings.pojos.Automlapischemas3AutoMLBuildSpecAutoMLMetricProvider;
import org.codelibs.fione.h2o.bindings.pojos.FrameV3;
import org.codelibs.fione.h2o.bindings.pojos.ParseV3;
import org.codelibs.fione.h2o.bindings.pojos.ScoreKeeperStoppingMetric;
import org.codelibs.fione.helper.ProjectHelper;
import org.codelibs.fione.util.StringCodecUtil;
import org.lastaflute.web.Execute;
import org.lastaflute.web.response.HtmlResponse;
import org.lastaflute.web.ruts.process.ActionRuntime;
import org.lastaflute.web.util.LaRequestUtil;

/**
 * @author shinsuke
 */
public class AdminAutomlAction extends FioneAdminAction {

    public static final String ROLE = "admin-automl";

    private static final Logger logger = LogManager.getLogger(AdminAutomlAction.class);

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
        runtime.registerData("helpLink", systemHelper.getHelpLink("automl"));
    }

    @Override
    protected String getActionRole() {
        return ROLE;
    }

    // ===================================================================================
    //                                                                      Search Execute
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
        // TODO check if project exists projectHelper.projectExists(form.projectId)
        final Project project = new Project(StringCodecUtil.encodeUrlSafe(form.name));
        project.setName(form.name);
        try {
            projectHelper.store(project);
            saveInfo(messages -> messages.addSuccessCrudCreateCrudTable(GLOBAL));// TODO create project
        } catch (final Exception e) {
            logger.error("Failed to add " + project.getId(), e);
            throwValidationError(messages -> messages.addErrorsCrudFailedToCreateCrudTable(GLOBAL, buildThrowableMessage(e)),
                    () -> asNewProjectHtml()); // TODO failed to create a new project
        }
        return redirectWith(getClass(), moreUrl("details", project.getId()));
    }

    @Execute
    @Secured({ ROLE, ROLE + VIEW })
    public HtmlResponse details(final String projectId) {
        saveToken();
        try {
            final Project project = projectHelper.getProject(projectId);
            final String frameId = LaRequestUtil.getOptionalRequest().map(req -> {
                final String fid = req.getParameter("frameId");
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

            return asHtml(path_AdminAutoml_AdminAutomlDetailsJsp).renderWith(data -> {
                RenderDataUtil.register(data, "project", project);
                RenderDataUtil.register(data, "frameId", frameId);
                if (frameId != null) {
                    final FrameV3 columnSummaries = projectHelper.getColumnSummaries(frameId);
                    RenderDataUtil.register(data, "columnSummaries", columnSummaries);
                }
            });
        } catch (final Exception e) {
            logger.error("Failed to read " + projectId, e);
            throwValidationError(messages -> messages.addErrorsCrudFailedToCreateCrudTable(GLOBAL, buildThrowableMessage(e)),
                    () -> asListHtml()); // TODO Failed to load project {0}
        }
        return redirect(getClass()); // not invoked
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
            projectHelper.addDataSet(form.projectId, fileName, in);
            saveInfo(messages -> messages.addSuccessCrudCreateCrudTable(GLOBAL)); // TODO uploaded {0}
        } catch (final Exception e) {
            logger.error("Failed to add " + form.dataFile.getFileName(), e);
            throwValidationError(messages -> messages.addErrorsCrudFailedToCreateCrudTable(GLOBAL, buildThrowableMessage(e)),
                    () -> asNewDataHtml(form.projectId));// TODO failed to upload {0}
        }
        return redirectWith(getClass(), moreUrl("details", form.projectId));
    }

    @Execute
    @Secured({ ROLE })
    public HtmlResponse deletedataset(final String projectId, final String dataSetId) {
        // TODO validate(form, messages -> {}, () -> as...());
        // TODO verifyToken(() -> as...());
        try {
            projectHelper.deleteDataSet(projectId, dataSetId);
            saveInfo(messages -> messages.addSuccessCrudCreateCrudTable(GLOBAL));// TODO deleting data {0}
        } catch (final Exception e) {
            logger.error("Failed to delete data: {}", dataSetId, e);
            throwValidationError(messages -> messages.addErrorsCrudFailedToCreateCrudTable(GLOBAL, buildThrowableMessage(e)),
                    () -> asListHtml()); // TODO failed to delete data {0}
        }
        return redirectWith(getClass(), moreUrl("details", projectId));
    }

    @Execute
    @Secured({ ROLE })
    public HtmlResponse newframe(final String projectId, final String dataSetId) {
        saveToken();
        return asNewFrameaHtml(projectId, dataSetId);
    }

    @Execute
    @Secured({ ROLE })
    public HtmlResponse createframe(final CreateFrameForm form) {
        validate(form, messages -> {}, () -> asNewFrameaHtml(form.projectId, form.dataSetId));
        verifyToken(() -> asNewFrameaHtml(form.projectId, form.dataSetId));
        final DataSet dataSet = projectHelper.getDataSet(form.projectId, form.dataSetId);
        // TODO check if dataSet exists
        final ParseV3 schema = dataSet.getSchema();
        for (int i = 0; i < schema.columnNames.length; i++) {
            final String value = form.columns.get(StringCodecUtil.encodeUrlSafe(schema.columnNames[i]));
            if (StringUtil.isNotBlank(value)) {
                schema.columnTypes[i] = value;
            }
        }
        try {
            projectHelper.createFrame(form.projectId, dataSet);
            saveInfo(messages -> messages.addSuccessCrudCreateCrudTable(GLOBAL));// TODO loading a new frame
        } catch (final Exception e) {
            logger.error("Failed to create frame: {}", dataSet, e);
            throwValidationError(messages -> messages.addErrorsCrudFailedToCreateCrudTable(GLOBAL, buildThrowableMessage(e)),
                    () -> asNewFrameaHtml(form.projectId, form.dataSetId)); // TODO failed to create a new frame
        }
        return redirectWith(getClass(), moreUrl("details", form.projectId));
    }

    @Execute
    @Secured({ ROLE })
    public HtmlResponse deleteframe(final String projectId, final String frameId) {
        // TODO validate(form, messages -> {}, () -> as...());
        // TODO verifyToken(() -> as...());
        try {
            projectHelper.deleteFrame(frameId);
            saveInfo(messages -> messages.addSuccessCrudCreateCrudTable(GLOBAL));// TODO Deleted frame {0}
        } catch (final Exception e) {
            logger.error("Failed to delete frame: {}", frameId, e);
            throwValidationError(messages -> messages.addErrorsCrudFailedToCreateCrudTable(GLOBAL, buildThrowableMessage(e)),
                    () -> asListHtml()); // TODO failed to delete frame {0}
        }
        return redirectWith(getClass(), moreUrl("details", projectId));
    }

    @Execute
    @Secured({ ROLE })
    public HtmlResponse deletejob(final String projectId, final String jobId) {
        // TODO validate(form, messages -> {}, () -> as...());
        // TODO verifyToken(() -> as...());
        try {
            projectHelper.deleteJob(projectId, jobId);
            saveInfo(messages -> messages.addSuccessCrudCreateCrudTable(GLOBAL));// TODO Deleted job {0}
        } catch (final Exception e) {
            logger.error("Failed to delete frame: {}", jobId, e);
            throwValidationError(messages -> messages.addErrorsCrudFailedToCreateCrudTable(GLOBAL, buildThrowableMessage(e)),
                    () -> asListHtml()); // TODO failed to delete job {0}
        }
        return redirectWith(getClass(), moreUrl("details", projectId));
    }

    @Execute
    @Secured({ ROLE })
    public HtmlResponse loaddataset(final String projectId, final String dataSetId) {
        // TODO validate(form, messages -> {}, () -> as...());
        // TODO verifyToken(() -> as...());
        try {
            final DataSet dataSet = projectHelper.getDataSet(projectId, dataSetId);
            // TODO check if dataSet exists
            projectHelper.loadDataSetSchema(projectId, dataSet);
            saveInfo(messages -> messages.addSuccessCrudCreateCrudTable(GLOBAL));// TODO load data {0}
        } catch (final Exception e) {
            logger.error("Failed to load {} in {}.", dataSetId, projectId, e);
            throwValidationError(messages -> messages.addErrorsCrudFailedToCreateCrudTable(GLOBAL, buildThrowableMessage(e)),
                    () -> asListHtml()); // TODO failed to load data {0}
        }
        return redirectWith(getClass(), moreUrl("details", projectId));
    }

    @Execute
    @Secured({ ROLE })
    public HtmlResponse setupml(final String projectId, final String frameId) {
        saveToken();
        return asSetupMlHtml(projectId, frameId);
    }

    @Execute
    @Secured({ ROLE })
    public HtmlResponse runautoml(final RunSettingForm form) {
        validate(form, messages -> {}, this::asNewProjectHtml);
        verifyToken(this::asNewProjectHtml);

        final Project project = projectHelper.getProject(form.projectId);
        // TODO null check

        final String projectName = StringCodecUtil.normalize(project.getName());
        final AutoMLBuildControlV99 buildControl =
                AutoMLBuildControlBuilder
                        .create()
                        .projectName(projectName)
                        .nfolds(5)
                        .balanceClasses(Boolean.valueOf(form.balanceClasses))
                        .stoppingCriteria(
                                AutoMLStoppingCriteriaBuilder.create().seed(form.seed).maxModels(form.maxModels)
                                        .maxRuntimeSecs(form.maxRuntimeSecs).maxRuntimeSecsPerModel(form.maxRuntimeSecsPerModel)
                                        .stoppingRounds(form.stoppingRounds)
                                        .stoppingMetric(ScoreKeeperStoppingMetric.valueOf(form.stoppingMetric))
                                        .stoppingTolerance(Double.valueOf(form.stoppingTolerance)).build())
                        .keepCrossValidationPredictions(Boolean.valueOf(form.keepCrossValidationPredictions))
                        .keepCrossValidationModels(Boolean.valueOf(form.keepCrossValidationModels))
                        .keepCrossValidationFoldAssignment(Boolean.valueOf(form.keepCrossValidationFoldAssignment)).build();
        final AutoMLInputV99 input =
                AutoMLInputBuilder.create().trainingFrame(form.frameId).responseColumn(form.responseColumn, null)
                        .sortMetric(Automlapischemas3AutoMLBuildSpecAutoMLMetricProvider.valueOf(form.sortMetric)).build();
        final AutoMLBuildModelsV99 buildModels = AutoMLBuildModelsBuilder.create().build();

        try {
            projectHelper.runAutoML(form.projectId, buildControl, input, buildModels);
            saveInfo(messages -> messages.addSuccessCrudCreateCrudTable(GLOBAL));
        } catch (final Exception e) {
            logger.error("Failed to run AutoML.", e);
            throwValidationError(messages -> messages.addErrorsCrudFailedToCreateCrudTable(GLOBAL, buildThrowableMessage(e)),
                    () -> asSetupMlHtml(form.projectId, form.frameId));// TODO fix a message
        }
        return redirectWith(getClass(), moreUrl("details", form.projectId));
    }

    // ===================================================================================
    //                                                                              JSP
    //                                                                           =========

    private HtmlResponse asListHtml() {
        return asHtml(path_AdminAutoml_AdminAutomlJsp).renderWith(data -> {
            RenderDataUtil.register(data, "projects", projectHelper.getProjects());
        }).useForm(SearchForm.class);
    }

    private HtmlResponse asNewProjectHtml() {
        return asHtml(path_AdminAutoml_AdminAutomlNewprojectJsp).useForm(CreateProjectForm.class);
    }

    private HtmlResponse asNewDataHtml(final String projectId) {
        return asHtml(path_AdminAutoml_AdminAutomlNewdataJsp).useForm(UploadDataSetForm.class, setup -> {
            setup.setup(form -> {
                form.projectId = projectId;
            });
        });
    }

    private HtmlResponse asNewFrameaHtml(final String projectId, final String dataSetId) {
        final DataSet dataSet = projectHelper.getDataSet(projectId, dataSetId);
        // TODO check if dataSet is null
        final ParseV3 schema = dataSet.getSchema();
        // TODO check if schema is null
        return asHtml(path_AdminAutoml_AdminAutomlNewframeJsp).useForm(CreateFrameForm.class, setup -> {
            setup.setup(form -> {
                form.projectId = projectId;
                form.dataSetId = dataSetId;
            });
        }).renderWith(
                data -> {
                    final List<Map<String, String>> columnItems = new ArrayList<>();
                    for (int i = 0; i < schema.columnNames.length; i++) {
                        columnItems.add(Maps.map("id", StringCodecUtil.encodeUrlSafe(schema.columnNames[i]))
                                .$("name", schema.columnNames[i]).$("value", schema.columnTypes[i]).$());
                    }
                    RenderDataUtil.register(data, "columnItems", columnItems);
                    final List<Map<String, String>> columnTypeItems = new ArrayList<>();
                    columnTypeItems.add(Maps.map("label", "BAD").$("value", "BAD").$());
                    columnTypeItems.add(Maps.map("label", "UUID").$("value", "UUID").$());
                    columnTypeItems.add(Maps.map("label", "String").$("value", "String").$());
                    columnTypeItems.add(Maps.map("label", "Numeric").$("value", "Numeric").$());
                    columnTypeItems.add(Maps.map("label", "Enum").$("value", "Enum").$());
                    columnTypeItems.add(Maps.map("label", "Time").$("value", "Time").$());
                    RenderDataUtil.register(data, "columnTypeItems", columnTypeItems);
                });
    }

    private HtmlResponse asSetupMlHtml(final String projectId, final String frameId) {
        final FrameV3 columnSummaries = projectHelper.getColumnSummaries(frameId);

        return asHtml(path_AdminAutoml_AdminAutomlRunmlJsp).useForm(RunSettingForm.class, setup -> {
            setup.setup(form -> {
                form.projectId = projectId;
                form.frameId = frameId;
            });
        }).renderWith(
                data -> {
                    final String[] columnItems = Arrays.stream(columnSummaries.columns).map(c -> c.label).toArray(n -> new String[n]);
                    RenderDataUtil.register(data, "columnItems", columnItems);
                    RenderDataUtil.register(data, "stoppingMetricItems",
                            Arrays.stream(ScoreKeeperStoppingMetric.values()).map(v -> v.toString()).toArray(n -> new String[n]));
                    RenderDataUtil.register(
                            data,
                            "sortMetricItems",
                            Arrays.stream(Automlapischemas3AutoMLBuildSpecAutoMLMetricProvider.values()).map(v -> v.toString())
                                    .toArray(n -> new String[n]));

                });
    }
}
