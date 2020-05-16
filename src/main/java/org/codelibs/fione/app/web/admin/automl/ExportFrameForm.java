package org.codelibs.fione.app.web.admin.automl;

import org.lastaflute.web.validation.Required;

public class ExportFrameForm {
    @Required
    public String projectId;

    @Required
    public String frameId;

    public String leaderboardId;

    @Required
    public String filename;
}
