package org.codelibs.fione.app.web.admin.automl;

import org.lastaflute.web.ruts.multipart.MultipartFormFile;
import org.lastaflute.web.validation.Required;

public class UploadDataSetForm {
    @Required
    public String id;

    @Required
    public MultipartFormFile dataFile;

}
