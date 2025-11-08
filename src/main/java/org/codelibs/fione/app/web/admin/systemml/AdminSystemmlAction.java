/*
 * Copyright 2012-2023 CodeLibs Project and the Others.
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
package org.codelibs.fione.app.web.admin.systemml;

import jakarta.annotation.Resource;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.codelibs.fess.annotation.Secured;
import org.codelibs.fess.util.RenderDataUtil;
import org.codelibs.fione.app.web.base.FioneAdminAction;
import org.codelibs.fione.helper.H2oHelper;
import org.lastaflute.web.Execute;
import org.lastaflute.web.response.HtmlResponse;
import org.lastaflute.web.ruts.process.ActionRuntime;

public class AdminSystemmlAction extends FioneAdminAction {

    public static final String ROLE = "admin-systemml";

    private static final Logger logger = LogManager.getLogger(AdminSystemmlAction.class);

    @Resource
    private H2oHelper h2oHelper;

    // ===================================================================================
    //                                                                               Hook
    //                                                                              ======
    @Override
    protected void setupHtmlData(final ActionRuntime runtime) {
        super.setupHtmlData(runtime);
        runtime.registerData("helpLink", systemHelper.getHelpLink("systemml"));
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
    @Secured({ ROLE })
    public HtmlResponse shutdowncluster(final SystemForm form) {
        validate(form, messages -> {}, this::asListHtml);
        verifyTokenKeep(this::asListHtml);
        try {
            final var shutdownClusterResponse = h2oHelper.shutdownCluster(getSessionKey()).execute();
            if (logger.isDebugEnabled()) {
                logger.debug("shutdownClusterResponse: {}", shutdownClusterResponse);
            }
            if (shutdownClusterResponse.code() == 200) {
                saveMessage(messages -> messages.addSuccessShutdownH2o(GLOBAL));
            } else {
                saveMessage(messages -> messages.addErrorsFailedToShutdownH2o(GLOBAL));
            }
        } catch (final Exception e) {
            logger.warn("Failed to restart H2O.", e);
            throw validationError(messages -> messages.addErrorsFailedToShutdownH2o(GLOBAL), this::asListHtml);
        }
        return redirect(getClass());
    }

    @Execute
    @Secured({ ROLE })
    public HtmlResponse reloadmodule(final SystemForm form) {
        validate(form, messages -> {}, this::asListHtml);
        verifyTokenKeep(this::asListHtml);
        try {
            pythonHelper.reload();
            saveMessage(messages -> messages.addSuccessReloadModules(GLOBAL));
        } catch (final Exception e) {
            logger.warn("Failed to reload modules.", e);
            throw validationError(messages -> messages.addErrorsFailedToReloadModules(GLOBAL), this::asListHtml);
        }
        return redirect(getClass());
    }

    @Execute
    @Secured({ ROLE })
    public HtmlResponse addmodule() {
        saveToken();
        return asAddModuleHtml();
    }

    @Execute
    @Secured({ ROLE })
    public HtmlResponse uploadmodule(final UploadModuleForm form) {
        validate(form, messages -> {}, this::asAddModuleHtml);
        verifyToken(this::asAddModuleHtml);
        final var fileName = form.moduleFile.getFileName();
        try (var in = form.moduleFile.getInputStream()) {
            pythonHelper.addModule(fileName, in);
            saveMessage(messages -> messages.addSuccessUploadedModule(GLOBAL, fileName));
        } catch (final Exception e) {
            logger.warn("Failed to add " + form.moduleFile.getFileName(), e);
            throw validationError(messages -> messages.addErrorsFailedToUploadModule(GLOBAL, fileName), this::asAddModuleHtml);
        }
        return redirect(AdminSystemmlAction.class);
    }

    // ===================================================================================
    //                                                                              JSP
    //                                                                           =========

    private HtmlResponse asListHtml() {
        final var token = doubleSubmitManager.saveToken(myTokenGroupType());
        return asHtml(path_AdminSystemml_AdminSystemmlJsp).renderWith(data -> {
            RenderDataUtil.register(data, "token", token);
            try {
                final var cloudStatusResponse = h2oHelper.getCloudStatus(getSessionKey()).execute();
                if (logger.isDebugEnabled()) {
                    logger.debug("cloudStatusResponse: {}", cloudStatusResponse);
                }
                if (cloudStatusResponse.code() == 200) {
                    final var cloudStatus = cloudStatusResponse.body();
                    RenderDataUtil.register(data, "cloudStatus", cloudStatus);
                }
            } catch (final Exception e) {
                logger.warn("Failed to get cloudStatus.", e);
            }
        });
    }

    private HtmlResponse asAddModuleHtml() {
        return asHtml(path_AdminSystemml_AdminSystemmlModuleJsp).useForm(UploadModuleForm.class);
    }
}
