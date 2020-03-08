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
package org.codelibs.fione.helper;

import static org.junit.Assert.assertArrayEquals;

import java.util.concurrent.CountDownLatch;

import org.codelibs.fione.h2o.bindings.builder.AutoMLBuildControlBuilder;
import org.codelibs.fione.h2o.bindings.builder.AutoMLBuildModelsBuilder;
import org.codelibs.fione.h2o.bindings.builder.AutoMLInputBuilder;
import org.codelibs.fione.h2o.bindings.builder.AutoMLStoppingCriteriaBuilder;
import org.codelibs.fione.h2o.bindings.pojos.AutoMLBuildControlV99;
import org.codelibs.fione.h2o.bindings.pojos.AutoMLBuildModelsV99;
import org.codelibs.fione.h2o.bindings.pojos.AutoMLBuildSpecV99;
import org.codelibs.fione.h2o.bindings.pojos.AutoMLInputV99;
import org.codelibs.fione.h2o.bindings.pojos.AutoMLStoppingCriteriaV99;
import org.codelibs.fione.h2o.bindings.pojos.Automlapischemas3AutoMLBuildSpecAutoMLMetricProvider;
import org.codelibs.fione.h2o.bindings.pojos.ColV3;
import org.codelibs.fione.h2o.bindings.pojos.FrameKeyV3;
import org.codelibs.fione.h2o.bindings.pojos.FrameV3;
import org.codelibs.fione.h2o.bindings.pojos.FramesV3;
import org.codelibs.fione.h2o.bindings.pojos.ImportFilesV3;
import org.codelibs.fione.h2o.bindings.pojos.JobV3;
import org.codelibs.fione.h2o.bindings.pojos.JobsV3;
import org.codelibs.fione.h2o.bindings.pojos.LeaderboardV99;
import org.codelibs.fione.h2o.bindings.pojos.ModelKeyV3;
import org.codelibs.fione.h2o.bindings.pojos.ModelMetricsListSchemaV3;
import org.codelibs.fione.h2o.bindings.pojos.ModelsV3;
import org.codelibs.fione.h2o.bindings.pojos.ParseSetupV3;
import org.codelibs.fione.h2o.bindings.pojos.ParseV3;
import org.codelibs.fione.h2o.bindings.pojos.ScoreKeeperStoppingMetric;
import org.codelibs.fione.h2o.bindings.pojos.TwoDimTableV3;
import org.dbflute.utflute.lastaflute.LastaFluteTestCase;
import org.testcontainers.containers.BindMode;
import org.testcontainers.containers.GenericContainer;
import org.testcontainers.containers.wait.strategy.Wait;

import junit.framework.AssertionFailedError;
import okhttp3.logging.HttpLoggingInterceptor;

public class H2oHelperTest extends LastaFluteTestCase {

    private GenericContainer<?> h2o;

    private H2oHelper h2oHelper;

    private Throwable throwable;

    @Override
    protected String prepareConfigFile() {
        return "test_app.xml";
    }

