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

import static org.junit.Assert.assertArrayEquals;

import java.util.concurrent.CountDownLatch;

import org.codelibs.fione.h2o.bindings.pojos.ColV3;
import org.codelibs.fione.h2o.bindings.pojos.FrameV3;
import org.codelibs.fione.h2o.bindings.pojos.FramesV3;
import org.codelibs.fione.h2o.bindings.pojos.ImportFilesV3;
import org.codelibs.fione.h2o.bindings.pojos.JobV3;
import org.codelibs.fione.h2o.bindings.pojos.JobsV3;
import org.codelibs.fione.h2o.bindings.pojos.ParseSetupV3;
import org.codelibs.fione.h2o.bindings.pojos.ParseV3;
import org.dbflute.utflute.lastaflute.LastaFluteTestCase;
import org.testcontainers.containers.BindMode;
import org.testcontainers.containers.GenericContainer;
import org.testcontainers.containers.wait.strategy.Wait;

import junit.framework.AssertionFailedError;

public class H2oHelperTest extends LastaFluteTestCase {

    private GenericContainer<?> h2o;

    private H2oHelper h2oHelper;

    private Throwable throwable;

    @Override
    protected String prepareConfigFile() {
        return "test_app.xml";
    }

    @Override
    public void setUp() throws Exception {
        super.setUp();
        h2o =
                new GenericContainer<>("codelibs/h2o:3.28.0.1")
                        //
                        .withExposedPorts(54321)
                        //
                        .withClasspathResourceMapping("data/iris.csv", "/data/iris.csv", BindMode.READ_ONLY)
                        .withClasspathResourceMapping("data/tips.csv", "/data/tips.csv", BindMode.READ_ONLY)
                        .waitingFor(Wait.forHttp("/flow/index.html").forStatusCode(200));
        h2o.start();
        h2o.followOutput(o -> System.out.print(o.getUtf8String()));

        h2oHelper = new H2oHelper();
        h2oHelper.setEndpoint(getEndpoint());
        h2oHelper.init();
        System.out.println("Endpoint: " + getEndpoint());
    }

    private String getEndpoint() {
        return "http://" + h2o.getContainerIpAddress() + ":" + h2o.getMappedPort(54321);
    }

    @Override
    public void tearDown() throws Exception {
        h2o.stop();
        super.tearDown();
    }

    public void test_iris() throws Throwable {
        final CountDownLatch latch = new CountDownLatch(1);
        h2oHelper.importFiles("/data/iris.csv").execute((call, res) -> {
            ImportFilesV3 result = res.body();
            assertEquals("/data/iris.csv", result.path);
            assertArrayEquals(new String[] { "nfs://data/iris.csv" }, result.destinationFrames);
            test_iris_parseSetup(latch, result);
        }, (call, t) -> {
            fail(t, latch);
        });
        latch.await();
        if (throwable != null) {
            throw throwable;
        }
    }

    private void test_iris_parseSetup(final CountDownLatch latch, ImportFilesV3 data) {
        h2oHelper.setupParse(data.destinationFrames).execute((call, res) -> {
            ParseSetupV3 result = res.body();
            assertEquals(1, result.checkHeader);
            assertEquals(4194304, result.chunkSize);
            assertEquals(0, result.columnCount);
            assertNull(result.columnNameFilter);
            assertArrayEquals(new String[] { "SepalLength", "SepalWidth", "PetalLength", "PetalWidth", "Name" }, result.columnNames);
            assertEquals(0, result.columnOffset);
            assertArrayEquals(new String[] { "Numeric", "Numeric", "Numeric", "Numeric", "Enum" }, result.columnTypes);
            assertEquals("iris.hex", result.destinationFrame);
            assertEquals(0, result.headerLines);
            assertNull(result.naStrings);
            assertEquals(5, result.numberColumns);
            assertEquals("CSV", result.parseType.name());
            assertEquals(44, result.separator);
            assertFalse(result.singleQuotes);
            assertEquals(5, result.totalFilteredColumnCount);
            assertNull(result.warnings);
            assertEquals("nfs://data/iris.csv", result.sourceFrames[0].name);
            test_iris_parse(latch, result);
        }, (call, t) -> {
            fail(t, latch);
        });
    }

