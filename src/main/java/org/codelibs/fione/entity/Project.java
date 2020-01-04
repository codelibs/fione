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
package org.codelibs.fione.entity;

import org.codelibs.core.lang.StringUtil;
import org.codelibs.fione.h2o.bindings.pojos.JobV3;
import org.codelibs.fione.util.StringCodecUtil;

import com.google.gson.GsonBuilder;

public class Project {

    private String id;

    private String name;

    private transient DataSet[] dataSets = new DataSet[0];

    private transient String[] frameIds = StringUtil.EMPTY_STRINGS;

    private transient JobV3[] jobs = new JobV3[0];

    public Project() {
        // no-op
    }

    public Project(final String id) {
        this.id = id;
        this.name = StringCodecUtil.decode(id);
    }

    public String getId() {
        return id;
    }

    public void setId(final String id) {
        this.id = id;
    }

    public String getName() {
        return name;
    }

    public void setName(final String name) {
        this.name = name;
    }

    public void setDataSets(final DataSet[] dataSets) {
        this.dataSets = dataSets;
    }

    public DataSet[] getDataSets() {
        return dataSets;
    }

    public DataSet getDataSet(final String dataSetId) {
        if (dataSets != null && dataSetId != null) {
            for (final DataSet dataSet : dataSets) {
                if (dataSetId.equals(dataSet.getId())) {
                    return dataSet;
                }
            }
        }
        return null;
    }

    public String[] getFrameIds() {
        return frameIds;
    }

    public void setFrameIds(final String[] frames) {
        this.frameIds = frames;
    }

    public JobV3[] getJobs() {
        return jobs;
    }

    public void setJobs(final JobV3[] jobs) {
        this.jobs = jobs;
    }

    @Override
    public String toString() {
        return new GsonBuilder().serializeSpecialFloatingPointValues().create().toJson(this);
    }

    public boolean hasRunningJobs() {
        if (jobs != null) {
            for (final JobV3 job : jobs) {
                if (JobV3.RUNNING.equals(job.status)) {
                    return true;
                }
            }
        }
        return false;
    }

}
