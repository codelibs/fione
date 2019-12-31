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
import java.util.Arrays;

import javax.annotation.Resource;

import org.apache.commons.codec.binary.Base64;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.codelibs.fess.annotation.Secured;
import org.codelibs.fess.app.web.admin.user.SearchForm;
import org.codelibs.fess.crawler.Constants;
import org.codelibs.fess.util.RenderDataUtil;
import org.codelibs.fione.app.web.base.FioneAdminAction;
import org.codelibs.fione.entity.DataSet;
import org.codelibs.fione.entity.DataSet.Status;
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
import org.codelibs.fione.h2o.bindings.pojos.ScoreKeeperStoppingMetric;
import org.codelibs.fione.helper.ProjectHelper;
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
    public HtmlResponse createproject(final NewProjectForm form) {
        validate(form, messages -> {}, this::asNewProjectHtml);
        verifyToken(this::asNewProjectHtml);
        final Project project = new Project(Base64.encodeBase64URLSafeString(form.name.getBytes(Constants.UTF_8_CHARSET)));
        project.setName(form.name);
        try {
            projectHelper.store(project);
            saveInfo(messages -> messages.addSuccessCrudCreateCrudTable(GLOBAL));
        } catch (final Exception e) {
            logger.error("Failed to add " + project.getId(), e);
            throwValidationError(messages -> messages.addErrorsCrudFailedToCreateCrudTable(GLOBAL, buildThrowableMessage(e)),
                    () -> asNewProjectHtml());
        }
        return redirectWith(getClass(), moreUrl("details", project.getId()));
    }

    @Execute
    @Secured({ ROLE, ROLE + VIEW })
    public HtmlResponse details(final String projectId) {
        saveToken();
        try {
            final Project project = projectHelper.getProject(projectId);
            final DataSet targetDataSet = LaRequestUtil.getOptionalRequest().map(req -> {
                final String dataSetId = req.getParameter("dataSetId");
                if (dataSetId != null) {
                    for (final DataSet dataSet : project.getDataSets()) {
                        if (dataSetId.equals(dataSet.getId())) {
                            return dataSet;
                        }
                    }
                }
                if (project.getDataSets().length > 0) {
                    return project.getDataSets()[0];
                }
                return null;
            }).get();

            return asHtml(path_AdminAutoml_AdminAutomlDetailsJsp).renderWith(data -> {
                RenderDataUtil.register(data, "project", project);
                RenderDataUtil.register(data, "dataSet", targetDataSet);
                if (targetDataSet.getStatus() == Status.PARSED) {
                    final FrameV3 columnSummaries = projectHelper.getColumnSummaries(targetDataSet);
                    RenderDataUtil.register(data, "columnSummaries", columnSummaries);
                }
            });
        } catch (final Exception e) {
            logger.error("Failed to read " + projectId, e);
            throwValidationError(messages -> messages.addErrorsCrudFailedToCreateCrudTable(GLOBAL, buildThrowableMessage(e)),
                    () -> asNewProjectHtml()); // TODO fix a message
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
        validate(form, messages -> {}, this::asNewProjectHtml);
        try (InputStream in = form.dataFile.getInputStream()) {
            projectHelper.addDataSet(form.id, form.dataFile.getFileName(), in);
            saveInfo(messages -> messages.addSuccessCrudCreateCrudTable(GLOBAL));
        } catch (final Exception e) {
            logger.error("Failed to add " + form.dataFile.getFileName(), e);
            throwValidationError(messages -> messages.addErrorsCrudFailedToCreateCrudTable(GLOBAL, buildThrowableMessage(e)),
                    () -> asNewDataHtml(form.id));// TODO fix a message
        }
        return redirectWith(getClass(), moreUrl("details", form.id));
    }

    @Execute
    @Secured({ ROLE })
    public HtmlResponse importfile(final String projectId, final String dataSetId) {
        try {
            projectHelper.importFile(projectId, dataSetId);
            saveInfo(messages -> messages.addSuccessCrudCreateCrudTable(GLOBAL));
        } catch (final Exception e) {
            logger.error("Failed to import {} in {}", dataSetId, projectId, e);
            throwValidationError(messages -> messages.addErrorsCrudFailedToCreateCrudTable(GLOBAL, buildThrowableMessage(e)),
                    () -> asNewDataHtml(projectId));// TODO fix a message
        }
        return redirectWith(getClass(), moreUrl("details", projectId));
    }

    @Execute
    @Secured({ ROLE })
    public HtmlResponse parsedata(final String projectId, final String dataSetId) {
        try {
            projectHelper.parseData(projectId, dataSetId);
            saveInfo(messages -> messages.addSuccessCrudCreateCrudTable(GLOBAL));
        } catch (final Exception e) {
            logger.error("Failed to parse {} in {}", dataSetId, projectId, e);
            throwValidationError(messages -> messages.addErrorsCrudFailedToCreateCrudTable(GLOBAL, buildThrowableMessage(e)),
                    () -> asNewDataHtml(projectId));// TODO fix a message
        }
        return redirectWith(getClass(), moreUrl("details", projectId));
    }

    @Execute
    @Secured({ ROLE })
    public HtmlResponse setupml(final String projectId, final String dataSetId) {
        saveToken();
        return asSetupMlHtml(projectId, dataSetId);
    }

    @Execute
    @Secured({ ROLE })
    public HtmlResponse runautoml(final RunSettingForm form) {
        validate(form, messages -> {}, this::asNewProjectHtml);
        verifyToken(this::asNewProjectHtml);

        final Project project = projectHelper.getProject(form.projectId);
        // TODO null check
        final DataSet dataSet = project.getDataSet(form.dataSetId);
        // TODO null check

        final AutoMLBuildControlV99 buildControl =
                AutoMLBuildControlBuilder
                        .create()
                        .projectName(project.getName())
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
                AutoMLInputBuilder.create().trainingFrame(dataSet.getMeta().destinationFrame).responseColumn(form.responseColumn, null)
                        .sortMetric(Automlapischemas3AutoMLBuildSpecAutoMLMetricProvider.valueOf(form.sortMetric)).build();
        final AutoMLBuildModelsV99 buildModels = AutoMLBuildModelsBuilder.create().build();

        try {
            projectHelper.runAutoML(project, buildControl, input, buildModels);
            saveInfo(messages -> messages.addSuccessCrudCreateCrudTable(GLOBAL));
        } catch (final Exception e) {
            logger.error("Failed to run AutoML.", e);
            throwValidationError(messages -> messages.addErrorsCrudFailedToCreateCrudTable(GLOBAL, buildThrowableMessage(e)),
                    () -> asSetupMlHtml(form.projectId, form.dataSetId));// TODO fix a message
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
        return asHtml(path_AdminAutoml_AdminAutomlNewprojectJsp).useForm(NewProjectForm.class);
    }

    private HtmlResponse asNewDataHtml(final String projectId) {
        return asHtml(path_AdminAutoml_AdminAutomlNewdataJsp).useForm(UploadDataSetForm.class, setup -> {
            setup.setup(form -> {
                form.id = projectId;
            });
        });
    }

    private HtmlResponse asSetupMlHtml(final String projectId, final String dataSetId) {
        final DataSet dataSet = projectHelper.getDataSet(projectId, dataSetId);
        if (dataSet.getStatus() != Status.PARSED) {
            // TODO message
            return redirectWith(getClass(), moreUrl("details", projectId));
        }

        return asHtml(path_AdminAutoml_AdminAutomlRunmlJsp).useForm(RunSettingForm.class, setup -> {
            setup.setup(form -> {
                form.projectId = projectId;
                form.dataSetId = dataSetId;
            });
        }).renderWith(
                data -> {
                    RenderDataUtil.register(data, "columnItems", dataSet.getMeta().columnNames);
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