    private void test_iris_parse(final CountDownLatch latch, ParseSetupV3 data) {
        ParseV3 params = h2oHelper.convert(data);
        h2oHelper.parseFiles(params).execute((call, res) -> {
            ParseV3 result = res.body();
            assertEquals(1, result.checkHeader);
            assertEquals(4194304, result.chunkSize);
            assertArrayEquals(new String[] { "SepalLength", "SepalWidth", "PetalLength", "PetalWidth", "Name" }, result.columnNames);
            assertArrayEquals(new String[] { "Numeric", "Numeric", "Numeric", "Numeric", "Enum" }, result.columnTypes);
            assertTrue(result.deleteOnDone);
            assertEquals("iris.hex", result.destinationFrame.name);
            assertNull(result.domains);
            assertNull(result.naStrings);
            assertEquals(5, result.numberColumns);
            assertEquals("CSV", result.parseType.name());
            assertEquals(150, result.rows);
            assertEquals(44, result.separator);
            assertFalse(result.singleQuotes);
            assertEquals("nfs://data/iris.csv", result.sourceFrames[0].name);
            test_iris_summary(latch, result, result.job);
        }, (call, t) -> {
            fail(t, latch);
        });
    }

    private void test_iris_summary(final CountDownLatch latch, ParseV3 data, JobV3 job) {
        if ("DONE".equals(job.status)) {
            h2oHelper.getFrameSummary(data.destinationFrame.name).execute((call, res) -> {
                FramesV3 result = res.body();
                assertEquals(1, result.frames.length);
                FrameV3 frame = result.frames[0];
                assertEquals(5, frame.columns.length);

                ColV3 col1 = frame.columns[0];
                assertEquals("SepalLength", col1.label);
                assertEquals(4.3, col1.histogramBase);
                assertEquals(7.9, col1.maxs[0]);
                assertEquals(5.843333333333333, col1.mean);
                assertEquals(4.3, col1.mins[0]);
                assertEquals(0, col1.missingCount);
                assertEquals(0, col1.negativeInfinityCount);
                assertEquals(17, col1.percentiles.length);
                assertEquals(0, col1.positiveInfinityCount);
                assertEquals(0, col1.precision);
                assertEquals(0.8280661279778637, col1.sigma);
                assertEquals(0, col1.zeroCount);
                assertEquals("real", col1.type);
                assertNull(col1.domain);

                ColV3 col5 = frame.columns[4];
                assertEquals("Name", col5.label);
                assertEquals(0.0, col5.histogramBase);
                assertEquals(2.0, col5.maxs[0]);
                assertEquals(Double.NaN, col5.mean);
                assertEquals(0.0, col5.mins[0]);
                assertEquals(0, col5.missingCount);
                assertEquals(0, col5.negativeInfinityCount);
                assertEquals(17, col5.percentiles.length);
                assertEquals(0, col5.positiveInfinityCount);
                assertEquals(-1, col5.precision);
                assertEquals(Double.NaN, col5.sigma);
                assertEquals(50, col5.zeroCount);
                assertEquals("enum", col5.type);
                assertArrayEquals(new String[] { "Iris-setosa", "Iris-versicolor", "Iris-virginica" }, col5.domain);
                assertEquals(3, col5.domainCardinality);

                test_iris_columnSummary(latch, data);
            }, (call, t) -> {
                fail(t, latch);
            });
        } else if ("CANCELLED".equals(job.status) || "FAILED".equals(job.status)) {
            fail(new AssertionFailedError("job.status: " + job.status), latch);
        } else {
            h2oHelper.fetchJobs(job.key.name).execute((call, res) -> {
                JobsV3 result = res.body();
                for (JobV3 j : result.jobs) {
                    if (j.key.name.equals(job.key.name)) {
                        test_iris_summary(latch, data, j);
                        return;
                    }
                }
                fail();
            }, (call, t) -> {
                fail(t, latch);
            });
        }
    }

    private void test_iris_columnSummary(final CountDownLatch latch, ParseV3 data) {
        h2oHelper.getFrameColumnSummary(data.destinationFrame.name, "SepalLength").execute((call, res) -> {
            FramesV3 result = res.body();
            assertEquals(1, result.frames.length);
            FrameV3 frame = result.frames[0];
            assertEquals(1, frame.columns.length);

            ColV3 col1 = frame.columns[0];
            assertEquals("SepalLength", col1.label);
            assertEquals(4.3, col1.histogramBase);
            assertEquals(7.9, col1.maxs[0]);
            assertEquals(5.843333333333333, col1.mean);
            assertEquals(4.3, col1.mins[0]);
            assertEquals(0, col1.missingCount);
            assertEquals(0, col1.negativeInfinityCount);
            assertEquals(17, col1.percentiles.length);
            assertEquals(0, col1.positiveInfinityCount);
            assertEquals(0, col1.precision);
            assertEquals(0.8280661279778637, col1.sigma);
            assertEquals(0, col1.zeroCount);
            assertEquals("real", col1.type);
            assertNull(col1.domain);

            latch.countDown();
        }, (call, t) -> {
            fail(t, latch);
        });
    }

    private void fail(Throwable t, CountDownLatch latch) {
        throwable = t;
        latch.countDown();
    }
}
