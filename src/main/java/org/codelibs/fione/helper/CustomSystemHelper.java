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

import javax.annotation.PostConstruct;

import org.codelibs.fess.helper.SystemHelper;
import org.codelibs.fess.mylasta.direction.FessConfig;
import org.codelibs.fess.util.ComponentUtil;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class CustomSystemHelper extends SystemHelper {

    private static final Logger logger = LoggerFactory.getLogger(CustomSystemHelper.class);

    @Override
    @PostConstruct
    public void init() {
        super.init();

        updateH2oSettings();
    }

    @Override
    public void updateSystemProperties() {
        super.updateSystemProperties();
        updateH2oSettings();
    }

    protected void updateH2oSettings() {
        if (logger.isDebugEnabled()) {
            logger.debug("Update credentials for H2O.");
        }
        final FessConfig fessConfig = ComponentUtil.getFessConfig();
        final H2oHelper h2oHelper = ComponentUtil.getComponent(H2oHelper.class);
        h2oHelper.setEndpoint(fessConfig.getSystemProperty("h2o.endpoint", "http://localhost:54321"));
        h2oHelper.setSecretAccessKey(fessConfig.getStorageAccessKey());
        h2oHelper.setSecretKeyId(fessConfig.getStorageSecretKey());
        h2oHelper.invalidate();
    }

    @Override
    public String getHelpLink(final String name) {
        return getHelpUrl("https://fione.codelibs.org/{lang}/");
    }
}
