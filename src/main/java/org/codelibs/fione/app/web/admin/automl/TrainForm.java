/*
 * Copyright 2012-2022 CodeLibs Project and the Others.
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

import java.util.HashMap;
import java.util.Map;

import javax.validation.constraints.Max;
import javax.validation.constraints.Min;

import org.lastaflute.web.validation.Required;
import org.lastaflute.web.validation.theme.conversion.ValidateTypeFailure;

public class TrainForm {
    @Required
    public String projectId;

    @Required
    public String frameId;

    @Required
    public String projectName;

    public Map<String, String> ignoredColumns = new HashMap<>();

    @Min(value = 0)
    @Max(value = 2147483647)
    @ValidateTypeFailure
    public Integer nfolds = 5;

    public String balanceClasses = Boolean.FALSE.toString();

    @ValidateTypeFailure
    public Integer seed = -1;

    @Min(value = 0)
    @Max(value = 2147483647)
    @ValidateTypeFailure
    public Integer maxModels = 0;

    @Min(value = 0)
    @Max(value = 2147483647)
    @ValidateTypeFailure
    public Integer maxRuntimeSecs = 3600;

    @Min(value = 0)
    @Max(value = 2147483647)
    @ValidateTypeFailure
    public Integer maxRuntimeSecsPerModel = 0;

    @Min(value = 0)
    @Max(value = 2147483647)
    @ValidateTypeFailure
    public Integer stoppingRounds = 3;

    public String stoppingMetric = "AUTO";

    @ValidateTypeFailure
    public Double stoppingTolerance = 0.001;

    public String keepCrossValidationPredictions = Boolean.TRUE.toString();

    public String keepCrossValidationModels = Boolean.TRUE.toString();

    public String keepCrossValidationFoldAssignment = Boolean.TRUE.toString();

    @Required
    public String responseColumn;

    public String sortMetric = "AUTO";

    @Min(value = 1)
    @Max(value = 2147483647)
    @ValidateTypeFailure
    public Integer maxCategoricalFeatures = 10000;
}
