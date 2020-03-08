/*
 * Copyright 2012-2020 CodeLibs Project and the Others.
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
package org.codelibs.fione.h2o.bindings.pojos;

import com.google.gson.GsonBuilder;
import com.google.gson.annotations.SerializedName;

public class CloudV3 extends RequestSchemaV3 {

    /**
     * skip_ticks
     */
    @SerializedName("skip_ticks")
    public boolean skipTicks;

    /**
     * version
     */
    public String version;

    /**
     * branch_name
     */
    @SerializedName("branch_name")
    public String branchName;

    /**
     * last_commit_hash
     */
    @SerializedName("last_commit_hash")
    public String lastCommitHash;

    /**
     * describe
     */
    public String describe;

    /**
     * compiled_by
     */
    @SerializedName("compiled_by")
    public String compiledBy;

    /**
     * compiled_on
     */
    @SerializedName("compiled_on")
    public String compiledOn;

    /**
     * build_number
     */
    @SerializedName("build_number")
    public String buildNumber;

    /**
     * build_age
     */
    @SerializedName("build_age")
    public String buildAge;

    /**
     * build_too_old
     */
    @SerializedName("build_too_old")
    public boolean buildTooOld;

    /**
     * Node index number cloud status is collected from (zero-based)
     */
    @SerializedName("node_idx")
    public int nodeIdx;

    /**
     * cloud_name
     */
    @SerializedName("cloud_name")
    public String cloudName;

    /**
     * cloud_size
     */
    @SerializedName("cloud_size")
    public int cloudSize;

    /**
     * cloud_uptime_millis
     */
    @SerializedName("cloud_uptime_millis")
    public long cloudUptimeMillis;

    /**
     * Cloud internal timezone
     */
    @SerializedName("cloud_internal_timezone")
    public String cloudInternalTimezone;

    /**
     * Timezone used for parsing datetime columns
     */
    @SerializedName("datafile_parser_timezone")
    public String datafileParserTimezone;

    /**
     * cloud_healthy
     */
    @SerializedName("cloud_healthy")
    public boolean cloudHealthy;

    /**
     * Nodes reporting unhealthy
     */
    @SerializedName("bad_nodes")
    public int badNodes;

    /**
     * Cloud voting is stable
     */
    public boolean consensus;

    /**
     * Cloud is accepting new members or not
     */
    public boolean locked;

    /**
     * Cloud is in client mode.
     */
    @SerializedName("is_client")
    public boolean isClient;

    /**
     * nodes
     */
    public NodeV3[] nodes;

    /**
     * internal_security_enabled
     */
    @SerializedName("internal_security_enabled")
    public boolean internalSecurityEnabled;

    /**
     * leader_idx
     */
    @SerializedName("leader_idx")
    public int leaderIdx;

    /*------------------------------------------------------------------------------------------------------------------
    //                                                  INHERITED
    //------------------------------------------------------------------------------------------------------------------

    // Comma-separated list of JSON field paths to exclude from the result, used like:
    // "/3/Frames?_exclude_fields=frames/frame_id/URL,__meta"
    public String _excludeFields;

    */

    /**
     * Public constructor
     */
    public CloudV3() {
        skipTicks = false;
        version = "";
        branchName = "";
        lastCommitHash = "";
        describe = "";
        compiledBy = "";
        compiledOn = "";
        buildNumber = "";
        buildAge = "";
        buildTooOld = false;
        nodeIdx = 0;
        cloudName = "";
        cloudSize = 0;
        cloudUptimeMillis = 0L;
        cloudInternalTimezone = "";
        datafileParserTimezone = "";
        cloudHealthy = false;
        badNodes = 0;
        consensus = false;
        locked = false;
        isClient = false;
        internalSecurityEnabled = false;
        leaderIdx = -1;
        _excludeFields = "";
    }

    /**
     * Return the contents of this object as a JSON String.
     */
    @Override
    public String toString() {
        return new GsonBuilder().serializeSpecialFloatingPointValues().create().toJson(this);
    }

}
