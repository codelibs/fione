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
package org.codelibs.fione.app.web.base;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Map;
import java.util.function.BiFunction;

import javax.annotation.Resource;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.codelibs.core.collection.Maps;
import org.codelibs.core.lang.StringUtil;
import org.codelibs.fess.app.web.base.FessAdminAction;
import org.codelibs.fess.mylasta.action.FessUserBean;
import org.codelibs.fess.util.RenderDataUtil;
import org.codelibs.fione.exception.FioneSystemException;
import org.codelibs.fione.h2o.bindings.pojos.Automlapischemas3AutoMLBuildSpecAutoMLMetricProvider;
import org.codelibs.fione.h2o.bindings.pojos.ParseV3;
import org.codelibs.fione.h2o.bindings.pojos.ScoreKeeperStoppingMetric;
import org.codelibs.fione.helper.ProjectHelper;
import org.codelibs.fione.helper.PythonHelper;
import org.codelibs.fione.mylasta.action.FioneHtmlPath;
import org.codelibs.fione.mylasta.action.FioneMessages;
import org.codelibs.fione.util.StringCodecUtil;
import org.lastaflute.web.response.render.RenderData;
import org.lastaflute.web.token.DoubleSubmitManager;
import org.lastaflute.web.validation.VaErrorHook;
import org.lastaflute.web.validation.VaMessenger;

/**
 * @author shinsuke
 */
public abstract class FioneAdminAction extends FessAdminAction implements FioneHtmlPath {

    private static final Logger logger = LogManager.getLogger(FioneAdminAction.class);

    protected static final String DATASET_ID = "did";

    protected static final String FRAME_ID = "fid";

    protected static final String LEADERBOARD_ID = "lid";

    protected static final String MODEL_ID = "mid";

    @Resource
    protected ProjectHelper projectHelper;

    @Resource
    protected PythonHelper pythonHelper;

    @Resource
    protected DoubleSubmitManager doubleSubmitManager;

    protected void saveMessage(final VaMessenger<FioneMessages> validationMessagesLambda) {
        final var messages = createMessages();
        validationMessagesLambda.message(messages);
        sessionManager.info().saveMessages(messages);
    }

    protected FioneSystemException validationError(final VaMessenger<FioneMessages> validationMessagesLambda,
            final VaErrorHook validationErrorLambda) {
        createValidator().throwValidationError(() -> {
            final var messages = createMessages();
            validationMessagesLambda.message(messages);
            return messages;
        }, validationErrorLambda);
        return new FioneSystemException("validation error"); // no-op
    }

    @Override
    public FioneMessages createMessages() { // application may call
        return new FioneMessages(); // overriding to change return type to concrete-class
    }

    protected void registerColumnTypeItems(final RenderData data) {
        final List<Map<String, String>> columnTypeItems = new ArrayList<>();
        columnTypeItems.add(Maps.map("label", "BAD").$("value", "BAD").$());
        columnTypeItems.add(Maps.map("label", "UUID").$("value", "UUID").$());
        columnTypeItems.add(Maps.map("label", "String").$("value", "String").$());
        columnTypeItems.add(Maps.map("label", "Numeric").$("value", "Numeric").$());
        columnTypeItems.add(Maps.map("label", "Enum").$("value", "Enum").$());
        columnTypeItems.add(Maps.map("label", "Time").$("value", "Time").$());
        RenderDataUtil.register(data, "columnTypeItems", columnTypeItems);
    }

    protected String convertSchemaColumnType(final String type) {
        return switch (type) {
        case "BAD" -> "BAD";
        case "UUID" -> "UUID";
        case "String", "string", "str", "character" -> "String";
        case "Numeric", "numeric", "int", "real" -> "Numeric";
        case "Enum", "enum", "factor", "categorical" -> "Enum";
        case "Time", "time" -> "Time";
        default -> "String";
        };
    }

    protected void registerColumnItems(final ParseV3 schema, final RenderData data,
            final BiFunction<Maps<String, String>, Integer, Maps<String, String>> maps) {
        final List<Map<String, String>> columnItems = new ArrayList<>();
        final var columnNames = schema.getAvailableColumnNames();
        for (var i = 0; i < columnNames.length; i++) {
            final var columnName = columnNames[i];
            columnItems.add(maps.apply(
                    Maps.map("id", StringCodecUtil.encodeUrlSafe(columnName)).$("name", columnName).$("value", schema.columnTypes[i]), i)
                    .$());
        }
        RenderDataUtil.register(data, "columnItems", columnItems);
    }

    protected void registerSortMetricItems(final RenderData data) {
        RenderDataUtil.register(data, "sortMetricItems", Arrays.stream(Automlapischemas3AutoMLBuildSpecAutoMLMetricProvider.values())
                .map(Automlapischemas3AutoMLBuildSpecAutoMLMetricProvider::toString).toArray(n -> new String[n]));
    }

    protected void registerStoppingMetricItems(final RenderData data) {
        RenderDataUtil.register(data, "stoppingMetricItems",
                Arrays.stream(ScoreKeeperStoppingMetric.values()).map(ScoreKeeperStoppingMetric::toString).toArray(n -> new String[n]));
    }

    protected String getResponseColumn(final String projectName) {
        if (projectName == null) {
            return StringUtil.EMPTY;
        }
        final var pos = projectName.indexOf("@@");
        if (pos == -1) {
            return projectName;
        }
        return projectName.split("@@", 2)[1];
    }

    protected String getSessionKey() {
        String sessionKey;
        try {
            sessionKey = fessLoginAssist.getSavedUserBean().map(FessUserBean::getUserId).orElse("guest");
        } catch (final Exception e) {
            if (logger.isDebugEnabled()) {
                logger.debug("Failed to get sessionKey.", e);
            }
            sessionKey = "guest";
        }
        return StringCodecUtil.encodeUrlSafe(sessionKey);
    }

}
