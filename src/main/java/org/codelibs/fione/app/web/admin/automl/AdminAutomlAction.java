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

import javax.annotation.Resource;

import org.apache.commons.codec.binary.Base64;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.codelibs.fess.annotation.Secured;
import org.codelibs.fess.app.web.admin.user.SearchForm;
import org.codelibs.fess.crawler.Constants;
import org.codelibs.fess.util.RenderDataUtil;
import org.codelibs.fione.app.web.base.FioneAdminAction;
import org.codelibs.fione.entity.Project;
import org.codelibs.fione.helper.ProjectHelper;
import org.lastaflute.web.Execute;
import org.lastaflute.web.response.HtmlResponse;
import org.lastaflute.web.ruts.process.ActionRuntime;

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
    public HtmlResponse details(final String id) {
        saveToken();
        try {
            final Project project = projectHelper.getProject(id);
            return asHtml(path_AdminAutoml_AdminAutomlDetailsJsp).renderWith(data -> {
                RenderDataUtil.register(data, "project", project);
            });
        } catch (final Exception e) {
            logger.error("Failed to read " + id, e);
            throwValidationError(messages -> messages.addErrorsCrudFailedToCreateCrudTable(GLOBAL, buildThrowableMessage(e)),
                    () -> asNewProjectHtml()); // TODO fix a message
        }
        return redirect(getClass()); // not invoked
    }

    @Execute
    @Secured({ ROLE })
    public HtmlResponse newdataset(final String id) {
        saveToken();
        return asNewDataHtml(id);
    }

    private HtmlResponse asNewDataHtml(final String id) {
        return asHtml(path_AdminAutoml_AdminAutomlNewdataJsp).useForm(UploadDataSetForm.class, setup -> {
            setup.setup(form -> {
                form.id = id;
            });
        });
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

}