    @SuppressWarnings("resource")
    @Override
    public void setUp() throws Exception {
        super.setUp();
        h2o =
                new GenericContainer<>("codelibs/h2o:3.28.0.3").withExposedPorts(54321)
                        .withClasspathResourceMapping("data/iris.csv", "/data/iris.csv", BindMode.READ_ONLY)
                        .withClasspathResourceMapping("data/tips.csv", "/data/tips.csv", BindMode.READ_ONLY)
                        .waitingFor(Wait.forHttp("/flow/index.html").forStatusCode(200));
        h2o.start();
        h2o.followOutput(o -> System.out.print(o.getUtf8String()));

        final HttpLoggingInterceptor interceptor = new HttpLoggingInterceptor();
        interceptor.setLevel(HttpLoggingInterceptor.Level.BODY);

        h2oHelper = new H2oHelper();
        h2oHelper.setEndpoint(getEndpoint());
        h2oHelper.addHttpInterceptor(interceptor);
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
            final ImportFilesV3 result = res.body();
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

    private void test_iris_parseSetup(final CountDownLatch latch, final ImportFilesV3 data) {
        h2oHelper.setupParse(data.destinationFrames).execute((call, res) -> {
            final ParseSetupV3 result = res.body();
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

    private void test_iris_parse(final CountDownLatch latch, final ParseSetupV3 data) {
        final ParseV3 params = h2oHelper.convert(data);
        h2oHelper.parseFiles(params).execute((call, res) -> {
            final ParseV3 result = res.body();
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

    private void test_iris_summary(final CountDownLatch latch, final ParseV3 data, final JobV3 job) {
        if ("DONE".equals(job.status)) {
            h2oHelper.getFrameSummary(data.destinationFrame.name).execute((call, res) -> {
                final FramesV3 result = res.body();
                assertEquals(1, result.frames.length);
                final FrameV3 frame = result.frames[0];
                assertEquals(5, frame.columns.length);

                final ColV3 col1 = frame.columns[0];
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

                final ColV3 col5 = frame.columns[4];
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
                final JobsV3 result = res.body();
                for (final JobV3 j : result.jobs) {
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

    private void test_iris_columnSummary(final CountDownLatch latch, final ParseV3 data) {
        h2oHelper.getFrameColumnSummary(data.destinationFrame.name, "SepalLength").execute((call, res) -> {
            final FramesV3 result = res.body();
            assertEquals(1, result.frames.length);
            final FrameV3 frame = result.frames[0];
            assertEquals(1, frame.columns.length);

            final ColV3 col1 = frame.columns[0];
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

            test_iris_runAutoML(latch, data);
        }, (call, t) -> {
            fail(t, latch);
        });
    }

    private void test_iris_runAutoML(final CountDownLatch latch, final ParseV3 data) {
        h2oHelper.runAutoML(
                AutoMLBuildControlBuilder
                        .create()
                        .projectName("iris")
                        .nfolds(5)
                        .balanceClasses(false)
                        .stoppingCriteria(
                                AutoMLStoppingCriteriaBuilder.create().seed(-1).maxModels(0).maxRuntimeSecs(60).maxRuntimeSecsPerModel(0)
                                        .stoppingRounds(3).stoppingMetric(ScoreKeeperStoppingMetric.AUTO).stoppingTolerance(0.001).build())
                        .keepCrossValidationPredictions(true).keepCrossValidationModels(true).keepCrossValidationFoldAssignment(false)
                        .build(),
                AutoMLInputBuilder.create().trainingFrame(data.destinationFrame).responseColumn("Name", null)
                        .sortMetric(Automlapischemas3AutoMLBuildSpecAutoMLMetricProvider.AUTO).build(),
                AutoMLBuildModelsBuilder.create().build()).execute((call, res) -> {
            final AutoMLBuildSpecV99 result = res.body();
            final AutoMLBuildControlV99 buildControl = result.buildControl;
            assertFalse(buildControl.balanceClasses);
            assertNull(buildControl.classSamplingFactors);
            assertEquals("", buildControl.exportCheckpointsDir);
            assertFalse(buildControl.keepCrossValidationFoldAssignment);
            assertTrue(buildControl.keepCrossValidationModels);
            assertTrue(buildControl.keepCrossValidationPredictions);
            assertEquals(5.0f, buildControl.maxAfterBalanceSize);
            assertEquals(5, buildControl.nfolds);
            assertEquals("iris", buildControl.projectName);
            final AutoMLStoppingCriteriaV99 stoppingCriteria = buildControl.stoppingCriteria;
            assertEquals(0, stoppingCriteria.maxModels);
            assertEquals(0, Double.compare(60.0, stoppingCriteria.maxRuntimeSecs));
            assertEquals(0, Double.compare(0.0f, stoppingCriteria.maxRuntimeSecsPerModel));
            assertEquals(-1, stoppingCriteria.seed);
            assertEquals(ScoreKeeperStoppingMetric.AUTO, stoppingCriteria.stoppingMetric);
            assertEquals(3, stoppingCriteria.stoppingRounds);
            assertEquals(0, Double.compare(0.001, stoppingCriteria.stoppingTolerance));
            final AutoMLBuildModelsV99 buildModels = result.buildModels;
            assertNull(buildModels.algoParameters);
            assertNull(buildModels.includeAlgos);
            assertNull(buildModels.monotoneConstraints);
            assertEquals(0, buildModels.excludeAlgos.length);
            final AutoMLInputV99 inputSpec = result.inputSpec;
            assertNull(inputSpec.blendingFrame);
            assertNull(inputSpec.foldColumn);
            assertNull(inputSpec.ignoredColumns);
            assertNull(inputSpec.leaderboardFrame);
            assertEquals("Name", inputSpec.responseColumn.columnName);
            assertEquals(Automlapischemas3AutoMLBuildSpecAutoMLMetricProvider.AUTO, inputSpec.sortMetric);
            assertEquals("iris.hex", inputSpec.trainingFrame.name);
            assertNull(inputSpec.validationFrame);
            assertNull(inputSpec.weightsColumn);
            final JobV3 job = result.job;
            assertEquals("AutoML build", job.description);
            assertEquals("iris@@Name", job.dest.name);
            assertNotNull(job.key.name);
            assertTrue(job.progress < 1.0f);
            assertEquals("RUNNING", job.status);

            test_iris_leaderboard(latch, result, job);
        }, (call, t) -> {
            fail(t, latch);
        });
    }

    private void test_iris_leaderboard(final CountDownLatch latch, final AutoMLBuildSpecV99 data, final JobV3 job) {
        if ("DONE".equals(job.status)) {
            h2oHelper.getLeaderboard(job.dest.name).execute((call, res) -> {
                final LeaderboardV99 result = res.body();
                assertNull(result.leaderboardFrame);
                assertEquals(0, result.leaderboardFrameChecksum);
                assertNotNull(result.models);
                assertEquals("iris@@Name", result.projectName);
                assertFalse(result.sortDecreasing);
                assertEquals("mean_per_class_error", result.sortMetric);
                assertEquals(result.models.length, result.sortMetrics.length);
                final TwoDimTableV3 table = result.table;
                assertEquals("", table.columns[0].name);
                assertEquals("model_id", table.columns[1].name);
                assertEquals("mean_per_class_error", table.columns[2].name);
                assertEquals("logloss", table.columns[3].name);
                assertEquals("rmse", table.columns[4].name);
                assertEquals("mse", table.columns[5].name);

                test_iris_getModel(latch, result.models[0]);
            }, (call, t) -> {
                fail(t, latch);
            });
        } else if ("CANCELLED".equals(job.status) || "FAILED".equals(job.status)) {
            fail(new AssertionFailedError("job.status: " + job.status), latch);
        } else {
            sleep(1000L);
            h2oHelper.fetchJobs(job.key.name).execute((call, res) -> {
                final JobsV3 result = res.body();
                for (final JobV3 j : result.jobs) {
                    if (j.key.name.equals(job.key.name)) {
                        test_iris_leaderboard(latch, data, j);
                        return;
                    }
                }
                fail();
            }, (call, t) -> {
                fail(t, latch);
            });
        }
    }

    private void test_iris_getModel(final CountDownLatch latch, final ModelKeyV3 modelKey) {
        h2oHelper.getModel(modelKey).execute((call, res) -> {
            final ModelsV3 result = res.body();
            assertEquals("", result._excludeFields);
            assertNull(result.compatibleFrames);
            assertFalse(result.findCompatibleFrames);
            assertNull(result.modelId);
            assertFalse(result.preview);
            assertEquals(1, result.models.length);

            test_iris_predict(latch, modelKey);
        }, (call, t) -> {
            fail(t, latch);
        });
    }

    private void test_iris_predict(final CountDownLatch latch, final ModelKeyV3 modelKey) {
        final FrameKeyV3 frameKey = new FrameKeyV3();
        frameKey.name = "iris.hex";
        h2oHelper.predict(modelKey, frameKey).execute((call, res) -> {
            final ModelMetricsListSchemaV3 result = res.body();
            assertEquals("", result._excludeFields);
            assertEquals("", result.customMetricFunc);
            assertEquals(-1, result.deepFeaturesHiddenLayer);
            assertEquals("", result.deepFeaturesHiddenLayerName);
            assertFalse(result.deviances);
            assertNull(result.deviancesFrame);
            assertEquals(-1, result.exemplarIndex);
            assertFalse(result.featureFrequencies);
            assertEquals("iris.hex", result.frame.name);
            assertFalse(result.leafNodeAssignment);
            assertNull(result.leafNodeAssignmentType);
            assertEquals(modelKey.name, result.model.name);
            assertFalse(result.predictContributions);
            assertNotNull(result.predictionsFrame);
            assertFalse(result.predictStagedProba);
            assertFalse(result.projectArchetypes);
            assertFalse(result.reconstructionError);
            assertFalse(result.reconstructionErrorPerFeature);
            assertFalse(result.reconstructTrain);
            assertFalse(result.reverseTransform);

            latch.countDown();
        }, (call, t) -> {
            fail(t, latch);
        });
    }

    private void sleep(final long mills) {
        try {
            Thread.sleep(mills);
        } catch (final InterruptedException e) {
            // ignore
        }
    }

    private void fail(final Throwable t, final CountDownLatch latch) {
        throwable = t;
        latch.countDown();
    }
}
