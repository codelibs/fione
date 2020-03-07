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
package org.codelibs.fione.app.web.admin.systemml;

import javax.annotation.Resource;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.codelibs.fess.annotation.Secured;
import org.codelibs.fess.util.RenderDataUtil;
import org.codelibs.fione.app.web.base.FioneAdminAction;
import org.codelibs.fione.h2o.bindings.pojos.CloudV3;
import org.codelibs.fione.helper.H2oHelper;
import org.lastaflute.web.Execute;
import org.lastaflute.web.response.HtmlResponse;
import org.lastaflute.web.ruts.process.ActionRuntime;

import retrofit2.Response;

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

    // ===================================================================================
    //                                                                              JSP
    //                                                                           =========

    private HtmlResponse asListHtml() {
        saveToken();
        return asHtml(path_AdminSystemml_AdminSystemmlJsp).renderWith(data -> {
            try {
                Response<CloudV3> cloudStatusResponse = h2oHelper.getCloudStatus().execute();
                if (logger.isDebugEnabled()) {
                    logger.debug("cloudStatusResponse: {}", cloudStatusResponse);
                }
                if (cloudStatusResponse.code() == 200) {
                    final CloudV3 cloudStatus = cloudStatusResponse.body();
                    RenderDataUtil.register(data, "cloudStatus", cloudStatus);
                }
            } catch (final Exception e) {
                logger.warn("Failed to get cloudStatus.", e);
            }
        });
    }
}
