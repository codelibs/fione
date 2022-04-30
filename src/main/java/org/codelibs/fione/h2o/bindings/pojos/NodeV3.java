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
package org.codelibs.fione.h2o.bindings.pojos;

import com.google.gson.Gson;
import com.google.gson.annotations.SerializedName;

public class NodeV3 extends SchemaV3 {

    /**
     * IP
     */
    public String h2o;

    /**
     * IP address and port in the form a.b.c.d:e
     */
    @SerializedName("ip_port")
    public String ipPort;

    /**
     * (now-last_ping)<HeartbeatThread.TIMEOUT
     */
    public boolean healthy;

    /**
     * Time (in msec) of last ping
     */
    @SerializedName("last_ping")
    public long lastPing;

    /**
     * PID
     */
    public int pid;

    /**
     * num_cpus
     */
    @SerializedName("num_cpus")
    public int numCpus;

    /**
     * cpus_allowed
     */
    @SerializedName("cpus_allowed")
    public int cpusAllowed;

    /**
     * nthreads
     */
    public int nthreads;

    /**
     * System load; average #runnables/#cores
     */
    @SerializedName("sys_load")
    public float sysLoad;

    /**
     * System CPU percentage used by this H2O process in last interval
     */
    @SerializedName("my_cpu_pct")
    public int myCpuPct;

    /**
     * System CPU percentage used by everything in last interval
     */
    @SerializedName("sys_cpu_pct")
    public int sysCpuPct;

    /**
     * Data on Node memory
     */
    @SerializedName("mem_value_size")
    public long memValueSize;

    /**
     * Temp (non Data) memory
     */
    @SerializedName("pojo_mem")
    public long pojoMem;

    /**
     * Free heap
     */
    @SerializedName("free_mem")
    public long freeMem;

    /**
     * Maximum memory size for node
     */
    @SerializedName("max_mem")
    public long maxMem;

    /**
     * Size of data on node's disk
     */
    @SerializedName("swap_mem")
    public long swapMem;

    /**
     * #local keys
     */
    @SerializedName("num_keys")
    public int numKeys;

    /**
     * Free disk
     */
    @SerializedName("free_disk")
    public long freeDisk;

    /**
     * Max disk
     */
    @SerializedName("max_disk")
    public long maxDisk;

    /**
     * Active Remote Procedure Calls
     */
    @SerializedName("rpcs_active")
    public int rpcsActive;

    /**
     * F/J Thread count, by priority
     */
    public short[] fjthrds;

    /**
     * F/J Task count, by priority
     */
    public short[] fjqueue;

    /**
     * Open TCP connections
     */
    @SerializedName("tcps_active")
    public int tcpsActive;

    /**
     * Open File Descripters
     */
    @SerializedName("open_fds")
    public int openFds;

    /**
     * Linpack GFlops
     */
    public double gflops;

    /**
     * Memory Bandwidth
     */
    @SerializedName("mem_bw")
    public double memBw;

    /**
     * Public constructor
     */
    public NodeV3() {
        h2o = "";
        ipPort = "";
        healthy = false;
        lastPing = 0L;
        pid = 0;
        numCpus = 0;
        cpusAllowed = 0;
        nthreads = 0;
        sysLoad = 0.0f;
        myCpuPct = 0;
        sysCpuPct = 0;
        memValueSize = 0L;
        pojoMem = 0L;
        freeMem = 0L;
        maxMem = 0L;
        swapMem = 0L;
        numKeys = 0;
        freeDisk = 0L;
        maxDisk = 0L;
        rpcsActive = 0;
        tcpsActive = 0;
        openFds = 0;
        gflops = 0.0;
        memBw = 0.0;
    }

    /**
     * Return the contents of this object as a JSON String.
     */
    @Override
    public String toString() {
        return new Gson().toJson(this);
    }

}
