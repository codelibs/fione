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
package org.codelibs.fione.app.web.base;

import org.codelibs.fess.app.web.base.FessAdminAction;
import org.codelibs.fione.exception.FioneSystemException;
import org.codelibs.fione.mylasta.action.FioneHtmlPath;
import org.codelibs.fione.mylasta.action.FioneMessages;
import org.lastaflute.web.validation.VaErrorHook;
import org.lastaflute.web.validation.VaMessenger;

/**
 * @author shinsuke
 */
public abstract class FioneAdminAction extends FessAdminAction implements FioneHtmlPath {

    protected void saveMessage(final VaMessenger<FioneMessages> validationMessagesLambda) {
        final FioneMessages messages = createMessages();
        validationMessagesLambda.message(messages);
        sessionManager.info().saveMessages(messages);
    }

    protected FioneSystemException validationError(final VaMessenger<FioneMessages> validationMessagesLambda,
            final VaErrorHook validationErrorLambda) {
        createValidator().throwValidationError(() -> {
            final FioneMessages messages = createMessages();
            validationMessagesLambda.message(messages);
            return messages;
        }, validationErrorLambda);
        return new FioneSystemException("validation error"); // no-op
    }

    @Override
    public FioneMessages createMessages() { // application may call
        return new FioneMessages(); // overriding to change return type to concrete-class
    }
}
