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
package org.codelibs.fione.h2o.bindings;

import java.io.IOException;
import java.lang.reflect.Array;
import java.lang.reflect.Field;
import java.lang.reflect.Type;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.TimeUnit;

import org.codelibs.fione.exception.H2oAccessException;
import org.codelibs.fione.h2o.bindings.pojos.*;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.About;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.Assembly;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.Capabilities;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.Cloud;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.CloudLock;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.ComputeGram;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.CreateFrame;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.DCTTransformer;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.DKV;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.DataInfoFrame;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.DecryptionSetup;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.DownloadDataset;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.Endpoints;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.Find;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.FrameChunks;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.Frames;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.GarbageCollect;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.GetGLMRegPath;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.Grid;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.Grids;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.ImportFiles;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.ImportFilesMulti;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.ImportHiveTable;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.ImportSQLTable;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.InitID;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.Interaction;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.JStack;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.Jobs;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.KillMinus3;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.Leaderboards;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.LogAndEcho;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.Logs;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.MakeGLMModel;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.Metadata;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.MissingInserter;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.ModelBuilders;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.ModelMetrics;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.Models;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.Modelsinfo;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.NetworkTest;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.NodePersistentStorage;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.Parse;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.ParseSVMLight;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.ParseSetup;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.PartialDependence;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.PersistS3;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.Ping;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.Predictions;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.Profiler;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.Rapids;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.Sample;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.Sessions;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.Shutdown;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.SplitFrame;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.SteamMetrics;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.Tabulate;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.TargetEncoderTransform;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.Timeline;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.Tree;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.Typeahead;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.UnlockKeys;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.WaterMeterCpuTicks;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.WaterMeterIo;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.Word2VecSynonyms;
import org.codelibs.fione.h2o.bindings.proxies.retrofit.Word2VecTransform;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonArray;
import com.google.gson.JsonDeserializationContext;
import com.google.gson.JsonDeserializer;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParseException;
import com.google.gson.JsonParser;
import com.google.gson.JsonPrimitive;
import com.google.gson.JsonSerializationContext;
import com.google.gson.JsonSerializer;
import com.google.gson.TypeAdapter;
import com.google.gson.TypeAdapterFactory;
import com.google.gson.reflect.TypeToken;
import com.google.gson.stream.JsonReader;
import com.google.gson.stream.JsonWriter;

import okhttp3.Interceptor;
import okhttp3.OkHttpClient;
import okhttp3.OkHttpClient.Builder;
import retrofit2.Call;
import retrofit2.Response;
import retrofit2.Retrofit;
import retrofit2.converter.gson.GsonConverterFactory;

@SuppressWarnings("unused")
public class H2oApi {

    public static final String DEFAULT_URL = "http://localhost:54321/";

    public H2oApi() {
        this(DEFAULT_URL);
    }

    public H2oApi(final String url) {
        this.url = url;
    }

    public H2oApi url(final String url) {
        this.url = url;
        retrofit = null;
        return this;
    }

    public H2oApi connectTimeout(final int t) {
        connectTimeout = t;
        retrofit = null;
        return this;
    }

    public H2oApi writeTimeout(final int t) {
        writeTimeout = t;
        retrofit = null;
        return this;
    }

    public H2oApi readTimeout(final int t) {
        readTimeout = t;
        retrofit = null;
        return this;
    }

    public H2oApi addInterceptor(final Interceptor interceptor) {
        interceptorList.add(interceptor);
        return this;
    }

    /**
     * Set time interval for job polling in {@link #waitForJobCompletion(JobKeyV3)}.
     *   @param millis time interval, in milliseconds
     */
    public H2oApi setJobPollInterval(final int millis) {
        pollInterval = millis;
        return this;
    }

    /**
     * Continuously poll server for the status of the given job, until it completes.
     *   @param jobKey job to query
     *   @return the finished job
     */
    public JobV3 waitForJobCompletion(final JobKeyV3 jobKey) {
        return waitForJobCompletion(keyToString(jobKey));
    }

    public JobV3 waitForJobCompletion(final String jobId) {
        final Jobs jobService = getService(Jobs.class);
        Response<JobsV3> jobsResponse = null;
        int retries = 3;
        JobsV3 jobs = null;
        do {
            try {
                Thread.sleep(pollInterval);
                jobsResponse = jobService.fetch(jobId).execute();
            } catch (final IOException e) {
                System.err.println("Caught exception: " + e);
            } catch (final InterruptedException e) { /* pass */}
            if (jobsResponse == null || !jobsResponse.isSuccessful()) {
                if (retries-- > 0) {
                    continue;
                } else {
                    throw new H2oAccessException("/3/Jobs/" + jobId + " failed 3 times.");
                }
            }
            jobs = jobsResponse.body();
            if (jobs.jobs == null || jobs.jobs.length != 1) {
                throw new H2oAccessException("Failed to find Job: " + jobId);
            }
        } while (jobs != null && jobs.jobs[0].status.equals("RUNNING"));
        return jobs == null ? null : jobs.jobs[0];
    }

    /**
     * Set Amazon S3 credentials (Secret Key ID, Secret Access Key)
     */
    public Call<PersistS3CredentialsV3> setS3Credentials(final String secretKeyId, final String secretAccessKey) {
        final PersistS3 s = getService(PersistS3.class);
        return s.setS3Credentials(secretKeyId, secretAccessKey);
    }

    /**
     * Return all the AutoML leaderboards.
     */
    public Call<LeaderboardsV99> leaderboards() {
        final Leaderboards s = getService(Leaderboards.class);
        return s.list();
    }

    public Call<LeaderboardsV99> leaderboards(final String projectName, final String[] extensions) {
        final Leaderboards s = getService(Leaderboards.class);
        return s.list(projectName, extensions, "");
    }

    public Call<LeaderboardsV99> leaderboards(final String projectName, final String[] extensions, final String _excludeFields) {
        final Leaderboards s = getService(Leaderboards.class);
        return s.list(projectName, extensions, _excludeFields);
    }

    /**
     * Return the AutoML leaderboard for the given project.
     */
    public Call<LeaderboardV99> leaderboard(final String projectName) {
        final Leaderboards s = getService(Leaderboards.class);
        return s.fetch(projectName);
    }

    public Call<LeaderboardV99> leaderboard(final String projectName, final String[] extensions) {
        final Leaderboards s = getService(Leaderboards.class);
        return s.fetch(projectName, extensions, "");
    }

    public Call<LeaderboardV99> leaderboard(final String projectName, final String[] extensions, final String _excludeFields) {
        final Leaderboards s = getService(Leaderboards.class);
        return s.fetch(projectName, extensions, _excludeFields);
    }

    /**
     * Train a XGBoost model.
     */
    public XGBoostV3 train_xgboost() throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.trainXgboost().execute().body();
    }

    public XGBoostV3 train_xgboost(final XGBoostParametersV3 params) throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.trainXgboost(params.ntrees, params.nEstimators, params.maxDepth, params.minRows, params.minChildWeight, params.learnRate,
                params.eta, params.sampleRate, params.subsample, params.colSampleRate, params.colsampleBylevel,
                params.colSampleRatePerTree, params.colsampleBytree, params.monotoneConstraints, params.maxAbsLeafnodePred,
                params.maxDeltaStep, params.scoreTreeInterval, params.seed, params.minSplitImprovement, params.gamma, params.nthread,
                params.saveMatrixDirectory, params.calibrateModel, keyToString(params.calibrationFrame), params.maxBins, params.maxLeaves,
                params.minSumHessianInLeaf, params.minDataInLeaf, params.treeMethod, params.growPolicy, params.booster, params.regLambda,
                params.regAlpha, params.quietMode, params.sampleType, params.normalizeType, params.rateDrop, params.oneDrop,
                params.skipDrop, params.dmatrixType, params.backend, params.gpuId, keyToString(params.modelId),
                keyToString(params.trainingFrame), keyToString(params.validationFrame), params.nfolds, params.keepCrossValidationModels,
                params.keepCrossValidationPredictions, params.keepCrossValidationFoldAssignment, params.parallelizeCrossValidation,
                params.distribution, params.tweediePower, params.quantileAlpha, params.huberAlpha, colToString(params.responseColumn),
                colToString(params.weightsColumn), colToString(params.offsetColumn), colToString(params.foldColumn), params.foldAssignment,
                params.categoricalEncoding, params.maxCategoricalLevels, params.ignoredColumns, params.ignoreConstCols,
                params.scoreEachIteration, keyToString(params.checkpoint), params.stoppingRounds, params.maxRuntimeSecs,
                params.stoppingMetric, params.stoppingTolerance, params.customMetricFunc, params.customDistributionFunc,
                params.exportCheckpointsDir).execute().body();
    }

    /**
     * Validate a set of XGBoost model builder parameters.
     */
    public XGBoostV3 validate_xgboost() throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.validate_parametersXgboost().execute().body();
    }

    public XGBoostV3 validate_xgboost(final XGBoostParametersV3 params) throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.validate_parametersXgboost(params.ntrees, params.nEstimators, params.maxDepth, params.minRows, params.minChildWeight,
                params.learnRate, params.eta, params.sampleRate, params.subsample, params.colSampleRate, params.colsampleBylevel,
                params.colSampleRatePerTree, params.colsampleBytree, params.monotoneConstraints, params.maxAbsLeafnodePred,
                params.maxDeltaStep, params.scoreTreeInterval, params.seed, params.minSplitImprovement, params.gamma, params.nthread,
                params.saveMatrixDirectory, params.calibrateModel, keyToString(params.calibrationFrame), params.maxBins, params.maxLeaves,
                params.minSumHessianInLeaf, params.minDataInLeaf, params.treeMethod, params.growPolicy, params.booster, params.regLambda,
                params.regAlpha, params.quietMode, params.sampleType, params.normalizeType, params.rateDrop, params.oneDrop,
                params.skipDrop, params.dmatrixType, params.backend, params.gpuId, keyToString(params.modelId),
                keyToString(params.trainingFrame), keyToString(params.validationFrame), params.nfolds, params.keepCrossValidationModels,
                params.keepCrossValidationPredictions, params.keepCrossValidationFoldAssignment, params.parallelizeCrossValidation,
                params.distribution, params.tweediePower, params.quantileAlpha, params.huberAlpha, colToString(params.responseColumn),
                colToString(params.weightsColumn), colToString(params.offsetColumn), colToString(params.foldColumn), params.foldAssignment,
                params.categoricalEncoding, params.maxCategoricalLevels, params.ignoredColumns, params.ignoreConstCols,
                params.scoreEachIteration, keyToString(params.checkpoint), params.stoppingRounds, params.maxRuntimeSecs,
                params.stoppingMetric, params.stoppingTolerance, params.customMetricFunc, params.customDistributionFunc,
                params.exportCheckpointsDir).execute().body();
    }

    /**
     * Run grid search for XGBoost model.
     */
    public XGBoostV3 grid_search_xgboost() throws IOException {
        final Grid s = getService(Grid.class);
        return s.trainXgboost().execute().body();
    }

    public XGBoostV3 grid_search_xgboost(final XGBoostParametersV3 params) throws IOException {
        final Grid s = getService(Grid.class);
        return s.trainXgboost(params.ntrees, params.nEstimators, params.maxDepth, params.minRows, params.minChildWeight, params.learnRate,
                params.eta, params.sampleRate, params.subsample, params.colSampleRate, params.colsampleBylevel,
                params.colSampleRatePerTree, params.colsampleBytree, params.monotoneConstraints, params.maxAbsLeafnodePred,
                params.maxDeltaStep, params.scoreTreeInterval, params.seed, params.minSplitImprovement, params.gamma, params.nthread,
                params.saveMatrixDirectory, params.calibrateModel, keyToString(params.calibrationFrame), params.maxBins, params.maxLeaves,
                params.minSumHessianInLeaf, params.minDataInLeaf, params.treeMethod, params.growPolicy, params.booster, params.regLambda,
                params.regAlpha, params.quietMode, params.sampleType, params.normalizeType, params.rateDrop, params.oneDrop,
                params.skipDrop, params.dmatrixType, params.backend, params.gpuId, keyToString(params.modelId),
                keyToString(params.trainingFrame), keyToString(params.validationFrame), params.nfolds, params.keepCrossValidationModels,
                params.keepCrossValidationPredictions, params.keepCrossValidationFoldAssignment, params.parallelizeCrossValidation,
                params.distribution, params.tweediePower, params.quantileAlpha, params.huberAlpha, colToString(params.responseColumn),
                colToString(params.weightsColumn), colToString(params.offsetColumn), colToString(params.foldColumn), params.foldAssignment,
                params.categoricalEncoding, params.maxCategoricalLevels, params.ignoredColumns, params.ignoreConstCols,
                params.scoreEachIteration, keyToString(params.checkpoint), params.stoppingRounds, params.maxRuntimeSecs,
                params.stoppingMetric, params.stoppingTolerance, params.customMetricFunc, params.customDistributionFunc,
                params.exportCheckpointsDir).execute().body();
    }

    /**
     * Train a TargetEncoderBuilder model.
     */
    public TargetEncoderV3 train_targetencoder() throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.trainTargetencoder().execute().body();
    }

    public TargetEncoderV3 train_targetencoder(final TargetEncoderParametersV3 params) throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.trainTargetencoder(params.blending, params.k, params.f, params.dataLeakageHandling, params.noiseLevel, params.seed,
                keyToString(params.modelId), keyToString(params.trainingFrame), keyToString(params.validationFrame), params.nfolds,
                params.keepCrossValidationModels, params.keepCrossValidationPredictions, params.keepCrossValidationFoldAssignment,
                params.parallelizeCrossValidation, params.distribution, params.tweediePower, params.quantileAlpha, params.huberAlpha,
                colToString(params.responseColumn), colToString(params.weightsColumn), colToString(params.offsetColumn),
                colToString(params.foldColumn), params.foldAssignment, params.categoricalEncoding, params.maxCategoricalLevels,
                params.ignoredColumns, params.ignoreConstCols, params.scoreEachIteration, keyToString(params.checkpoint),
                params.stoppingRounds, params.maxRuntimeSecs, params.stoppingMetric, params.stoppingTolerance, params.customMetricFunc,
                params.customDistributionFunc, params.exportCheckpointsDir).execute().body();
    }

    /**
     * Validate a set of TargetEncoderBuilder model builder parameters.
     */
    public TargetEncoderV3 validate_targetencoder() throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.validate_parametersTargetencoder().execute().body();
    }

    public TargetEncoderV3 validate_targetencoder(final TargetEncoderParametersV3 params) throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.validate_parametersTargetencoder(params.blending, params.k, params.f, params.dataLeakageHandling, params.noiseLevel,
                params.seed, keyToString(params.modelId), keyToString(params.trainingFrame), keyToString(params.validationFrame),
                params.nfolds, params.keepCrossValidationModels, params.keepCrossValidationPredictions,
                params.keepCrossValidationFoldAssignment, params.parallelizeCrossValidation, params.distribution, params.tweediePower,
                params.quantileAlpha, params.huberAlpha, colToString(params.responseColumn), colToString(params.weightsColumn),
                colToString(params.offsetColumn), colToString(params.foldColumn), params.foldAssignment, params.categoricalEncoding,
                params.maxCategoricalLevels, params.ignoredColumns, params.ignoreConstCols, params.scoreEachIteration,
                keyToString(params.checkpoint), params.stoppingRounds, params.maxRuntimeSecs, params.stoppingMetric,
                params.stoppingTolerance, params.customMetricFunc, params.customDistributionFunc, params.exportCheckpointsDir).execute()
                .body();
    }

    /**
     * Run grid search for TargetEncoderBuilder model.
     */
    public TargetEncoderV3 grid_search_targetencoder() throws IOException {
        final Grid s = getService(Grid.class);
        return s.trainTargetencoder().execute().body();
    }

    public TargetEncoderV3 grid_search_targetencoder(final TargetEncoderParametersV3 params) throws IOException {
        final Grid s = getService(Grid.class);
        return s.trainTargetencoder(params.blending, params.k, params.f, params.dataLeakageHandling, params.noiseLevel, params.seed,
                keyToString(params.modelId), keyToString(params.trainingFrame), keyToString(params.validationFrame), params.nfolds,
                params.keepCrossValidationModels, params.keepCrossValidationPredictions, params.keepCrossValidationFoldAssignment,
                params.parallelizeCrossValidation, params.distribution, params.tweediePower, params.quantileAlpha, params.huberAlpha,
                colToString(params.responseColumn), colToString(params.weightsColumn), colToString(params.offsetColumn),
                colToString(params.foldColumn), params.foldAssignment, params.categoricalEncoding, params.maxCategoricalLevels,
                params.ignoredColumns, params.ignoreConstCols, params.scoreEachIteration, keyToString(params.checkpoint),
                params.stoppingRounds, params.maxRuntimeSecs, params.stoppingMetric, params.stoppingTolerance, params.customMetricFunc,
                params.customDistributionFunc, params.exportCheckpointsDir).execute().body();
    }

    /**
     * Transform using give TargetEncoderModel
     */
    public FrameKeyV3 target_encoder_transform() throws IOException {
        final TargetEncoderTransform s = getService(TargetEncoderTransform.class);
        return s.transform().execute().body();
    }

    public FrameKeyV3 target_encoder_transform(final TargetEncoderTransformParametersV3 params) throws IOException {
        final TargetEncoderTransform s = getService(TargetEncoderTransform.class);
        return s.transform(keyToString(params.model), params.seed, params.dataLeakageHandling, params.noise, keyToString(params.frame),
                params.blending, params.inflectionPoint, params.smoothing).execute().body();
    }

    /**
     * Train a DeepLearning model.
     */
    public DeepLearningV3 train_deeplearning() throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.trainDeeplearning().execute().body();
    }

    public DeepLearningV3 train_deeplearning(final DeepLearningParametersV3 params) throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.trainDeeplearning(params.balanceClasses, params.classSamplingFactors, params.maxAfterBalanceSize,
                params.maxConfusionMatrixSize, params.maxHitRatioK, params.activation, params.hidden, params.epochs,
                params.trainSamplesPerIteration, params.targetRatioCommToComp, params.seed, params.adaptiveRate, params.rho,
                params.epsilon, params.rate, params.rateAnnealing, params.rateDecay, params.momentumStart, params.momentumRamp,
                params.momentumStable, params.nesterovAcceleratedGradient, params.inputDropoutRatio, params.hiddenDropoutRatios, params.l1,
                params.l2, params.maxW2, params.initialWeightDistribution, params.initialWeightScale,
                keyArrayToStringArray(params.initialWeights), keyArrayToStringArray(params.initialBiases), params.loss,
                params.scoreInterval, params.scoreTrainingSamples, params.scoreValidationSamples, params.scoreDutyCycle,
                params.classificationStop, params.regressionStop, params.quietMode, params.scoreValidationSampling,
                params.overwriteWithBestModel, params.autoencoder, params.useAllFactorLevels, params.standardize, params.diagnostics,
                params.variableImportances, params.fastMode, params.forceLoadBalance, params.replicateTrainingData, params.singleNodeMode,
                params.shuffleTrainingData, params.missingValuesHandling, params.sparse, params.colMajor, params.averageActivation,
                params.sparsityBeta, params.maxCategoricalFeatures, params.reproducible, params.exportWeightsAndBiases,
                params.miniBatchSize, params.elasticAveraging, params.elasticAveragingMovingRate, params.elasticAveragingRegularization,
                keyToString(params.pretrainedAutoencoder), keyToString(params.modelId), keyToString(params.trainingFrame),
                keyToString(params.validationFrame), params.nfolds, params.keepCrossValidationModels,
                params.keepCrossValidationPredictions, params.keepCrossValidationFoldAssignment, params.parallelizeCrossValidation,
                params.distribution, params.tweediePower, params.quantileAlpha, params.huberAlpha, colToString(params.responseColumn),
                colToString(params.weightsColumn), colToString(params.offsetColumn), colToString(params.foldColumn), params.foldAssignment,
                params.categoricalEncoding, params.maxCategoricalLevels, params.ignoredColumns, params.ignoreConstCols,
                params.scoreEachIteration, keyToString(params.checkpoint), params.stoppingRounds, params.maxRuntimeSecs,
                params.stoppingMetric, params.stoppingTolerance, params.customMetricFunc, params.customDistributionFunc,
                params.exportCheckpointsDir).execute().body();
    }

    /**
     * Validate a set of DeepLearning model builder parameters.
     */
    public DeepLearningV3 validate_deeplearning() throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.validate_parametersDeeplearning().execute().body();
    }

    public DeepLearningV3 validate_deeplearning(final DeepLearningParametersV3 params) throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.validate_parametersDeeplearning(params.balanceClasses, params.classSamplingFactors, params.maxAfterBalanceSize,
                params.maxConfusionMatrixSize, params.maxHitRatioK, params.activation, params.hidden, params.epochs,
                params.trainSamplesPerIteration, params.targetRatioCommToComp, params.seed, params.adaptiveRate, params.rho,
                params.epsilon, params.rate, params.rateAnnealing, params.rateDecay, params.momentumStart, params.momentumRamp,
                params.momentumStable, params.nesterovAcceleratedGradient, params.inputDropoutRatio, params.hiddenDropoutRatios, params.l1,
                params.l2, params.maxW2, params.initialWeightDistribution, params.initialWeightScale,
                keyArrayToStringArray(params.initialWeights), keyArrayToStringArray(params.initialBiases), params.loss,
                params.scoreInterval, params.scoreTrainingSamples, params.scoreValidationSamples, params.scoreDutyCycle,
                params.classificationStop, params.regressionStop, params.quietMode, params.scoreValidationSampling,
                params.overwriteWithBestModel, params.autoencoder, params.useAllFactorLevels, params.standardize, params.diagnostics,
                params.variableImportances, params.fastMode, params.forceLoadBalance, params.replicateTrainingData, params.singleNodeMode,
                params.shuffleTrainingData, params.missingValuesHandling, params.sparse, params.colMajor, params.averageActivation,
                params.sparsityBeta, params.maxCategoricalFeatures, params.reproducible, params.exportWeightsAndBiases,
                params.miniBatchSize, params.elasticAveraging, params.elasticAveragingMovingRate, params.elasticAveragingRegularization,
                keyToString(params.pretrainedAutoencoder), keyToString(params.modelId), keyToString(params.trainingFrame),
                keyToString(params.validationFrame), params.nfolds, params.keepCrossValidationModels,
                params.keepCrossValidationPredictions, params.keepCrossValidationFoldAssignment, params.parallelizeCrossValidation,
                params.distribution, params.tweediePower, params.quantileAlpha, params.huberAlpha, colToString(params.responseColumn),
                colToString(params.weightsColumn), colToString(params.offsetColumn), colToString(params.foldColumn), params.foldAssignment,
                params.categoricalEncoding, params.maxCategoricalLevels, params.ignoredColumns, params.ignoreConstCols,
                params.scoreEachIteration, keyToString(params.checkpoint), params.stoppingRounds, params.maxRuntimeSecs,
                params.stoppingMetric, params.stoppingTolerance, params.customMetricFunc, params.customDistributionFunc,
                params.exportCheckpointsDir).execute().body();
    }

    /**
     * Run grid search for DeepLearning model.
     */
    public DeepLearningV3 grid_search_deeplearning() throws IOException {
        final Grid s = getService(Grid.class);
        return s.trainDeeplearning().execute().body();
    }

    public DeepLearningV3 grid_search_deeplearning(final DeepLearningParametersV3 params) throws IOException {
        final Grid s = getService(Grid.class);
        return s.trainDeeplearning(params.balanceClasses, params.classSamplingFactors, params.maxAfterBalanceSize,
                params.maxConfusionMatrixSize, params.maxHitRatioK, params.activation, params.hidden, params.epochs,
                params.trainSamplesPerIteration, params.targetRatioCommToComp, params.seed, params.adaptiveRate, params.rho,
                params.epsilon, params.rate, params.rateAnnealing, params.rateDecay, params.momentumStart, params.momentumRamp,
                params.momentumStable, params.nesterovAcceleratedGradient, params.inputDropoutRatio, params.hiddenDropoutRatios, params.l1,
                params.l2, params.maxW2, params.initialWeightDistribution, params.initialWeightScale,
                keyArrayToStringArray(params.initialWeights), keyArrayToStringArray(params.initialBiases), params.loss,
                params.scoreInterval, params.scoreTrainingSamples, params.scoreValidationSamples, params.scoreDutyCycle,
                params.classificationStop, params.regressionStop, params.quietMode, params.scoreValidationSampling,
                params.overwriteWithBestModel, params.autoencoder, params.useAllFactorLevels, params.standardize, params.diagnostics,
                params.variableImportances, params.fastMode, params.forceLoadBalance, params.replicateTrainingData, params.singleNodeMode,
                params.shuffleTrainingData, params.missingValuesHandling, params.sparse, params.colMajor, params.averageActivation,
                params.sparsityBeta, params.maxCategoricalFeatures, params.reproducible, params.exportWeightsAndBiases,
                params.miniBatchSize, params.elasticAveraging, params.elasticAveragingMovingRate, params.elasticAveragingRegularization,
                keyToString(params.pretrainedAutoencoder), keyToString(params.modelId), keyToString(params.trainingFrame),
                keyToString(params.validationFrame), params.nfolds, params.keepCrossValidationModels,
                params.keepCrossValidationPredictions, params.keepCrossValidationFoldAssignment, params.parallelizeCrossValidation,
                params.distribution, params.tweediePower, params.quantileAlpha, params.huberAlpha, colToString(params.responseColumn),
                colToString(params.weightsColumn), colToString(params.offsetColumn), colToString(params.foldColumn), params.foldAssignment,
                params.categoricalEncoding, params.maxCategoricalLevels, params.ignoredColumns, params.ignoreConstCols,
                params.scoreEachIteration, keyToString(params.checkpoint), params.stoppingRounds, params.maxRuntimeSecs,
                params.stoppingMetric, params.stoppingTolerance, params.customMetricFunc, params.customDistributionFunc,
                params.exportCheckpointsDir).execute().body();
    }

    /**
     * Train a GLM model.
     */
    public GLMV3 train_glm() throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.trainGlm().execute().body();
    }

    public GLMV3 train_glm(final GLMParametersV3 params) throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.trainGlm(params.seed, params.family, params.randFamily, params.tweedieVariancePower, params.tweedieLinkPower,
                params.theta, params.solver, params.alpha, params.lambda, params.lambdaSearch, params.earlyStopping, params.nlambdas,
                params.standardize, params.missingValuesHandling, keyToString(params.plugValues), params.nonNegative, params.maxIterations,
                params.betaEpsilon, params.objectiveEpsilon, params.gradientEpsilon, params.objReg, params.link, params.randLink,
                params.startval, params.randomColumns, params.calcLike, params.intercept, params.hglm, params.prior, params.lambdaMinRatio,
                keyToString(params.betaConstraints), params.maxActivePredictors, params.interactions, params.interactionPairs,
                params.balanceClasses, params.classSamplingFactors, params.maxAfterBalanceSize, params.maxConfusionMatrixSize,
                params.maxHitRatioK, params.computePValues, params.removeCollinearColumns, keyToString(params.modelId),
                keyToString(params.trainingFrame), keyToString(params.validationFrame), params.nfolds, params.keepCrossValidationModels,
                params.keepCrossValidationPredictions, params.keepCrossValidationFoldAssignment, params.parallelizeCrossValidation,
                params.distribution, params.tweediePower, params.quantileAlpha, params.huberAlpha, colToString(params.responseColumn),
                colToString(params.weightsColumn), colToString(params.offsetColumn), colToString(params.foldColumn), params.foldAssignment,
                params.categoricalEncoding, params.maxCategoricalLevels, params.ignoredColumns, params.ignoreConstCols,
                params.scoreEachIteration, keyToString(params.checkpoint), params.stoppingRounds, params.maxRuntimeSecs,
                params.stoppingMetric, params.stoppingTolerance, params.customMetricFunc, params.customDistributionFunc,
                params.exportCheckpointsDir).execute().body();
    }

    /**
     * Validate a set of GLM model builder parameters.
     */
    public GLMV3 validate_glm() throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.validate_parametersGlm().execute().body();
    }

    public GLMV3 validate_glm(final GLMParametersV3 params) throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.validate_parametersGlm(params.seed, params.family, params.randFamily, params.tweedieVariancePower,
                params.tweedieLinkPower, params.theta, params.solver, params.alpha, params.lambda, params.lambdaSearch,
                params.earlyStopping, params.nlambdas, params.standardize, params.missingValuesHandling, keyToString(params.plugValues),
                params.nonNegative, params.maxIterations, params.betaEpsilon, params.objectiveEpsilon, params.gradientEpsilon,
                params.objReg, params.link, params.randLink, params.startval, params.randomColumns, params.calcLike, params.intercept,
                params.hglm, params.prior, params.lambdaMinRatio, keyToString(params.betaConstraints), params.maxActivePredictors,
                params.interactions, params.interactionPairs, params.balanceClasses, params.classSamplingFactors,
                params.maxAfterBalanceSize, params.maxConfusionMatrixSize, params.maxHitRatioK, params.computePValues,
                params.removeCollinearColumns, keyToString(params.modelId), keyToString(params.trainingFrame),
                keyToString(params.validationFrame), params.nfolds, params.keepCrossValidationModels,
                params.keepCrossValidationPredictions, params.keepCrossValidationFoldAssignment, params.parallelizeCrossValidation,
                params.distribution, params.tweediePower, params.quantileAlpha, params.huberAlpha, colToString(params.responseColumn),
                colToString(params.weightsColumn), colToString(params.offsetColumn), colToString(params.foldColumn), params.foldAssignment,
                params.categoricalEncoding, params.maxCategoricalLevels, params.ignoredColumns, params.ignoreConstCols,
                params.scoreEachIteration, keyToString(params.checkpoint), params.stoppingRounds, params.maxRuntimeSecs,
                params.stoppingMetric, params.stoppingTolerance, params.customMetricFunc, params.customDistributionFunc,
                params.exportCheckpointsDir).execute().body();
    }

    /**
     * Run grid search for GLM model.
     */
    public GLMV3 grid_search_glm() throws IOException {
        final Grid s = getService(Grid.class);
        return s.trainGlm().execute().body();
    }

    public GLMV3 grid_search_glm(final GLMParametersV3 params) throws IOException {
        final Grid s = getService(Grid.class);
        return s.trainGlm(params.seed, params.family, params.randFamily, params.tweedieVariancePower, params.tweedieLinkPower,
                params.theta, params.solver, params.alpha, params.lambda, params.lambdaSearch, params.earlyStopping, params.nlambdas,
                params.standardize, params.missingValuesHandling, keyToString(params.plugValues), params.nonNegative, params.maxIterations,
                params.betaEpsilon, params.objectiveEpsilon, params.gradientEpsilon, params.objReg, params.link, params.randLink,
                params.startval, params.randomColumns, params.calcLike, params.intercept, params.hglm, params.prior, params.lambdaMinRatio,
                keyToString(params.betaConstraints), params.maxActivePredictors, params.interactions, params.interactionPairs,
                params.balanceClasses, params.classSamplingFactors, params.maxAfterBalanceSize, params.maxConfusionMatrixSize,
                params.maxHitRatioK, params.computePValues, params.removeCollinearColumns, keyToString(params.modelId),
                keyToString(params.trainingFrame), keyToString(params.validationFrame), params.nfolds, params.keepCrossValidationModels,
                params.keepCrossValidationPredictions, params.keepCrossValidationFoldAssignment, params.parallelizeCrossValidation,
                params.distribution, params.tweediePower, params.quantileAlpha, params.huberAlpha, colToString(params.responseColumn),
                colToString(params.weightsColumn), colToString(params.offsetColumn), colToString(params.foldColumn), params.foldAssignment,
                params.categoricalEncoding, params.maxCategoricalLevels, params.ignoredColumns, params.ignoreConstCols,
                params.scoreEachIteration, keyToString(params.checkpoint), params.stoppingRounds, params.maxRuntimeSecs,
                params.stoppingMetric, params.stoppingTolerance, params.customMetricFunc, params.customDistributionFunc,
                params.exportCheckpointsDir).execute().body();
    }

    /**
     * Train a GLRM model.
     */
    public GLRMV3 train_glrm(final int k) throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.trainGlrm(k).execute().body();
    }

    public GLRMV3 train_glrm(final GLRMParametersV3 params) throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.trainGlrm(params.transform, params.k, params.loss, params.multiLoss, params.lossByCol, params.lossByColIdx, params.period,
                params.regularizationX, params.regularizationY, params.gammaX, params.gammaY, params.maxIterations, params.maxUpdates,
                params.initStepSize, params.minStepSize, params.seed, params.init, params.svdMethod, keyToString(params.userY),
                keyToString(params.userX), params.loadingName, params.expandUserY, params.imputeOriginal, params.recoverSvd,
                keyToString(params.modelId), keyToString(params.trainingFrame), keyToString(params.validationFrame), params.nfolds,
                params.keepCrossValidationModels, params.keepCrossValidationPredictions, params.keepCrossValidationFoldAssignment,
                params.parallelizeCrossValidation, params.distribution, params.tweediePower, params.quantileAlpha, params.huberAlpha,
                colToString(params.responseColumn), colToString(params.weightsColumn), colToString(params.offsetColumn),
                colToString(params.foldColumn), params.foldAssignment, params.categoricalEncoding, params.maxCategoricalLevels,
                params.ignoredColumns, params.ignoreConstCols, params.scoreEachIteration, keyToString(params.checkpoint),
                params.stoppingRounds, params.maxRuntimeSecs, params.stoppingMetric, params.stoppingTolerance, params.customMetricFunc,
                params.customDistributionFunc, params.exportCheckpointsDir).execute().body();
    }

    /**
     * Validate a set of GLRM model builder parameters.
     */
    public GLRMV3 validate_glrm(final int k) throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.validate_parametersGlrm(k).execute().body();
    }

    public GLRMV3 validate_glrm(final GLRMParametersV3 params) throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.validate_parametersGlrm(params.transform, params.k, params.loss, params.multiLoss, params.lossByCol, params.lossByColIdx,
                params.period, params.regularizationX, params.regularizationY, params.gammaX, params.gammaY, params.maxIterations,
                params.maxUpdates, params.initStepSize, params.minStepSize, params.seed, params.init, params.svdMethod,
                keyToString(params.userY), keyToString(params.userX), params.loadingName, params.expandUserY, params.imputeOriginal,
                params.recoverSvd, keyToString(params.modelId), keyToString(params.trainingFrame), keyToString(params.validationFrame),
                params.nfolds, params.keepCrossValidationModels, params.keepCrossValidationPredictions,
                params.keepCrossValidationFoldAssignment, params.parallelizeCrossValidation, params.distribution, params.tweediePower,
                params.quantileAlpha, params.huberAlpha, colToString(params.responseColumn), colToString(params.weightsColumn),
                colToString(params.offsetColumn), colToString(params.foldColumn), params.foldAssignment, params.categoricalEncoding,
                params.maxCategoricalLevels, params.ignoredColumns, params.ignoreConstCols, params.scoreEachIteration,
                keyToString(params.checkpoint), params.stoppingRounds, params.maxRuntimeSecs, params.stoppingMetric,
                params.stoppingTolerance, params.customMetricFunc, params.customDistributionFunc, params.exportCheckpointsDir).execute()
                .body();
    }

    /**
     * Run grid search for GLRM model.
     */
    public GLRMV3 grid_search_glrm(final int k) throws IOException {
        final Grid s = getService(Grid.class);
        return s.trainGlrm(k).execute().body();
    }

    public GLRMV3 grid_search_glrm(final GLRMParametersV3 params) throws IOException {
        final Grid s = getService(Grid.class);
        return s.trainGlrm(params.transform, params.k, params.loss, params.multiLoss, params.lossByCol, params.lossByColIdx, params.period,
                params.regularizationX, params.regularizationY, params.gammaX, params.gammaY, params.maxIterations, params.maxUpdates,
                params.initStepSize, params.minStepSize, params.seed, params.init, params.svdMethod, keyToString(params.userY),
                keyToString(params.userX), params.loadingName, params.expandUserY, params.imputeOriginal, params.recoverSvd,
                keyToString(params.modelId), keyToString(params.trainingFrame), keyToString(params.validationFrame), params.nfolds,
                params.keepCrossValidationModels, params.keepCrossValidationPredictions, params.keepCrossValidationFoldAssignment,
                params.parallelizeCrossValidation, params.distribution, params.tweediePower, params.quantileAlpha, params.huberAlpha,
                colToString(params.responseColumn), colToString(params.weightsColumn), colToString(params.offsetColumn),
                colToString(params.foldColumn), params.foldAssignment, params.categoricalEncoding, params.maxCategoricalLevels,
                params.ignoredColumns, params.ignoreConstCols, params.scoreEachIteration, keyToString(params.checkpoint),
                params.stoppingRounds, params.maxRuntimeSecs, params.stoppingMetric, params.stoppingTolerance, params.customMetricFunc,
                params.customDistributionFunc, params.exportCheckpointsDir).execute().body();
    }

    /**
     * Train a KMeans model.
     */
    public KMeansV3 train_kmeans() throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.trainKmeans().execute().body();
    }

    public KMeansV3 train_kmeans(final KMeansParametersV3 params) throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.trainKmeans(keyToString(params.userPoints), params.maxIterations, params.standardize, params.seed, params.init,
                params.estimateK, params.k, keyToString(params.modelId), keyToString(params.trainingFrame),
                keyToString(params.validationFrame), params.nfolds, params.keepCrossValidationModels,
                params.keepCrossValidationPredictions, params.keepCrossValidationFoldAssignment, params.parallelizeCrossValidation,
                params.distribution, params.tweediePower, params.quantileAlpha, params.huberAlpha, colToString(params.responseColumn),
                colToString(params.weightsColumn), colToString(params.offsetColumn), colToString(params.foldColumn), params.foldAssignment,
                params.categoricalEncoding, params.maxCategoricalLevels, params.ignoredColumns, params.ignoreConstCols,
                params.scoreEachIteration, keyToString(params.checkpoint), params.stoppingRounds, params.maxRuntimeSecs,
                params.stoppingMetric, params.stoppingTolerance, params.customMetricFunc, params.customDistributionFunc,
                params.exportCheckpointsDir).execute().body();
    }

    /**
     * Validate a set of KMeans model builder parameters.
     */
    public KMeansV3 validate_kmeans() throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.validate_parametersKmeans().execute().body();
    }

    public KMeansV3 validate_kmeans(final KMeansParametersV3 params) throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.validate_parametersKmeans(keyToString(params.userPoints), params.maxIterations, params.standardize, params.seed,
                params.init, params.estimateK, params.k, keyToString(params.modelId), keyToString(params.trainingFrame),
                keyToString(params.validationFrame), params.nfolds, params.keepCrossValidationModels,
                params.keepCrossValidationPredictions, params.keepCrossValidationFoldAssignment, params.parallelizeCrossValidation,
                params.distribution, params.tweediePower, params.quantileAlpha, params.huberAlpha, colToString(params.responseColumn),
                colToString(params.weightsColumn), colToString(params.offsetColumn), colToString(params.foldColumn), params.foldAssignment,
                params.categoricalEncoding, params.maxCategoricalLevels, params.ignoredColumns, params.ignoreConstCols,
                params.scoreEachIteration, keyToString(params.checkpoint), params.stoppingRounds, params.maxRuntimeSecs,
                params.stoppingMetric, params.stoppingTolerance, params.customMetricFunc, params.customDistributionFunc,
                params.exportCheckpointsDir).execute().body();
    }

    /**
     * Run grid search for KMeans model.
     */
    public KMeansV3 grid_search_kmeans() throws IOException {
        final Grid s = getService(Grid.class);
        return s.trainKmeans().execute().body();
    }

    public KMeansV3 grid_search_kmeans(final KMeansParametersV3 params) throws IOException {
        final Grid s = getService(Grid.class);
        return s.trainKmeans(keyToString(params.userPoints), params.maxIterations, params.standardize, params.seed, params.init,
                params.estimateK, params.k, keyToString(params.modelId), keyToString(params.trainingFrame),
                keyToString(params.validationFrame), params.nfolds, params.keepCrossValidationModels,
                params.keepCrossValidationPredictions, params.keepCrossValidationFoldAssignment, params.parallelizeCrossValidation,
                params.distribution, params.tweediePower, params.quantileAlpha, params.huberAlpha, colToString(params.responseColumn),
                colToString(params.weightsColumn), colToString(params.offsetColumn), colToString(params.foldColumn), params.foldAssignment,
                params.categoricalEncoding, params.maxCategoricalLevels, params.ignoredColumns, params.ignoreConstCols,
                params.scoreEachIteration, keyToString(params.checkpoint), params.stoppingRounds, params.maxRuntimeSecs,
                params.stoppingMetric, params.stoppingTolerance, params.customMetricFunc, params.customDistributionFunc,
                params.exportCheckpointsDir).execute().body();
    }

    /**
     * Train a NaiveBayes model.
     */
    public NaiveBayesV3 train_naivebayes() throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.trainNaivebayes().execute().body();
    }

    public NaiveBayesV3 train_naivebayes(final NaiveBayesParametersV3 params) throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.trainNaivebayes(params.balanceClasses, params.classSamplingFactors, params.maxAfterBalanceSize,
                params.maxConfusionMatrixSize, params.maxHitRatioK, params.laplace, params.minSdev, params.epsSdev, params.minProb,
                params.epsProb, params.computeMetrics, params.seed, keyToString(params.modelId), keyToString(params.trainingFrame),
                keyToString(params.validationFrame), params.nfolds, params.keepCrossValidationModels,
                params.keepCrossValidationPredictions, params.keepCrossValidationFoldAssignment, params.parallelizeCrossValidation,
                params.distribution, params.tweediePower, params.quantileAlpha, params.huberAlpha, colToString(params.responseColumn),
                colToString(params.weightsColumn), colToString(params.offsetColumn), colToString(params.foldColumn), params.foldAssignment,
                params.categoricalEncoding, params.maxCategoricalLevels, params.ignoredColumns, params.ignoreConstCols,
                params.scoreEachIteration, keyToString(params.checkpoint), params.stoppingRounds, params.maxRuntimeSecs,
                params.stoppingMetric, params.stoppingTolerance, params.customMetricFunc, params.customDistributionFunc,
                params.exportCheckpointsDir).execute().body();
    }

    /**
     * Validate a set of NaiveBayes model builder parameters.
     */
    public NaiveBayesV3 validate_naivebayes() throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.validate_parametersNaivebayes().execute().body();
    }

    public NaiveBayesV3 validate_naivebayes(final NaiveBayesParametersV3 params) throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.validate_parametersNaivebayes(params.balanceClasses, params.classSamplingFactors, params.maxAfterBalanceSize,
                params.maxConfusionMatrixSize, params.maxHitRatioK, params.laplace, params.minSdev, params.epsSdev, params.minProb,
                params.epsProb, params.computeMetrics, params.seed, keyToString(params.modelId), keyToString(params.trainingFrame),
                keyToString(params.validationFrame), params.nfolds, params.keepCrossValidationModels,
                params.keepCrossValidationPredictions, params.keepCrossValidationFoldAssignment, params.parallelizeCrossValidation,
                params.distribution, params.tweediePower, params.quantileAlpha, params.huberAlpha, colToString(params.responseColumn),
                colToString(params.weightsColumn), colToString(params.offsetColumn), colToString(params.foldColumn), params.foldAssignment,
                params.categoricalEncoding, params.maxCategoricalLevels, params.ignoredColumns, params.ignoreConstCols,
                params.scoreEachIteration, keyToString(params.checkpoint), params.stoppingRounds, params.maxRuntimeSecs,
                params.stoppingMetric, params.stoppingTolerance, params.customMetricFunc, params.customDistributionFunc,
                params.exportCheckpointsDir).execute().body();
    }

    /**
     * Run grid search for NaiveBayes model.
     */
    public NaiveBayesV3 grid_search_naivebayes() throws IOException {
        final Grid s = getService(Grid.class);
        return s.trainNaivebayes().execute().body();
    }

    public NaiveBayesV3 grid_search_naivebayes(final NaiveBayesParametersV3 params) throws IOException {
        final Grid s = getService(Grid.class);
        return s.trainNaivebayes(params.balanceClasses, params.classSamplingFactors, params.maxAfterBalanceSize,
                params.maxConfusionMatrixSize, params.maxHitRatioK, params.laplace, params.minSdev, params.epsSdev, params.minProb,
                params.epsProb, params.computeMetrics, params.seed, keyToString(params.modelId), keyToString(params.trainingFrame),
                keyToString(params.validationFrame), params.nfolds, params.keepCrossValidationModels,
                params.keepCrossValidationPredictions, params.keepCrossValidationFoldAssignment, params.parallelizeCrossValidation,
                params.distribution, params.tweediePower, params.quantileAlpha, params.huberAlpha, colToString(params.responseColumn),
                colToString(params.weightsColumn), colToString(params.offsetColumn), colToString(params.foldColumn), params.foldAssignment,
                params.categoricalEncoding, params.maxCategoricalLevels, params.ignoredColumns, params.ignoreConstCols,
                params.scoreEachIteration, keyToString(params.checkpoint), params.stoppingRounds, params.maxRuntimeSecs,
                params.stoppingMetric, params.stoppingTolerance, params.customMetricFunc, params.customDistributionFunc,
                params.exportCheckpointsDir).execute().body();
    }

    /**
     * Train a PCA model.
     */
    public PCAV3 train_pca(final int k) throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.trainPca(k).execute().body();
    }

    public PCAV3 train_pca(final PCAParametersV3 params) throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.trainPca(params.transform, params.pcaMethod, params.pcaImpl, params.k, params.maxIterations, params.seed,
                params.useAllFactorLevels, params.computeMetrics, params.imputeMissing, keyToString(params.modelId),
                keyToString(params.trainingFrame), keyToString(params.validationFrame), params.nfolds, params.keepCrossValidationModels,
                params.keepCrossValidationPredictions, params.keepCrossValidationFoldAssignment, params.parallelizeCrossValidation,
                params.distribution, params.tweediePower, params.quantileAlpha, params.huberAlpha, colToString(params.responseColumn),
                colToString(params.weightsColumn), colToString(params.offsetColumn), colToString(params.foldColumn), params.foldAssignment,
                params.categoricalEncoding, params.maxCategoricalLevels, params.ignoredColumns, params.ignoreConstCols,
                params.scoreEachIteration, keyToString(params.checkpoint), params.stoppingRounds, params.maxRuntimeSecs,
                params.stoppingMetric, params.stoppingTolerance, params.customMetricFunc, params.customDistributionFunc,
                params.exportCheckpointsDir).execute().body();
    }

    /**
     * Validate a set of PCA model builder parameters.
     */
    public PCAV3 validate_pca(final int k) throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.validate_parametersPca(k).execute().body();
    }

    public PCAV3 validate_pca(final PCAParametersV3 params) throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.validate_parametersPca(params.transform, params.pcaMethod, params.pcaImpl, params.k, params.maxIterations, params.seed,
                params.useAllFactorLevels, params.computeMetrics, params.imputeMissing, keyToString(params.modelId),
                keyToString(params.trainingFrame), keyToString(params.validationFrame), params.nfolds, params.keepCrossValidationModels,
                params.keepCrossValidationPredictions, params.keepCrossValidationFoldAssignment, params.parallelizeCrossValidation,
                params.distribution, params.tweediePower, params.quantileAlpha, params.huberAlpha, colToString(params.responseColumn),
                colToString(params.weightsColumn), colToString(params.offsetColumn), colToString(params.foldColumn), params.foldAssignment,
                params.categoricalEncoding, params.maxCategoricalLevels, params.ignoredColumns, params.ignoreConstCols,
                params.scoreEachIteration, keyToString(params.checkpoint), params.stoppingRounds, params.maxRuntimeSecs,
                params.stoppingMetric, params.stoppingTolerance, params.customMetricFunc, params.customDistributionFunc,
                params.exportCheckpointsDir).execute().body();
    }

    /**
     * Run grid search for PCA model.
     */
    public PCAV3 grid_search_pca(final int k) throws IOException {
        final Grid s = getService(Grid.class);
        return s.trainPca(k).execute().body();
    }

    public PCAV3 grid_search_pca(final PCAParametersV3 params) throws IOException {
        final Grid s = getService(Grid.class);
        return s.trainPca(params.transform, params.pcaMethod, params.pcaImpl, params.k, params.maxIterations, params.seed,
                params.useAllFactorLevels, params.computeMetrics, params.imputeMissing, keyToString(params.modelId),
                keyToString(params.trainingFrame), keyToString(params.validationFrame), params.nfolds, params.keepCrossValidationModels,
                params.keepCrossValidationPredictions, params.keepCrossValidationFoldAssignment, params.parallelizeCrossValidation,
                params.distribution, params.tweediePower, params.quantileAlpha, params.huberAlpha, colToString(params.responseColumn),
                colToString(params.weightsColumn), colToString(params.offsetColumn), colToString(params.foldColumn), params.foldAssignment,
                params.categoricalEncoding, params.maxCategoricalLevels, params.ignoredColumns, params.ignoreConstCols,
                params.scoreEachIteration, keyToString(params.checkpoint), params.stoppingRounds, params.maxRuntimeSecs,
                params.stoppingMetric, params.stoppingTolerance, params.customMetricFunc, params.customDistributionFunc,
                params.exportCheckpointsDir).execute().body();
    }

    /**
     * Train a SVD model.
     */
    public SVDV99 train_svd() throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.trainSvd().execute().body();
    }

    public SVDV99 train_svd(final SVDParametersV99 params) throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.trainSvd(params.transform, params.svdMethod, params.nv, params.maxIterations, params.seed, params.keepU, params.uName,
                params.useAllFactorLevels, keyToString(params.modelId), keyToString(params.trainingFrame),
                keyToString(params.validationFrame), params.nfolds, params.keepCrossValidationModels,
                params.keepCrossValidationPredictions, params.keepCrossValidationFoldAssignment, params.parallelizeCrossValidation,
                params.distribution, params.tweediePower, params.quantileAlpha, params.huberAlpha, colToString(params.responseColumn),
                colToString(params.weightsColumn), colToString(params.offsetColumn), colToString(params.foldColumn), params.foldAssignment,
                params.categoricalEncoding, params.maxCategoricalLevels, params.ignoredColumns, params.ignoreConstCols,
                params.scoreEachIteration, keyToString(params.checkpoint), params.stoppingRounds, params.maxRuntimeSecs,
                params.stoppingMetric, params.stoppingTolerance, params.customMetricFunc, params.customDistributionFunc,
                params.exportCheckpointsDir).execute().body();
    }

    /**
     * Validate a set of SVD model builder parameters.
     */
    public SVDV99 validate_svd() throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.validate_parametersSvd().execute().body();
    }

    public SVDV99 validate_svd(final SVDParametersV99 params) throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.validate_parametersSvd(params.transform, params.svdMethod, params.nv, params.maxIterations, params.seed, params.keepU,
                params.uName, params.useAllFactorLevels, keyToString(params.modelId), keyToString(params.trainingFrame),
                keyToString(params.validationFrame), params.nfolds, params.keepCrossValidationModels,
                params.keepCrossValidationPredictions, params.keepCrossValidationFoldAssignment, params.parallelizeCrossValidation,
                params.distribution, params.tweediePower, params.quantileAlpha, params.huberAlpha, colToString(params.responseColumn),
                colToString(params.weightsColumn), colToString(params.offsetColumn), colToString(params.foldColumn), params.foldAssignment,
                params.categoricalEncoding, params.maxCategoricalLevels, params.ignoredColumns, params.ignoreConstCols,
                params.scoreEachIteration, keyToString(params.checkpoint), params.stoppingRounds, params.maxRuntimeSecs,
                params.stoppingMetric, params.stoppingTolerance, params.customMetricFunc, params.customDistributionFunc,
                params.exportCheckpointsDir).execute().body();
    }

    /**
     * Run grid search for SVD model.
     */
    public SVDV99 grid_search_svd() throws IOException {
        final Grid s = getService(Grid.class);
        return s.trainSvd().execute().body();
    }

    public SVDV99 grid_search_svd(final SVDParametersV99 params) throws IOException {
        final Grid s = getService(Grid.class);
        return s.trainSvd(params.transform, params.svdMethod, params.nv, params.maxIterations, params.seed, params.keepU, params.uName,
                params.useAllFactorLevels, keyToString(params.modelId), keyToString(params.trainingFrame),
                keyToString(params.validationFrame), params.nfolds, params.keepCrossValidationModels,
                params.keepCrossValidationPredictions, params.keepCrossValidationFoldAssignment, params.parallelizeCrossValidation,
                params.distribution, params.tweediePower, params.quantileAlpha, params.huberAlpha, colToString(params.responseColumn),
                colToString(params.weightsColumn), colToString(params.offsetColumn), colToString(params.foldColumn), params.foldAssignment,
                params.categoricalEncoding, params.maxCategoricalLevels, params.ignoredColumns, params.ignoreConstCols,
                params.scoreEachIteration, keyToString(params.checkpoint), params.stoppingRounds, params.maxRuntimeSecs,
                params.stoppingMetric, params.stoppingTolerance, params.customMetricFunc, params.customDistributionFunc,
                params.exportCheckpointsDir).execute().body();
    }

    /**
     * Train a DRF model.
     */
    public DRFV3 train_drf() throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.trainDrf().execute().body();
    }

    public DRFV3 train_drf(final DRFParametersV3 params) throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.trainDrf(params.mtries, params.binomialDoubleTrees, params.sampleRate, params.balanceClasses, params.classSamplingFactors,
                params.maxAfterBalanceSize, params.maxConfusionMatrixSize, params.maxHitRatioK, params.ntrees, params.maxDepth,
                params.minRows, params.nbins, params.nbinsTopLevel, params.nbinsCats, params.r2Stopping, params.seed,
                params.buildTreeOneNode, params.sampleRatePerClass, params.colSampleRatePerTree, params.colSampleRateChangePerLevel,
                params.scoreTreeInterval, params.minSplitImprovement, params.histogramType, params.calibrateModel,
                keyToString(params.calibrationFrame), params.checkConstantResponse, keyToString(params.modelId),
                keyToString(params.trainingFrame), keyToString(params.validationFrame), params.nfolds, params.keepCrossValidationModels,
                params.keepCrossValidationPredictions, params.keepCrossValidationFoldAssignment, params.parallelizeCrossValidation,
                params.distribution, params.tweediePower, params.quantileAlpha, params.huberAlpha, colToString(params.responseColumn),
                colToString(params.weightsColumn), colToString(params.offsetColumn), colToString(params.foldColumn), params.foldAssignment,
                params.categoricalEncoding, params.maxCategoricalLevels, params.ignoredColumns, params.ignoreConstCols,
                params.scoreEachIteration, keyToString(params.checkpoint), params.stoppingRounds, params.maxRuntimeSecs,
                params.stoppingMetric, params.stoppingTolerance, params.customMetricFunc, params.customDistributionFunc,
                params.exportCheckpointsDir).execute().body();
    }

    /**
     * Validate a set of DRF model builder parameters.
     */
    public DRFV3 validate_drf() throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.validate_parametersDrf().execute().body();
    }

    public DRFV3 validate_drf(final DRFParametersV3 params) throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.validate_parametersDrf(params.mtries, params.binomialDoubleTrees, params.sampleRate, params.balanceClasses,
                params.classSamplingFactors, params.maxAfterBalanceSize, params.maxConfusionMatrixSize, params.maxHitRatioK, params.ntrees,
                params.maxDepth, params.minRows, params.nbins, params.nbinsTopLevel, params.nbinsCats, params.r2Stopping, params.seed,
                params.buildTreeOneNode, params.sampleRatePerClass, params.colSampleRatePerTree, params.colSampleRateChangePerLevel,
                params.scoreTreeInterval, params.minSplitImprovement, params.histogramType, params.calibrateModel,
                keyToString(params.calibrationFrame), params.checkConstantResponse, keyToString(params.modelId),
                keyToString(params.trainingFrame), keyToString(params.validationFrame), params.nfolds, params.keepCrossValidationModels,
                params.keepCrossValidationPredictions, params.keepCrossValidationFoldAssignment, params.parallelizeCrossValidation,
                params.distribution, params.tweediePower, params.quantileAlpha, params.huberAlpha, colToString(params.responseColumn),
                colToString(params.weightsColumn), colToString(params.offsetColumn), colToString(params.foldColumn), params.foldAssignment,
                params.categoricalEncoding, params.maxCategoricalLevels, params.ignoredColumns, params.ignoreConstCols,
                params.scoreEachIteration, keyToString(params.checkpoint), params.stoppingRounds, params.maxRuntimeSecs,
                params.stoppingMetric, params.stoppingTolerance, params.customMetricFunc, params.customDistributionFunc,
                params.exportCheckpointsDir).execute().body();
    }

    /**
     * Run grid search for DRF model.
     */
    public DRFV3 grid_search_drf() throws IOException {
        final Grid s = getService(Grid.class);
        return s.trainDrf().execute().body();
    }

    public DRFV3 grid_search_drf(final DRFParametersV3 params) throws IOException {
        final Grid s = getService(Grid.class);
        return s.trainDrf(params.mtries, params.binomialDoubleTrees, params.sampleRate, params.balanceClasses, params.classSamplingFactors,
                params.maxAfterBalanceSize, params.maxConfusionMatrixSize, params.maxHitRatioK, params.ntrees, params.maxDepth,
                params.minRows, params.nbins, params.nbinsTopLevel, params.nbinsCats, params.r2Stopping, params.seed,
                params.buildTreeOneNode, params.sampleRatePerClass, params.colSampleRatePerTree, params.colSampleRateChangePerLevel,
                params.scoreTreeInterval, params.minSplitImprovement, params.histogramType, params.calibrateModel,
                keyToString(params.calibrationFrame), params.checkConstantResponse, keyToString(params.modelId),
                keyToString(params.trainingFrame), keyToString(params.validationFrame), params.nfolds, params.keepCrossValidationModels,
                params.keepCrossValidationPredictions, params.keepCrossValidationFoldAssignment, params.parallelizeCrossValidation,
                params.distribution, params.tweediePower, params.quantileAlpha, params.huberAlpha, colToString(params.responseColumn),
                colToString(params.weightsColumn), colToString(params.offsetColumn), colToString(params.foldColumn), params.foldAssignment,
                params.categoricalEncoding, params.maxCategoricalLevels, params.ignoredColumns, params.ignoreConstCols,
                params.scoreEachIteration, keyToString(params.checkpoint), params.stoppingRounds, params.maxRuntimeSecs,
                params.stoppingMetric, params.stoppingTolerance, params.customMetricFunc, params.customDistributionFunc,
                params.exportCheckpointsDir).execute().body();
    }

    /**
     * Train a GBM model.
     */
    public GBMV3 train_gbm() throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.trainGbm().execute().body();
    }

    public GBMV3 train_gbm(final GBMParametersV3 params) throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.trainGbm(params.learnRate, params.learnRateAnnealing, params.sampleRate, params.colSampleRate, params.monotoneConstraints,
                params.maxAbsLeafnodePred, params.predNoiseBandwidth, params.balanceClasses, params.classSamplingFactors,
                params.maxAfterBalanceSize, params.maxConfusionMatrixSize, params.maxHitRatioK, params.ntrees, params.maxDepth,
                params.minRows, params.nbins, params.nbinsTopLevel, params.nbinsCats, params.r2Stopping, params.seed,
                params.buildTreeOneNode, params.sampleRatePerClass, params.colSampleRatePerTree, params.colSampleRateChangePerLevel,
                params.scoreTreeInterval, params.minSplitImprovement, params.histogramType, params.calibrateModel,
                keyToString(params.calibrationFrame), params.checkConstantResponse, keyToString(params.modelId),
                keyToString(params.trainingFrame), keyToString(params.validationFrame), params.nfolds, params.keepCrossValidationModels,
                params.keepCrossValidationPredictions, params.keepCrossValidationFoldAssignment, params.parallelizeCrossValidation,
                params.distribution, params.tweediePower, params.quantileAlpha, params.huberAlpha, colToString(params.responseColumn),
                colToString(params.weightsColumn), colToString(params.offsetColumn), colToString(params.foldColumn), params.foldAssignment,
                params.categoricalEncoding, params.maxCategoricalLevels, params.ignoredColumns, params.ignoreConstCols,
                params.scoreEachIteration, keyToString(params.checkpoint), params.stoppingRounds, params.maxRuntimeSecs,
                params.stoppingMetric, params.stoppingTolerance, params.customMetricFunc, params.customDistributionFunc,
                params.exportCheckpointsDir).execute().body();
    }

    /**
     * Validate a set of GBM model builder parameters.
     */
    public GBMV3 validate_gbm() throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.validate_parametersGbm().execute().body();
    }

    public GBMV3 validate_gbm(final GBMParametersV3 params) throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.validate_parametersGbm(params.learnRate, params.learnRateAnnealing, params.sampleRate, params.colSampleRate,
                params.monotoneConstraints, params.maxAbsLeafnodePred, params.predNoiseBandwidth, params.balanceClasses,
                params.classSamplingFactors, params.maxAfterBalanceSize, params.maxConfusionMatrixSize, params.maxHitRatioK, params.ntrees,
                params.maxDepth, params.minRows, params.nbins, params.nbinsTopLevel, params.nbinsCats, params.r2Stopping, params.seed,
                params.buildTreeOneNode, params.sampleRatePerClass, params.colSampleRatePerTree, params.colSampleRateChangePerLevel,
                params.scoreTreeInterval, params.minSplitImprovement, params.histogramType, params.calibrateModel,
                keyToString(params.calibrationFrame), params.checkConstantResponse, keyToString(params.modelId),
                keyToString(params.trainingFrame), keyToString(params.validationFrame), params.nfolds, params.keepCrossValidationModels,
                params.keepCrossValidationPredictions, params.keepCrossValidationFoldAssignment, params.parallelizeCrossValidation,
                params.distribution, params.tweediePower, params.quantileAlpha, params.huberAlpha, colToString(params.responseColumn),
                colToString(params.weightsColumn), colToString(params.offsetColumn), colToString(params.foldColumn), params.foldAssignment,
                params.categoricalEncoding, params.maxCategoricalLevels, params.ignoredColumns, params.ignoreConstCols,
                params.scoreEachIteration, keyToString(params.checkpoint), params.stoppingRounds, params.maxRuntimeSecs,
                params.stoppingMetric, params.stoppingTolerance, params.customMetricFunc, params.customDistributionFunc,
                params.exportCheckpointsDir).execute().body();
    }

    /**
     * Run grid search for GBM model.
     */
    public GBMV3 grid_search_gbm() throws IOException {
        final Grid s = getService(Grid.class);
        return s.trainGbm().execute().body();
    }

    public GBMV3 grid_search_gbm(final GBMParametersV3 params) throws IOException {
        final Grid s = getService(Grid.class);
        return s.trainGbm(params.learnRate, params.learnRateAnnealing, params.sampleRate, params.colSampleRate, params.monotoneConstraints,
                params.maxAbsLeafnodePred, params.predNoiseBandwidth, params.balanceClasses, params.classSamplingFactors,
                params.maxAfterBalanceSize, params.maxConfusionMatrixSize, params.maxHitRatioK, params.ntrees, params.maxDepth,
                params.minRows, params.nbins, params.nbinsTopLevel, params.nbinsCats, params.r2Stopping, params.seed,
                params.buildTreeOneNode, params.sampleRatePerClass, params.colSampleRatePerTree, params.colSampleRateChangePerLevel,
                params.scoreTreeInterval, params.minSplitImprovement, params.histogramType, params.calibrateModel,
                keyToString(params.calibrationFrame), params.checkConstantResponse, keyToString(params.modelId),
                keyToString(params.trainingFrame), keyToString(params.validationFrame), params.nfolds, params.keepCrossValidationModels,
                params.keepCrossValidationPredictions, params.keepCrossValidationFoldAssignment, params.parallelizeCrossValidation,
                params.distribution, params.tweediePower, params.quantileAlpha, params.huberAlpha, colToString(params.responseColumn),
                colToString(params.weightsColumn), colToString(params.offsetColumn), colToString(params.foldColumn), params.foldAssignment,
                params.categoricalEncoding, params.maxCategoricalLevels, params.ignoredColumns, params.ignoreConstCols,
                params.scoreEachIteration, keyToString(params.checkpoint), params.stoppingRounds, params.maxRuntimeSecs,
                params.stoppingMetric, params.stoppingTolerance, params.customMetricFunc, params.customDistributionFunc,
                params.exportCheckpointsDir).execute().body();
    }

    /**
     * Train a IsolationForest model.
     */
    public IsolationForestV3 train_isolationforest() throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.trainIsolationforest().execute().body();
    }

    public IsolationForestV3 train_isolationforest(final IsolationForestParametersV3 params) throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.trainIsolationforest(params.sampleSize, params.sampleRate, params.mtries, params.balanceClasses,
                params.classSamplingFactors, params.maxAfterBalanceSize, params.maxConfusionMatrixSize, params.maxHitRatioK, params.ntrees,
                params.maxDepth, params.minRows, params.nbins, params.nbinsTopLevel, params.nbinsCats, params.r2Stopping, params.seed,
                params.buildTreeOneNode, params.sampleRatePerClass, params.colSampleRatePerTree, params.colSampleRateChangePerLevel,
                params.scoreTreeInterval, params.minSplitImprovement, params.histogramType, params.calibrateModel,
                keyToString(params.calibrationFrame), params.checkConstantResponse, keyToString(params.modelId),
                keyToString(params.trainingFrame), keyToString(params.validationFrame), params.nfolds, params.keepCrossValidationModels,
                params.keepCrossValidationPredictions, params.keepCrossValidationFoldAssignment, params.parallelizeCrossValidation,
                params.distribution, params.tweediePower, params.quantileAlpha, params.huberAlpha, colToString(params.responseColumn),
                colToString(params.weightsColumn), colToString(params.offsetColumn), colToString(params.foldColumn), params.foldAssignment,
                params.categoricalEncoding, params.maxCategoricalLevels, params.ignoredColumns, params.ignoreConstCols,
                params.scoreEachIteration, keyToString(params.checkpoint), params.stoppingRounds, params.maxRuntimeSecs,
                params.stoppingMetric, params.stoppingTolerance, params.customMetricFunc, params.customDistributionFunc,
                params.exportCheckpointsDir).execute().body();
    }

    /**
     * Validate a set of IsolationForest model builder parameters.
     */
    public IsolationForestV3 validate_isolationforest() throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.validate_parametersIsolationforest().execute().body();
    }

    public IsolationForestV3 validate_isolationforest(final IsolationForestParametersV3 params) throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.validate_parametersIsolationforest(params.sampleSize, params.sampleRate, params.mtries, params.balanceClasses,
                params.classSamplingFactors, params.maxAfterBalanceSize, params.maxConfusionMatrixSize, params.maxHitRatioK, params.ntrees,
                params.maxDepth, params.minRows, params.nbins, params.nbinsTopLevel, params.nbinsCats, params.r2Stopping, params.seed,
                params.buildTreeOneNode, params.sampleRatePerClass, params.colSampleRatePerTree, params.colSampleRateChangePerLevel,
                params.scoreTreeInterval, params.minSplitImprovement, params.histogramType, params.calibrateModel,
                keyToString(params.calibrationFrame), params.checkConstantResponse, keyToString(params.modelId),
                keyToString(params.trainingFrame), keyToString(params.validationFrame), params.nfolds, params.keepCrossValidationModels,
                params.keepCrossValidationPredictions, params.keepCrossValidationFoldAssignment, params.parallelizeCrossValidation,
                params.distribution, params.tweediePower, params.quantileAlpha, params.huberAlpha, colToString(params.responseColumn),
                colToString(params.weightsColumn), colToString(params.offsetColumn), colToString(params.foldColumn), params.foldAssignment,
                params.categoricalEncoding, params.maxCategoricalLevels, params.ignoredColumns, params.ignoreConstCols,
                params.scoreEachIteration, keyToString(params.checkpoint), params.stoppingRounds, params.maxRuntimeSecs,
                params.stoppingMetric, params.stoppingTolerance, params.customMetricFunc, params.customDistributionFunc,
                params.exportCheckpointsDir).execute().body();
    }

    /**
     * Run grid search for IsolationForest model.
     */
    public IsolationForestV3 grid_search_isolationforest() throws IOException {
        final Grid s = getService(Grid.class);
        return s.trainIsolationforest().execute().body();
    }

    public IsolationForestV3 grid_search_isolationforest(final IsolationForestParametersV3 params) throws IOException {
        final Grid s = getService(Grid.class);
        return s.trainIsolationforest(params.sampleSize, params.sampleRate, params.mtries, params.balanceClasses,
                params.classSamplingFactors, params.maxAfterBalanceSize, params.maxConfusionMatrixSize, params.maxHitRatioK, params.ntrees,
                params.maxDepth, params.minRows, params.nbins, params.nbinsTopLevel, params.nbinsCats, params.r2Stopping, params.seed,
                params.buildTreeOneNode, params.sampleRatePerClass, params.colSampleRatePerTree, params.colSampleRateChangePerLevel,
                params.scoreTreeInterval, params.minSplitImprovement, params.histogramType, params.calibrateModel,
                keyToString(params.calibrationFrame), params.checkConstantResponse, keyToString(params.modelId),
                keyToString(params.trainingFrame), keyToString(params.validationFrame), params.nfolds, params.keepCrossValidationModels,
                params.keepCrossValidationPredictions, params.keepCrossValidationFoldAssignment, params.parallelizeCrossValidation,
                params.distribution, params.tweediePower, params.quantileAlpha, params.huberAlpha, colToString(params.responseColumn),
                colToString(params.weightsColumn), colToString(params.offsetColumn), colToString(params.foldColumn), params.foldAssignment,
                params.categoricalEncoding, params.maxCategoricalLevels, params.ignoredColumns, params.ignoreConstCols,
                params.scoreEachIteration, keyToString(params.checkpoint), params.stoppingRounds, params.maxRuntimeSecs,
                params.stoppingMetric, params.stoppingTolerance, params.customMetricFunc, params.customDistributionFunc,
                params.exportCheckpointsDir).execute().body();
    }

    /**
     * Train a Aggregator model.
     */
    public AggregatorV99 train_aggregator() throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.trainAggregator().execute().body();
    }

    public AggregatorV99 train_aggregator(final AggregatorParametersV99 params) throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.trainAggregator(params.transform, params.pcaMethod, params.k, params.maxIterations, params.targetNumExemplars,
                params.relTolNumExemplars, params.seed, params.useAllFactorLevels, params.saveMappingFrame,
                params.numIterationWithoutNewExemplar, keyToString(params.modelId), keyToString(params.trainingFrame),
                keyToString(params.validationFrame), params.nfolds, params.keepCrossValidationModels,
                params.keepCrossValidationPredictions, params.keepCrossValidationFoldAssignment, params.parallelizeCrossValidation,
                params.distribution, params.tweediePower, params.quantileAlpha, params.huberAlpha, colToString(params.responseColumn),
                colToString(params.weightsColumn), colToString(params.offsetColumn), colToString(params.foldColumn), params.foldAssignment,
                params.categoricalEncoding, params.maxCategoricalLevels, params.ignoredColumns, params.ignoreConstCols,
                params.scoreEachIteration, keyToString(params.checkpoint), params.stoppingRounds, params.maxRuntimeSecs,
                params.stoppingMetric, params.stoppingTolerance, params.customMetricFunc, params.customDistributionFunc,
                params.exportCheckpointsDir).execute().body();
    }

    /**
     * Validate a set of Aggregator model builder parameters.
     */
    public AggregatorV99 validate_aggregator() throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.validate_parametersAggregator().execute().body();
    }

    public AggregatorV99 validate_aggregator(final AggregatorParametersV99 params) throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.validate_parametersAggregator(params.transform, params.pcaMethod, params.k, params.maxIterations,
                params.targetNumExemplars, params.relTolNumExemplars, params.seed, params.useAllFactorLevels, params.saveMappingFrame,
                params.numIterationWithoutNewExemplar, keyToString(params.modelId), keyToString(params.trainingFrame),
                keyToString(params.validationFrame), params.nfolds, params.keepCrossValidationModels,
                params.keepCrossValidationPredictions, params.keepCrossValidationFoldAssignment, params.parallelizeCrossValidation,
                params.distribution, params.tweediePower, params.quantileAlpha, params.huberAlpha, colToString(params.responseColumn),
                colToString(params.weightsColumn), colToString(params.offsetColumn), colToString(params.foldColumn), params.foldAssignment,
                params.categoricalEncoding, params.maxCategoricalLevels, params.ignoredColumns, params.ignoreConstCols,
                params.scoreEachIteration, keyToString(params.checkpoint), params.stoppingRounds, params.maxRuntimeSecs,
                params.stoppingMetric, params.stoppingTolerance, params.customMetricFunc, params.customDistributionFunc,
                params.exportCheckpointsDir).execute().body();
    }

    /**
     * Run grid search for Aggregator model.
     */
    public AggregatorV99 grid_search_aggregator() throws IOException {
        final Grid s = getService(Grid.class);
        return s.trainAggregator().execute().body();
    }

    public AggregatorV99 grid_search_aggregator(final AggregatorParametersV99 params) throws IOException {
        final Grid s = getService(Grid.class);
        return s.trainAggregator(params.transform, params.pcaMethod, params.k, params.maxIterations, params.targetNumExemplars,
                params.relTolNumExemplars, params.seed, params.useAllFactorLevels, params.saveMappingFrame,
                params.numIterationWithoutNewExemplar, keyToString(params.modelId), keyToString(params.trainingFrame),
                keyToString(params.validationFrame), params.nfolds, params.keepCrossValidationModels,
                params.keepCrossValidationPredictions, params.keepCrossValidationFoldAssignment, params.parallelizeCrossValidation,
                params.distribution, params.tweediePower, params.quantileAlpha, params.huberAlpha, colToString(params.responseColumn),
                colToString(params.weightsColumn), colToString(params.offsetColumn), colToString(params.foldColumn), params.foldAssignment,
                params.categoricalEncoding, params.maxCategoricalLevels, params.ignoredColumns, params.ignoreConstCols,
                params.scoreEachIteration, keyToString(params.checkpoint), params.stoppingRounds, params.maxRuntimeSecs,
                params.stoppingMetric, params.stoppingTolerance, params.customMetricFunc, params.customDistributionFunc,
                params.exportCheckpointsDir).execute().body();
    }

    /**
     * Train a DeepWater model.
     */
    public DeepWaterV3 train_deepwater() throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.trainDeepwater().execute().body();
    }

    public DeepWaterV3 train_deepwater(final DeepWaterParametersV3 params) throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.trainDeepwater(params.problemType, params.activation, params.hidden, params.inputDropoutRatio, params.hiddenDropoutRatios,
                params.maxConfusionMatrixSize, params.sparse, params.maxHitRatioK, params.epochs, params.trainSamplesPerIteration,
                params.targetRatioCommToComp, params.seed, params.learningRate, params.learningRateAnnealing, params.momentumStart,
                params.momentumRamp, params.momentumStable, params.scoreInterval, params.scoreTrainingSamples,
                params.scoreValidationSamples, params.scoreDutyCycle, params.classificationStop, params.regressionStop, params.quietMode,
                params.overwriteWithBestModel, params.autoencoder, params.diagnostics, params.variableImportances,
                params.replicateTrainingData, params.singleNodeMode, params.shuffleTrainingData, params.miniBatchSize, params.clipGradient,
                params.network, params.backend, params.imageShape, params.channels, params.gpu, params.deviceId, params.cacheData,
                params.networkDefinitionFile, params.networkParametersFile, params.meanImageFile, params.exportNativeParametersPrefix,
                params.standardize, params.balanceClasses, params.classSamplingFactors, params.maxAfterBalanceSize,
                keyToString(params.modelId), keyToString(params.trainingFrame), keyToString(params.validationFrame), params.nfolds,
                params.keepCrossValidationModels, params.keepCrossValidationPredictions, params.keepCrossValidationFoldAssignment,
                params.parallelizeCrossValidation, params.distribution, params.tweediePower, params.quantileAlpha, params.huberAlpha,
                colToString(params.responseColumn), colToString(params.weightsColumn), colToString(params.offsetColumn),
                colToString(params.foldColumn), params.foldAssignment, params.categoricalEncoding, params.maxCategoricalLevels,
                params.ignoredColumns, params.ignoreConstCols, params.scoreEachIteration, keyToString(params.checkpoint),
                params.stoppingRounds, params.maxRuntimeSecs, params.stoppingMetric, params.stoppingTolerance, params.customMetricFunc,
                params.customDistributionFunc, params.exportCheckpointsDir).execute().body();
    }

    /**
     * Validate a set of DeepWater model builder parameters.
     */
    public DeepWaterV3 validate_deepwater() throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.validate_parametersDeepwater().execute().body();
    }

    public DeepWaterV3 validate_deepwater(final DeepWaterParametersV3 params) throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.validate_parametersDeepwater(params.problemType, params.activation, params.hidden, params.inputDropoutRatio,
                params.hiddenDropoutRatios, params.maxConfusionMatrixSize, params.sparse, params.maxHitRatioK, params.epochs,
                params.trainSamplesPerIteration, params.targetRatioCommToComp, params.seed, params.learningRate,
                params.learningRateAnnealing, params.momentumStart, params.momentumRamp, params.momentumStable, params.scoreInterval,
                params.scoreTrainingSamples, params.scoreValidationSamples, params.scoreDutyCycle, params.classificationStop,
                params.regressionStop, params.quietMode, params.overwriteWithBestModel, params.autoencoder, params.diagnostics,
                params.variableImportances, params.replicateTrainingData, params.singleNodeMode, params.shuffleTrainingData,
                params.miniBatchSize, params.clipGradient, params.network, params.backend, params.imageShape, params.channels, params.gpu,
                params.deviceId, params.cacheData, params.networkDefinitionFile, params.networkParametersFile, params.meanImageFile,
                params.exportNativeParametersPrefix, params.standardize, params.balanceClasses, params.classSamplingFactors,
                params.maxAfterBalanceSize, keyToString(params.modelId), keyToString(params.trainingFrame),
                keyToString(params.validationFrame), params.nfolds, params.keepCrossValidationModels,
                params.keepCrossValidationPredictions, params.keepCrossValidationFoldAssignment, params.parallelizeCrossValidation,
                params.distribution, params.tweediePower, params.quantileAlpha, params.huberAlpha, colToString(params.responseColumn),
                colToString(params.weightsColumn), colToString(params.offsetColumn), colToString(params.foldColumn), params.foldAssignment,
                params.categoricalEncoding, params.maxCategoricalLevels, params.ignoredColumns, params.ignoreConstCols,
                params.scoreEachIteration, keyToString(params.checkpoint), params.stoppingRounds, params.maxRuntimeSecs,
                params.stoppingMetric, params.stoppingTolerance, params.customMetricFunc, params.customDistributionFunc,
                params.exportCheckpointsDir).execute().body();
    }

    /**
     * Run grid search for DeepWater model.
     */
    public DeepWaterV3 grid_search_deepwater() throws IOException {
        final Grid s = getService(Grid.class);
        return s.trainDeepwater().execute().body();
    }

    public DeepWaterV3 grid_search_deepwater(final DeepWaterParametersV3 params) throws IOException {
        final Grid s = getService(Grid.class);
        return s.trainDeepwater(params.problemType, params.activation, params.hidden, params.inputDropoutRatio, params.hiddenDropoutRatios,
                params.maxConfusionMatrixSize, params.sparse, params.maxHitRatioK, params.epochs, params.trainSamplesPerIteration,
                params.targetRatioCommToComp, params.seed, params.learningRate, params.learningRateAnnealing, params.momentumStart,
                params.momentumRamp, params.momentumStable, params.scoreInterval, params.scoreTrainingSamples,
                params.scoreValidationSamples, params.scoreDutyCycle, params.classificationStop, params.regressionStop, params.quietMode,
                params.overwriteWithBestModel, params.autoencoder, params.diagnostics, params.variableImportances,
                params.replicateTrainingData, params.singleNodeMode, params.shuffleTrainingData, params.miniBatchSize, params.clipGradient,
                params.network, params.backend, params.imageShape, params.channels, params.gpu, params.deviceId, params.cacheData,
                params.networkDefinitionFile, params.networkParametersFile, params.meanImageFile, params.exportNativeParametersPrefix,
                params.standardize, params.balanceClasses, params.classSamplingFactors, params.maxAfterBalanceSize,
                keyToString(params.modelId), keyToString(params.trainingFrame), keyToString(params.validationFrame), params.nfolds,
                params.keepCrossValidationModels, params.keepCrossValidationPredictions, params.keepCrossValidationFoldAssignment,
                params.parallelizeCrossValidation, params.distribution, params.tweediePower, params.quantileAlpha, params.huberAlpha,
                colToString(params.responseColumn), colToString(params.weightsColumn), colToString(params.offsetColumn),
                colToString(params.foldColumn), params.foldAssignment, params.categoricalEncoding, params.maxCategoricalLevels,
                params.ignoredColumns, params.ignoreConstCols, params.scoreEachIteration, keyToString(params.checkpoint),
                params.stoppingRounds, params.maxRuntimeSecs, params.stoppingMetric, params.stoppingTolerance, params.customMetricFunc,
                params.customDistributionFunc, params.exportCheckpointsDir).execute().body();
    }

    /**
     * Train a Word2Vec model.
     */
    public Word2VecV3 train_word2vec() throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.trainWord2vec().execute().body();
    }

    public Word2VecV3 train_word2vec(final Word2VecParametersV3 params) throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.trainWord2vec(params.vecSize, params.windowSize, params.sentSampleRate, params.normModel, params.epochs,
                params.minWordFreq, params.initLearningRate, params.wordModel, keyToString(params.preTrained), keyToString(params.modelId),
                keyToString(params.trainingFrame), keyToString(params.validationFrame), params.nfolds, params.keepCrossValidationModels,
                params.keepCrossValidationPredictions, params.keepCrossValidationFoldAssignment, params.parallelizeCrossValidation,
                params.distribution, params.tweediePower, params.quantileAlpha, params.huberAlpha, colToString(params.responseColumn),
                colToString(params.weightsColumn), colToString(params.offsetColumn), colToString(params.foldColumn), params.foldAssignment,
                params.categoricalEncoding, params.maxCategoricalLevels, params.ignoredColumns, params.ignoreConstCols,
                params.scoreEachIteration, keyToString(params.checkpoint), params.stoppingRounds, params.maxRuntimeSecs,
                params.stoppingMetric, params.stoppingTolerance, params.customMetricFunc, params.customDistributionFunc,
                params.exportCheckpointsDir).execute().body();
    }

    /**
     * Validate a set of Word2Vec model builder parameters.
     */
    public Word2VecV3 validate_word2vec() throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.validate_parametersWord2vec().execute().body();
    }

    public Word2VecV3 validate_word2vec(final Word2VecParametersV3 params) throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.validate_parametersWord2vec(params.vecSize, params.windowSize, params.sentSampleRate, params.normModel, params.epochs,
                params.minWordFreq, params.initLearningRate, params.wordModel, keyToString(params.preTrained), keyToString(params.modelId),
                keyToString(params.trainingFrame), keyToString(params.validationFrame), params.nfolds, params.keepCrossValidationModels,
                params.keepCrossValidationPredictions, params.keepCrossValidationFoldAssignment, params.parallelizeCrossValidation,
                params.distribution, params.tweediePower, params.quantileAlpha, params.huberAlpha, colToString(params.responseColumn),
                colToString(params.weightsColumn), colToString(params.offsetColumn), colToString(params.foldColumn), params.foldAssignment,
                params.categoricalEncoding, params.maxCategoricalLevels, params.ignoredColumns, params.ignoreConstCols,
                params.scoreEachIteration, keyToString(params.checkpoint), params.stoppingRounds, params.maxRuntimeSecs,
                params.stoppingMetric, params.stoppingTolerance, params.customMetricFunc, params.customDistributionFunc,
                params.exportCheckpointsDir).execute().body();
    }

    /**
     * Run grid search for Word2Vec model.
     */
    public Word2VecV3 grid_search_word2vec() throws IOException {
        final Grid s = getService(Grid.class);
        return s.trainWord2vec().execute().body();
    }

    public Word2VecV3 grid_search_word2vec(final Word2VecParametersV3 params) throws IOException {
        final Grid s = getService(Grid.class);
        return s.trainWord2vec(params.vecSize, params.windowSize, params.sentSampleRate, params.normModel, params.epochs,
                params.minWordFreq, params.initLearningRate, params.wordModel, keyToString(params.preTrained), keyToString(params.modelId),
                keyToString(params.trainingFrame), keyToString(params.validationFrame), params.nfolds, params.keepCrossValidationModels,
                params.keepCrossValidationPredictions, params.keepCrossValidationFoldAssignment, params.parallelizeCrossValidation,
                params.distribution, params.tweediePower, params.quantileAlpha, params.huberAlpha, colToString(params.responseColumn),
                colToString(params.weightsColumn), colToString(params.offsetColumn), colToString(params.foldColumn), params.foldAssignment,
                params.categoricalEncoding, params.maxCategoricalLevels, params.ignoredColumns, params.ignoreConstCols,
                params.scoreEachIteration, keyToString(params.checkpoint), params.stoppingRounds, params.maxRuntimeSecs,
                params.stoppingMetric, params.stoppingTolerance, params.customMetricFunc, params.customDistributionFunc,
                params.exportCheckpointsDir).execute().body();
    }

    /**
     * Train a StackedEnsemble model.
     */
    public StackedEnsembleV99 train_stackedensemble(final ModelKeyV3[] baseModels) throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.trainStackedensemble(keyArrayToStringArray(baseModels)).execute().body();
    }

    public StackedEnsembleV99 train_stackedensemble(final StackedEnsembleParametersV99 params) throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.trainStackedensemble(keyArrayToStringArray(params.baseModels), params.metalearnerAlgorithm, params.metalearnerNfolds,
                params.metalearnerFoldAssignment, colToString(params.metalearnerFoldColumn), params.keepLeveloneFrame,
                params.metalearnerParams, keyToString(params.blendingFrame), params.seed, keyToString(params.modelId),
                keyToString(params.trainingFrame), keyToString(params.validationFrame), params.nfolds, params.keepCrossValidationModels,
                params.keepCrossValidationPredictions, params.keepCrossValidationFoldAssignment, params.parallelizeCrossValidation,
                params.distribution, params.tweediePower, params.quantileAlpha, params.huberAlpha, colToString(params.responseColumn),
                colToString(params.weightsColumn), colToString(params.offsetColumn), colToString(params.foldColumn), params.foldAssignment,
                params.categoricalEncoding, params.maxCategoricalLevels, params.ignoredColumns, params.ignoreConstCols,
                params.scoreEachIteration, keyToString(params.checkpoint), params.stoppingRounds, params.maxRuntimeSecs,
                params.stoppingMetric, params.stoppingTolerance, params.customMetricFunc, params.customDistributionFunc,
                params.exportCheckpointsDir).execute().body();
    }

    /**
     * Validate a set of StackedEnsemble model builder parameters.
     */
    public StackedEnsembleV99 validate_stackedensemble(final ModelKeyV3[] baseModels) throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.validate_parametersStackedensemble(keyArrayToStringArray(baseModels)).execute().body();
    }

    public StackedEnsembleV99 validate_stackedensemble(final StackedEnsembleParametersV99 params) throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.validate_parametersStackedensemble(keyArrayToStringArray(params.baseModels), params.metalearnerAlgorithm,
                params.metalearnerNfolds, params.metalearnerFoldAssignment, colToString(params.metalearnerFoldColumn),
                params.keepLeveloneFrame, params.metalearnerParams, keyToString(params.blendingFrame), params.seed,
                keyToString(params.modelId), keyToString(params.trainingFrame), keyToString(params.validationFrame), params.nfolds,
                params.keepCrossValidationModels, params.keepCrossValidationPredictions, params.keepCrossValidationFoldAssignment,
                params.parallelizeCrossValidation, params.distribution, params.tweediePower, params.quantileAlpha, params.huberAlpha,
                colToString(params.responseColumn), colToString(params.weightsColumn), colToString(params.offsetColumn),
                colToString(params.foldColumn), params.foldAssignment, params.categoricalEncoding, params.maxCategoricalLevels,
                params.ignoredColumns, params.ignoreConstCols, params.scoreEachIteration, keyToString(params.checkpoint),
                params.stoppingRounds, params.maxRuntimeSecs, params.stoppingMetric, params.stoppingTolerance, params.customMetricFunc,
                params.customDistributionFunc, params.exportCheckpointsDir).execute().body();
    }

    /**
     * Run grid search for StackedEnsemble model.
     */
    public StackedEnsembleV99 grid_search_stackedensemble(final ModelKeyV3[] baseModels) throws IOException {
        final Grid s = getService(Grid.class);
        return s.trainStackedensemble(keyArrayToStringArray(baseModels)).execute().body();
    }

    public StackedEnsembleV99 grid_search_stackedensemble(final StackedEnsembleParametersV99 params) throws IOException {
        final Grid s = getService(Grid.class);
        return s.trainStackedensemble(keyArrayToStringArray(params.baseModels), params.metalearnerAlgorithm, params.metalearnerNfolds,
                params.metalearnerFoldAssignment, colToString(params.metalearnerFoldColumn), params.keepLeveloneFrame,
                params.metalearnerParams, keyToString(params.blendingFrame), params.seed, keyToString(params.modelId),
                keyToString(params.trainingFrame), keyToString(params.validationFrame), params.nfolds, params.keepCrossValidationModels,
                params.keepCrossValidationPredictions, params.keepCrossValidationFoldAssignment, params.parallelizeCrossValidation,
                params.distribution, params.tweediePower, params.quantileAlpha, params.huberAlpha, colToString(params.responseColumn),
                colToString(params.weightsColumn), colToString(params.offsetColumn), colToString(params.foldColumn), params.foldAssignment,
                params.categoricalEncoding, params.maxCategoricalLevels, params.ignoredColumns, params.ignoreConstCols,
                params.scoreEachIteration, keyToString(params.checkpoint), params.stoppingRounds, params.maxRuntimeSecs,
                params.stoppingMetric, params.stoppingTolerance, params.customMetricFunc, params.customDistributionFunc,
                params.exportCheckpointsDir).execute().body();
    }

    /**
     * Train a CoxPH model.
     */
    public CoxPHV3 train_coxph() throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.trainCoxph().execute().body();
    }

    public CoxPHV3 train_coxph(final CoxPHParametersV3 params) throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.trainCoxph(colToString(params.startColumn), colToString(params.stopColumn), params.stratifyBy, params.ties, params.init,
                params.lreMin, params.maxIterations, params.interactionsOnly, params.interactions, params.interactionPairs,
                params.useAllFactorLevels, keyToString(params.modelId), keyToString(params.trainingFrame),
                keyToString(params.validationFrame), params.nfolds, params.keepCrossValidationModels,
                params.keepCrossValidationPredictions, params.keepCrossValidationFoldAssignment, params.parallelizeCrossValidation,
                params.distribution, params.tweediePower, params.quantileAlpha, params.huberAlpha, colToString(params.responseColumn),
                colToString(params.weightsColumn), colToString(params.offsetColumn), colToString(params.foldColumn), params.foldAssignment,
                params.categoricalEncoding, params.maxCategoricalLevels, params.ignoredColumns, params.ignoreConstCols,
                params.scoreEachIteration, keyToString(params.checkpoint), params.stoppingRounds, params.maxRuntimeSecs,
                params.stoppingMetric, params.stoppingTolerance, params.customMetricFunc, params.customDistributionFunc,
                params.exportCheckpointsDir).execute().body();
    }

    /**
     * Validate a set of CoxPH model builder parameters.
     */
    public CoxPHV3 validate_coxph() throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.validate_parametersCoxph().execute().body();
    }

    public CoxPHV3 validate_coxph(final CoxPHParametersV3 params) throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.validate_parametersCoxph(colToString(params.startColumn), colToString(params.stopColumn), params.stratifyBy, params.ties,
                params.init, params.lreMin, params.maxIterations, params.interactionsOnly, params.interactions, params.interactionPairs,
                params.useAllFactorLevels, keyToString(params.modelId), keyToString(params.trainingFrame),
                keyToString(params.validationFrame), params.nfolds, params.keepCrossValidationModels,
                params.keepCrossValidationPredictions, params.keepCrossValidationFoldAssignment, params.parallelizeCrossValidation,
                params.distribution, params.tweediePower, params.quantileAlpha, params.huberAlpha, colToString(params.responseColumn),
                colToString(params.weightsColumn), colToString(params.offsetColumn), colToString(params.foldColumn), params.foldAssignment,
                params.categoricalEncoding, params.maxCategoricalLevels, params.ignoredColumns, params.ignoreConstCols,
                params.scoreEachIteration, keyToString(params.checkpoint), params.stoppingRounds, params.maxRuntimeSecs,
                params.stoppingMetric, params.stoppingTolerance, params.customMetricFunc, params.customDistributionFunc,
                params.exportCheckpointsDir).execute().body();
    }

    /**
     * Run grid search for CoxPH model.
     */
    public CoxPHV3 grid_search_coxph() throws IOException {
        final Grid s = getService(Grid.class);
        return s.trainCoxph().execute().body();
    }

    public CoxPHV3 grid_search_coxph(final CoxPHParametersV3 params) throws IOException {
        final Grid s = getService(Grid.class);
        return s.trainCoxph(colToString(params.startColumn), colToString(params.stopColumn), params.stratifyBy, params.ties, params.init,
                params.lreMin, params.maxIterations, params.interactionsOnly, params.interactions, params.interactionPairs,
                params.useAllFactorLevels, keyToString(params.modelId), keyToString(params.trainingFrame),
                keyToString(params.validationFrame), params.nfolds, params.keepCrossValidationModels,
                params.keepCrossValidationPredictions, params.keepCrossValidationFoldAssignment, params.parallelizeCrossValidation,
                params.distribution, params.tweediePower, params.quantileAlpha, params.huberAlpha, colToString(params.responseColumn),
                colToString(params.weightsColumn), colToString(params.offsetColumn), colToString(params.foldColumn), params.foldAssignment,
                params.categoricalEncoding, params.maxCategoricalLevels, params.ignoredColumns, params.ignoreConstCols,
                params.scoreEachIteration, keyToString(params.checkpoint), params.stoppingRounds, params.maxRuntimeSecs,
                params.stoppingMetric, params.stoppingTolerance, params.customMetricFunc, params.customDistributionFunc,
                params.exportCheckpointsDir).execute().body();
    }

    /**
     * Train a Generic model.
     */
    public GenericV3 train_generic() throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.trainGeneric().execute().body();
    }

    public GenericV3 train_generic(final GenericParametersV3 params) throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.trainGeneric(params.path, keyToString(params.modelKey), keyToString(params.modelId), keyToString(params.trainingFrame),
                keyToString(params.validationFrame), params.nfolds, params.keepCrossValidationModels,
                params.keepCrossValidationPredictions, params.keepCrossValidationFoldAssignment, params.parallelizeCrossValidation,
                params.distribution, params.tweediePower, params.quantileAlpha, params.huberAlpha, colToString(params.responseColumn),
                colToString(params.weightsColumn), colToString(params.offsetColumn), colToString(params.foldColumn), params.foldAssignment,
                params.categoricalEncoding, params.maxCategoricalLevels, params.ignoredColumns, params.ignoreConstCols,
                params.scoreEachIteration, keyToString(params.checkpoint), params.stoppingRounds, params.maxRuntimeSecs,
                params.stoppingMetric, params.stoppingTolerance, params.customMetricFunc, params.customDistributionFunc,
                params.exportCheckpointsDir).execute().body();
    }

    /**
     * Validate a set of Generic model builder parameters.
     */
    public GenericV3 validate_generic() throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.validate_parametersGeneric().execute().body();
    }

    public GenericV3 validate_generic(final GenericParametersV3 params) throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.validate_parametersGeneric(params.path, keyToString(params.modelKey), keyToString(params.modelId),
                keyToString(params.trainingFrame), keyToString(params.validationFrame), params.nfolds, params.keepCrossValidationModels,
                params.keepCrossValidationPredictions, params.keepCrossValidationFoldAssignment, params.parallelizeCrossValidation,
                params.distribution, params.tweediePower, params.quantileAlpha, params.huberAlpha, colToString(params.responseColumn),
                colToString(params.weightsColumn), colToString(params.offsetColumn), colToString(params.foldColumn), params.foldAssignment,
                params.categoricalEncoding, params.maxCategoricalLevels, params.ignoredColumns, params.ignoreConstCols,
                params.scoreEachIteration, keyToString(params.checkpoint), params.stoppingRounds, params.maxRuntimeSecs,
                params.stoppingMetric, params.stoppingTolerance, params.customMetricFunc, params.customDistributionFunc,
                params.exportCheckpointsDir).execute().body();
    }

    /**
     * Run grid search for Generic model.
     */
    public GenericV3 grid_search_generic() throws IOException {
        final Grid s = getService(Grid.class);
        return s.trainGeneric().execute().body();
    }

    public GenericV3 grid_search_generic(final GenericParametersV3 params) throws IOException {
        final Grid s = getService(Grid.class);
        return s.trainGeneric(params.path, keyToString(params.modelKey), keyToString(params.modelId), keyToString(params.trainingFrame),
                keyToString(params.validationFrame), params.nfolds, params.keepCrossValidationModels,
                params.keepCrossValidationPredictions, params.keepCrossValidationFoldAssignment, params.parallelizeCrossValidation,
                params.distribution, params.tweediePower, params.quantileAlpha, params.huberAlpha, colToString(params.responseColumn),
                colToString(params.weightsColumn), colToString(params.offsetColumn), colToString(params.foldColumn), params.foldAssignment,
                params.categoricalEncoding, params.maxCategoricalLevels, params.ignoredColumns, params.ignoreConstCols,
                params.scoreEachIteration, keyToString(params.checkpoint), params.stoppingRounds, params.maxRuntimeSecs,
                params.stoppingMetric, params.stoppingTolerance, params.customMetricFunc, params.customDistributionFunc,
                params.exportCheckpointsDir).execute().body();
    }

    /**
     * Train a PSVM model.
     */
    public PSVMV3 train_psvm() throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.trainPsvm().execute().body();
    }

    public PSVMV3 train_psvm(final PSVMParametersV3 params) throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.trainPsvm(params.hyperParam, params.kernelType, params.gamma, params.rankRatio, params.positiveWeight,
                params.negativeWeight, params.disableTrainingMetrics, params.svThreshold, params.maxIterations, params.factThreshold,
                params.feasibleThreshold, params.surrogateGapThreshold, params.muFactor, params.seed, keyToString(params.modelId),
                keyToString(params.trainingFrame), keyToString(params.validationFrame), params.nfolds, params.keepCrossValidationModels,
                params.keepCrossValidationPredictions, params.keepCrossValidationFoldAssignment, params.parallelizeCrossValidation,
                params.distribution, params.tweediePower, params.quantileAlpha, params.huberAlpha, colToString(params.responseColumn),
                colToString(params.weightsColumn), colToString(params.offsetColumn), colToString(params.foldColumn), params.foldAssignment,
                params.categoricalEncoding, params.maxCategoricalLevels, params.ignoredColumns, params.ignoreConstCols,
                params.scoreEachIteration, keyToString(params.checkpoint), params.stoppingRounds, params.maxRuntimeSecs,
                params.stoppingMetric, params.stoppingTolerance, params.customMetricFunc, params.customDistributionFunc,
                params.exportCheckpointsDir).execute().body();
    }

    /**
     * Validate a set of PSVM model builder parameters.
     */
    public PSVMV3 validate_psvm() throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.validate_parametersPsvm().execute().body();
    }

    public PSVMV3 validate_psvm(final PSVMParametersV3 params) throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.validate_parametersPsvm(params.hyperParam, params.kernelType, params.gamma, params.rankRatio, params.positiveWeight,
                params.negativeWeight, params.disableTrainingMetrics, params.svThreshold, params.maxIterations, params.factThreshold,
                params.feasibleThreshold, params.surrogateGapThreshold, params.muFactor, params.seed, keyToString(params.modelId),
                keyToString(params.trainingFrame), keyToString(params.validationFrame), params.nfolds, params.keepCrossValidationModels,
                params.keepCrossValidationPredictions, params.keepCrossValidationFoldAssignment, params.parallelizeCrossValidation,
                params.distribution, params.tweediePower, params.quantileAlpha, params.huberAlpha, colToString(params.responseColumn),
                colToString(params.weightsColumn), colToString(params.offsetColumn), colToString(params.foldColumn), params.foldAssignment,
                params.categoricalEncoding, params.maxCategoricalLevels, params.ignoredColumns, params.ignoreConstCols,
                params.scoreEachIteration, keyToString(params.checkpoint), params.stoppingRounds, params.maxRuntimeSecs,
                params.stoppingMetric, params.stoppingTolerance, params.customMetricFunc, params.customDistributionFunc,
                params.exportCheckpointsDir).execute().body();
    }

    /**
     * Run grid search for PSVM model.
     */
    public PSVMV3 grid_search_psvm() throws IOException {
        final Grid s = getService(Grid.class);
        return s.trainPsvm().execute().body();
    }

    public PSVMV3 grid_search_psvm(final PSVMParametersV3 params) throws IOException {
        final Grid s = getService(Grid.class);
        return s.trainPsvm(params.hyperParam, params.kernelType, params.gamma, params.rankRatio, params.positiveWeight,
                params.negativeWeight, params.disableTrainingMetrics, params.svThreshold, params.maxIterations, params.factThreshold,
                params.feasibleThreshold, params.surrogateGapThreshold, params.muFactor, params.seed, keyToString(params.modelId),
                keyToString(params.trainingFrame), keyToString(params.validationFrame), params.nfolds, params.keepCrossValidationModels,
                params.keepCrossValidationPredictions, params.keepCrossValidationFoldAssignment, params.parallelizeCrossValidation,
                params.distribution, params.tweediePower, params.quantileAlpha, params.huberAlpha, colToString(params.responseColumn),
                colToString(params.weightsColumn), colToString(params.offsetColumn), colToString(params.foldColumn), params.foldAssignment,
                params.categoricalEncoding, params.maxCategoricalLevels, params.ignoredColumns, params.ignoreConstCols,
                params.scoreEachIteration, keyToString(params.checkpoint), params.stoppingRounds, params.maxRuntimeSecs,
                params.stoppingMetric, params.stoppingTolerance, params.customMetricFunc, params.customDistributionFunc,
                params.exportCheckpointsDir).execute().body();
    }

    /**
     * Make a new GLM model based on existing one
     */
    public GLMModelV3 make_glm_model(final ModelKeyV3 model, final String[] names, final double[] beta) throws IOException {
        final MakeGLMModel s = getService(MakeGLMModel.class);
        return s.make_model(keyToString(model), names, beta).execute().body();
    }

    public GLMModelV3 make_glm_model(final MakeGLMModelV3 params) throws IOException {
        final MakeGLMModel s = getService(MakeGLMModel.class);
        return s.make_model(keyToString(params.model), keyToString(params.dest), params.names, params.beta, params.threshold).execute()
                .body();
    }

    /**
     * Get full regularization path
     */
    public GLMRegularizationPathV3 glm_regularization_path(final ModelKeyV3 model) throws IOException {
        final GetGLMRegPath s = getService(GetGLMRegPath.class);
        return s.extractRegularizationPath(keyToString(model)).execute().body();
    }

    public GLMRegularizationPathV3 glm_regularization_path(final GLMRegularizationPathV3 params) throws IOException {
        final GetGLMRegPath s = getService(GetGLMRegPath.class);
        return s.extractRegularizationPath(keyToString(params.model), params.lambdas, params.explainedDevianceTrain,
                params.explainedDevianceValid, params.coefficients, params.coefficientsStd, params.coefficientNames).execute().body();
    }

    /**
     * Get weighted gram matrix
     */
    public GramV3 weighted_gram_matrix(final FrameKeyV3 x) throws IOException {
        final ComputeGram s = getService(ComputeGram.class);
        return s.computeGram(keyToString(x)).execute().body();
    }

    public GramV3 weighted_gram_matrix(final GramV3 params) throws IOException {
        final ComputeGram s = getService(ComputeGram.class);
        return s.computeGram(keyToString(params.x), colToString(params.w), params.useAllFactorLevels, params.standardize,
                params.skipMissing).execute().body();
    }

    /**
     * Find synonyms using a word2vec model
     */
    public Word2VecSynonymsV3 word2vec_synonyms(final ModelKeyV3 model, final String word, final int count) throws IOException {
        final Word2VecSynonyms s = getService(Word2VecSynonyms.class);
        return s.findSynonyms(keyToString(model), word, count).execute().body();
    }

    public Word2VecSynonymsV3 word2vec_synonyms(final Word2VecSynonymsV3 params) throws IOException {
        final Word2VecSynonyms s = getService(Word2VecSynonyms.class);
        return s.findSynonyms(keyToString(params.model), params.word, params.count, params.synonyms, params.scores).execute().body();
    }

    /**
     * Transform words to vectors using a word2vec model
     */
    public Word2VecTransformV3 word2vec_transform(final ModelKeyV3 model, final FrameKeyV3 wordsFrame) throws IOException {
        final Word2VecTransform s = getService(Word2VecTransform.class);
        return s.transform(keyToString(model), keyToString(wordsFrame)).execute().body();
    }

    public Word2VecTransformV3 word2vec_transform(final ModelKeyV3 model, final FrameKeyV3 wordsFrame,
            final Word2VecModelAggregateMethod aggregateMethod) throws IOException {
        final Word2VecTransform s = getService(Word2VecTransform.class);
        return s.transform(keyToString(model), keyToString(wordsFrame), aggregateMethod).execute().body();
    }

    /**
     * Test only
     */
    public DataInfoFrameV3 glm_datainfo_frame() throws IOException {
        final DataInfoFrame s = getService(DataInfoFrame.class);
        return s.getDataInfoFrame().execute().body();
    }

    public DataInfoFrameV3 glm_datainfo_frame(final DataInfoFrameV3 params) throws IOException {
        final DataInfoFrame s = getService(DataInfoFrame.class);
        return s.getDataInfoFrame(keyToString(params.frame), params.interactions, params.useAll, params.standardize,
                params.interactionsOnly).execute().body();
    }

    /**
     * Obtain a traverseable representation of a specific tree
     */
    public TreeV3 get_tree(final ModelKeyV3 model, final int treeNumber) throws IOException {
        final Tree s = getService(Tree.class);
        return s.getTree(keyToString(model), treeNumber).execute().body();
    }

    public TreeV3 get_tree(final ModelKeyV3 model, final int treeNumber, final String treeClass) throws IOException {
        final Tree s = getService(Tree.class);
        return s.getTree(keyToString(model), treeNumber, treeClass).execute().body();
    }

    /**
     * Create a synthetic H2O Frame with random data. You can specify the number of rows/columns, as well as column types:
     * integer, real, boolean, time, string, categorical. The frame may also have a dedicated "response" column, and some
     * of the entries in the dataset may be created as missing.
     */
    public JobV3 createFrame() throws IOException {
        final CreateFrame s = getService(CreateFrame.class);
        return s.run().execute().body();
    }

    public JobV3 createFrame(final CreateFrameV3 params) throws IOException {
        final CreateFrame s = getService(CreateFrame.class);
        return s.run(keyToString(params.dest), params.rows, params.cols, params.seed, params.seedForColumnTypes, params.randomize,
                params.value, params.realRange, params.categoricalFraction, params.factors, params.integerFraction, params.integerRange,
                params.binaryFraction, params.binaryOnesFraction, params.timeFraction, params.stringFraction, params.missingFraction,
                params.hasResponse, params.responseFactors, params.positiveResponse, params._excludeFields).execute().body();
    }

    /**
     * Split an H2O Frame.
     */
    public SplitFrameV3 splitFrame() throws IOException {
        final SplitFrame s = getService(SplitFrame.class);
        return s.run().execute().body();
    }

    public SplitFrameV3 splitFrame(final SplitFrameV3 params) throws IOException {
        final SplitFrame s = getService(SplitFrame.class);
        return s.run(keyToString(params.key), keyToString(params.dataset), params.ratios, keyArrayToStringArray(params.destinationFrames))
                .execute().body();
    }

    /**
     * Create interactions between categorical columns.
     */
    public JobV3 generateInteractions(final int maxFactors) throws IOException {
        final Interaction s = getService(Interaction.class);
        return s.run(maxFactors).execute().body();
    }

    public JobV3 generateInteractions(final InteractionV3 params) throws IOException {
        final Interaction s = getService(Interaction.class);
        return s.run(keyToString(params.dest), keyToString(params.sourceFrame), params.factorColumns, params.pairwise, params.maxFactors,
                params.minOccurrence, params._excludeFields).execute().body();
    }

    /**
     * Insert missing values.
     */
    public JobV3 _missingInserter_run(final FrameKeyV3 dataset, final double fraction) throws IOException {
        final MissingInserter s = getService(MissingInserter.class);
        return s.run(keyToString(dataset), fraction).execute().body();
    }

    public JobV3 _missingInserter_run(final MissingInserterV3 params) throws IOException {
        final MissingInserter s = getService(MissingInserter.class);
        return s.run(keyToString(params.dataset), params.fraction, params.seed, params._excludeFields).execute().body();
    }

    /**
     * Row-by-row discrete cosine transforms in 1D, 2D and 3D.
     */
    public JobV3 _dctTransformer_run(final FrameKeyV3 dataset, final int[] dimensions) throws IOException {
        final DCTTransformer s = getService(DCTTransformer.class);
        return s.run(keyToString(dataset), dimensions).execute().body();
    }

    public JobV3 _dctTransformer_run(final DCTTransformerV3 params) throws IOException {
        final DCTTransformer s = getService(DCTTransformer.class);
        return s.run(keyToString(params.dataset), keyToString(params.destinationFrame), params.dimensions, params.inverse,
                params._excludeFields).execute().body();
    }

    /**
     * Tabulate one column vs another.
     */
    public TabulateV3 _tabulate_run(final FrameKeyV3 dataset, final ColSpecifierV3 predictor, final ColSpecifierV3 response)
            throws IOException {
        final Tabulate s = getService(Tabulate.class);
        return s.run(keyToString(dataset), colToString(predictor), colToString(response)).execute().body();
    }

    public TabulateV3 _tabulate_run(final TabulateV3 params) throws IOException {
        final Tabulate s = getService(Tabulate.class);
        return s.run(keyToString(params.dataset), colToString(params.predictor), colToString(params.response), colToString(params.weight),
                params.nbinsPredictor, params.nbinsResponse).execute().body();
    }

    /**
     * Import raw data files into a single-column H2O Frame.
     */
    public Call<ImportFilesV3> importFiles(final String path) {
        final ImportFiles s = getService(ImportFiles.class);
        return s.importFiles(path);
    }

    public ImportFilesV3 importFiles(final String path, final String pattern) throws IOException {
        final ImportFiles s = getService(ImportFiles.class);
        return s.importFiles(path, pattern, "").execute().body();
    }

    public ImportFilesV3 importFiles(final String path, final String pattern, final String _excludeFields) throws IOException {
        final ImportFiles s = getService(ImportFiles.class);
        return s.importFiles(path, pattern, _excludeFields).execute().body();
    }

    /**
     * Import raw data files from multiple directories (or different data sources) into a single-column H2O Frame.
     */
    public ImportFilesMultiV3 importFilesMulti(final String[] paths) throws IOException {
        final ImportFilesMulti s = getService(ImportFilesMulti.class);
        return s.importFilesMulti(paths).execute().body();
    }

    public ImportFilesMultiV3 importFilesMulti(final String[] paths, final String pattern) throws IOException {
        final ImportFilesMulti s = getService(ImportFilesMulti.class);
        return s.importFilesMulti(paths, pattern, "").execute().body();
    }

    public ImportFilesMultiV3 importFilesMulti(final String[] paths, final String pattern, final String _excludeFields) throws IOException {
        final ImportFilesMulti s = getService(ImportFilesMulti.class);
        return s.importFilesMulti(paths, pattern, _excludeFields).execute().body();
    }

    /**
     * Import SQL table into an H2O Frame.
     */
    public JobV3 importSqlTable(final String connectionUrl, final String username, final String password) throws IOException {
        final ImportSQLTable s = getService(ImportSQLTable.class);
        return s.importSQLTable(connectionUrl, username, password).execute().body();
    }

    public JobV3 importSqlTable(final ImportSQLTableV99 params) throws IOException {
        final ImportSQLTable s = getService(ImportSQLTable.class);
        return s.importSQLTable(params.connectionUrl, params.table, params.selectQuery, params.useTempTable, params.tempTableName,
                params.username, params.password, params.columns, params.fetchMode, params._excludeFields).execute().body();
    }

    /**
     * Import Hive table into an H2O Frame.
     */
    public JobV3 importHiveTable(final String table) throws IOException {
        final ImportHiveTable s = getService(ImportHiveTable.class);
        return s.importHiveTable(table).execute().body();
    }

    public JobV3 importHiveTable(final ImportHiveTableV3 params) throws IOException {
        final ImportHiveTable s = getService(ImportHiveTable.class);
        return s.importHiveTable(params.database, params.table, params.partitions, params.allowMultiFormat, params._excludeFields)
                .execute().body();
    }

    /**
     * Guess the parameters for parsing raw byte-oriented data into an H2O Frame.
     */
    public Call<ParseSetupV3> guessParseSetup(final FrameKeyV3[] sourceFrames) {
        return guessParseSetup(keyArrayToStringArray(sourceFrames));
    }

    public Call<ParseSetupV3> guessParseSetup(final String[] sourceFrames) {
        final ParseSetup s = getService(ParseSetup.class);
        return s.guessSetup(sourceFrames);
    }

    public ParseSetupV3 guessParseSetup(final ParseSetupV3 params) throws IOException {
        final ParseSetup s = getService(ParseSetup.class);
        return s.guessSetup(keyArrayToStringArray(params.sourceFrames), params.parseType, params.separator, params.singleQuotes,
                params.checkHeader, params.columnNames, params.skippedColumns, params.columnTypes, params.naStrings,
                params.columnNameFilter, params.columnOffset, params.columnCount, params.totalFilteredColumnCount,
                params.customNonDataLineMarkers, keyToString(params.decryptTool), params._excludeFields).execute().body();
    }

    /**
     * Parse a raw byte-oriented Frame into a useful columnar data Frame.
     */
    public Call<ParseV3> parse(final ParseV3 params) {
        final Parse s = getService(Parse.class);
        return s.parse(keyToString(params.destinationFrame), keyArrayToStringArray(params.sourceFrames), params.parseType,
                params.separator, params.singleQuotes, params.checkHeader, params.numberColumns, params.columnNames, params.columnTypes,
                params.skippedColumns, params.domains, params.naStrings, params.chunkSize, params.deleteOnDone, params.blocking,
                keyToString(params.decryptTool), params.customNonDataLineMarkers, params._excludeFields);
    }

    /**
     * Install a decryption tool for parsing of encrypted data.
     */
    public DecryptionSetupV3 setupDecryption() throws IOException {
        final DecryptionSetup s = getService(DecryptionSetup.class);
        return s.setupDecryption().execute().body();
    }

    public DecryptionSetupV3 setupDecryption(final DecryptionSetupV3 params) throws IOException {
        final DecryptionSetup s = getService(DecryptionSetup.class);
        return s.setupDecryption(keyToString(params.decryptToolId), params.decryptImpl, keyToString(params.keystoreId),
                params.keystoreType, params.keyAlias, params.password, params.cipherSpec, params._excludeFields).execute().body();
    }

    /**
     * Parse a raw byte-oriented Frame into a useful columnar data Frame.
     */
    public JobV3 parseSvmLight(final FrameKeyV3[] sourceFrames) throws IOException {
        final ParseSVMLight s = getService(ParseSVMLight.class);
        return s.parseSVMLight(keyArrayToStringArray(sourceFrames)).execute().body();
    }

    public JobV3 parseSvmLight(final FrameKeyV3 destinationFrame, final FrameKeyV3[] sourceFrames) throws IOException {
        final ParseSVMLight s = getService(ParseSVMLight.class);
        return s.parseSVMLight(keyToString(destinationFrame), keyArrayToStringArray(sourceFrames), "").execute().body();
    }

    public JobV3 parseSvmLight(final FrameKeyV3 destinationFrame, final FrameKeyV3[] sourceFrames, final String _excludeFields)
            throws IOException {
        final ParseSVMLight s = getService(ParseSVMLight.class);
        return s.parseSVMLight(keyToString(destinationFrame), keyArrayToStringArray(sourceFrames), _excludeFields).execute().body();
    }

    /**
     * The endpoint used to let H2O know from external services that it should keep running.
     */
    public PingV3 ping() throws IOException {
        final Ping s = getService(Ping.class);
        return s.ping().execute().body();
    }

    public PingV3 ping(final String _excludeFields) throws IOException {
        final Ping s = getService(Ping.class);
        return s.ping(_excludeFields).execute().body();
    }

    /**
     * Determine the status of the nodes in the H2O cloud.
     */
    public CloudV3 cloudStatus() throws IOException {
        final Cloud s = getService(Cloud.class);
        return s.status().execute().body();
    }

    public CloudV3 cloudStatus(final boolean skipTicks) throws IOException {
        final Cloud s = getService(Cloud.class);
        return s.status(skipTicks, "").execute().body();
    }

    public CloudV3 cloudStatus(final boolean skipTicks, final String _excludeFields) throws IOException {
        final Cloud s = getService(Cloud.class);
        return s.status(skipTicks, _excludeFields).execute().body();
    }

    /**
     * Determine the status of the nodes in the H2O cloud.
     */
    public CloudV3 cloudStatusMinimal() throws IOException {
        final Cloud s = getService(Cloud.class);
        return s.head().execute().body();
    }

    public CloudV3 cloudStatusMinimal(final boolean skipTicks) throws IOException {
        final Cloud s = getService(Cloud.class);
        return s.head(skipTicks, "").execute().body();
    }

    public CloudV3 cloudStatusMinimal(final boolean skipTicks, final String _excludeFields) throws IOException {
        final Cloud s = getService(Cloud.class);
        return s.head(skipTicks, _excludeFields).execute().body();
    }

    /**
     * Lock the cloud.
     */
    public CloudLockV3 cloudLock() throws IOException {
        final CloudLock s = getService(CloudLock.class);
        return s.lock().execute().body();
    }

    public CloudLockV3 cloudLock(final String reason) throws IOException {
        final CloudLock s = getService(CloudLock.class);
        return s.lock(reason, "").execute().body();
    }

    public CloudLockV3 cloudLock(final String reason, final String _excludeFields) throws IOException {
        final CloudLock s = getService(CloudLock.class);
        return s.lock(reason, _excludeFields).execute().body();
    }

    /**
     * Get a list of all the H2O Jobs (long-running actions).
     */
    public Call<JobsV3> jobs() {
        final Jobs s = getService(Jobs.class);
        return s.list();
    }

    public Call<JobsV3> jobs(final JobKeyV3 jobId) {
        final Jobs s = getService(Jobs.class);
        return s.list(keyToString(jobId), "");
    }

    public Call<JobsV3> jobs(final JobKeyV3 jobId, final String _excludeFields) {
        final Jobs s = getService(Jobs.class);
        return s.list(keyToString(jobId), _excludeFields);
    }

    /**
     * Debugging tool that provides information on current communication between nodes.
     */
    public TimelineV3 timeline() throws IOException {
        final Timeline s = getService(Timeline.class);
        return s.fetch().execute().body();
    }

    public TimelineV3 timeline(final String _excludeFields) throws IOException {
        final Timeline s = getService(Timeline.class);
        return s.fetch(_excludeFields).execute().body();
    }

    /**
     * Report real-time profiling information for all nodes (sorted, aggregated stack traces).
     */
    public ProfilerV3 profiler(final int depth) throws IOException {
        final Profiler s = getService(Profiler.class);
        return s.fetch(depth).execute().body();
    }

    public ProfilerV3 profiler(final int depth, final String _excludeFields) throws IOException {
        final Profiler s = getService(Profiler.class);
        return s.fetch(depth, _excludeFields).execute().body();
    }

    /**
     * Report stack traces for all threads on all nodes.
     */
    public JStackV3 stacktraces() throws IOException {
        final JStack s = getService(JStack.class);
        return s.fetch().execute().body();
    }

    public JStackV3 stacktraces(final String _excludeFields) throws IOException {
        final JStack s = getService(JStack.class);
        return s.fetch(_excludeFields).execute().body();
    }

    /**
     * Run a network test to measure the performance of the cluster interconnect.
     */
    public NetworkTestV3 testNetwork() throws IOException {
        final NetworkTest s = getService(NetworkTest.class);
        return s.fetch().execute().body();
    }

    public NetworkTestV3 testNetwork(final String _excludeFields) throws IOException {
        final NetworkTest s = getService(NetworkTest.class);
        return s.fetch(_excludeFields).execute().body();
    }

    /**
     * Unlock all keys in the H2O distributed K/V store, to attempt to recover from a crash.
     */
    public UnlockKeysV3 unlockAllKeys() throws IOException {
        final UnlockKeys s = getService(UnlockKeys.class);
        return s.unlock().execute().body();
    }

    public UnlockKeysV3 unlockAllKeys(final String _excludeFields) throws IOException {
        final UnlockKeys s = getService(UnlockKeys.class);
        return s.unlock(_excludeFields).execute().body();
    }

    /**
     * Shut down the cluster.
     */
    public ShutdownV3 shutdownCluster() throws IOException {
        final Shutdown s = getService(Shutdown.class);
        return s.shutdown().execute().body();
    }

    public ShutdownV3 shutdownCluster(final String _excludeFields) throws IOException {
        final Shutdown s = getService(Shutdown.class);
        return s.shutdown(_excludeFields).execute().body();
    }

    /**
     * Return information about this H2O cluster.
     */
    public AboutV3 about() throws IOException {
        final About s = getService(About.class);
        return s.get().execute().body();
    }

    public AboutV3 about(final String _excludeFields) throws IOException {
        final About s = getService(About.class);
        return s.get(_excludeFields).execute().body();
    }

    /**
     * Return the list of (almost) all REST API endpoints.
     */
    public MetadataV3 endpoints() throws IOException {
        final Metadata s = getService(Metadata.class);
        return s.listRoutes().execute().body();
    }

    public MetadataV3 endpoints(final MetadataV3 params) throws IOException {
        final Metadata s = getService(Metadata.class);
        return s.listRoutes(params.num, params.httpMethod, params.path, params.classname, params.schemaname, params._excludeFields)
                .execute().body();
    }

    /**
     * Return the REST API endpoint metadata, including documentation, for the endpoint specified by path or index.
     */
    public MetadataV3 endpoint(final String path) throws IOException {
        final Metadata s = getService(Metadata.class);
        return s.fetchRoute(path).execute().body();
    }

    public MetadataV3 endpoint(final MetadataV3 params) throws IOException {
        final Metadata s = getService(Metadata.class);
        return s.fetchRoute(params.path, params.num, params.httpMethod, params.classname, params.schemaname, params._excludeFields)
                .execute().body();
    }

    /**
     * Return the REST API schema metadata for specified schema class.
     */
    public MetadataV3 schemaForClass(final String classname) throws IOException {
        final Metadata s = getService(Metadata.class);
        return s.fetchSchemaMetadataByClass(classname).execute().body();
    }

    public MetadataV3 schemaForClass(final MetadataV3 params) throws IOException {
        final Metadata s = getService(Metadata.class);
        return s.fetchSchemaMetadataByClass(params.classname, params.num, params.httpMethod, params.path, params.schemaname,
                params._excludeFields).execute().body();
    }

    /**
     * Return the REST API schema metadata for specified schema.
     */
    public MetadataV3 schema(final String schemaname) throws IOException {
        final Metadata s = getService(Metadata.class);
        return s.fetchSchemaMetadata(schemaname).execute().body();
    }

    public MetadataV3 schema(final MetadataV3 params) throws IOException {
        final Metadata s = getService(Metadata.class);
        return s.fetchSchemaMetadata(params.schemaname, params.num, params.httpMethod, params.path, params.classname, params._excludeFields)
                .execute().body();
    }

    /**
     * Return list of all REST API schemas.
     */
    public MetadataV3 schemas() throws IOException {
        final Metadata s = getService(Metadata.class);
        return s.listSchemas().execute().body();
    }

    public MetadataV3 schemas(final MetadataV3 params) throws IOException {
        final Metadata s = getService(Metadata.class);
        return s.listSchemas(params.num, params.httpMethod, params.path, params.classname, params.schemaname, params._excludeFields)
                .execute().body();
    }

    /**
     * Typeahead hander for filename completion.
     */
    public TypeaheadV3 typeaheadFileSuggestions(final String src) throws IOException {
        final Typeahead s = getService(Typeahead.class);
        return s.files(src).execute().body();
    }

    public TypeaheadV3 typeaheadFileSuggestions(final String src, final int limit) throws IOException {
        final Typeahead s = getService(Typeahead.class);
        return s.files(src, limit, "").execute().body();
    }

    public TypeaheadV3 typeaheadFileSuggestions(final String src, final int limit, final String _excludeFields) throws IOException {
        final Typeahead s = getService(Typeahead.class);
        return s.files(src, limit, _excludeFields).execute().body();
    }

    /**
     * Get the status of the given H2O Job (long-running action).
     */
    public JobsV3 job(final JobKeyV3 jobId) throws IOException {
        final Jobs s = getService(Jobs.class);
        return s.fetch(keyToString(jobId)).execute().body();
    }

    public JobsV3 job(final JobKeyV3 jobId, final String _excludeFields) throws IOException {
        final Jobs s = getService(Jobs.class);
        return s.fetch(keyToString(jobId), _excludeFields).execute().body();
    }

    /**
     * Cancel a running job.
     */
    public JobsV3 cancelJob(final JobKeyV3 jobId) throws IOException {
        final Jobs s = getService(Jobs.class);
        return s.cancel(keyToString(jobId)).execute().body();
    }

    public JobsV3 cancelJob(final JobKeyV3 jobId, final String _excludeFields) throws IOException {
        final Jobs s = getService(Jobs.class);
        return s.cancel(keyToString(jobId), _excludeFields).execute().body();
    }

    /**
     * Find a value within a Frame.
     */
    public FindV3 findInFrame(final FrameV3 key, final long row) throws IOException {
        final Find s = getService(Find.class);
        return s.find(key, row).execute().body();
    }

    public FindV3 findInFrame(final FindV3 params) throws IOException {
        final Find s = getService(Find.class);
        return s.find(params.key, params.column, params.row, params.match, params._excludeFields).execute().body();
    }

    /**
     * Export a Frame to the given path with optional overwrite.
     */
    public Call<FramesV3> exportFrame(final FrameKeyV3 frameId) {
        final Frames s = getService(Frames.class);
        return s.export(keyToString(frameId));
    }

    public Call<FramesV3> exportFrame(final FramesV3 params) {
        final Frames s = getService(Frames.class);
        return s.export(keyToString(params.frameId), params.column, params.rowOffset, params.rowCount, params.columnOffset,
                params.fullColumnCount, params.columnCount, params.findCompatibleModels, params.path, params.force, params.numParts,
                params.compression, params.separator, params._excludeFields);
    }

    /**
     * Return the summary metrics for a column, e.g. min, max, mean, sigma, percentiles, etc.
     */
    public FramesV3 frameColumnSummary(final FrameKeyV3 frameId, final String column) throws IOException {
        final Frames s = getService(Frames.class);
        return s.columnSummary(keyToString(frameId), column).execute().body();
    }

    public FramesV3 frameColumnSummary(final FramesV3 params) throws IOException {
        final Frames s = getService(Frames.class);
        return s.columnSummary(keyToString(params.frameId), params.column, params.rowOffset, params.rowCount, params.columnOffset,
                params.fullColumnCount, params.columnCount, params.findCompatibleModels, params.path, params.force, params.numParts,
                params.compression, params.separator, params._excludeFields).execute().body();
    }

    /**
     * Return the domains for the specified categorical column ("null" if the column is not a categorical).
     */
    public FramesV3 frameColumnDomain(final FrameKeyV3 frameId, final String column) throws IOException {
        final Frames s = getService(Frames.class);
        return s.columnDomain(keyToString(frameId), column).execute().body();
    }

    public FramesV3 frameColumnDomain(final FramesV3 params) throws IOException {
        final Frames s = getService(Frames.class);
        return s.columnDomain(keyToString(params.frameId), params.column, params.rowOffset, params.rowCount, params.columnOffset,
                params.fullColumnCount, params.columnCount, params.findCompatibleModels, params.path, params.force, params.numParts,
                params.compression, params.separator, params._excludeFields).execute().body();
    }

    /**
     * Return the specified column from a Frame.
     */
    public FramesV3 frameColumn(final FrameKeyV3 frameId, final String column) throws IOException {
        final Frames s = getService(Frames.class);
        return s.column(keyToString(frameId), column).execute().body();
    }

    public FramesV3 frameColumn(final FramesV3 params) throws IOException {
        final Frames s = getService(Frames.class);
        return s.column(keyToString(params.frameId), params.column, params.rowOffset, params.rowCount, params.columnOffset,
                params.fullColumnCount, params.columnCount, params.findCompatibleModels, params.path, params.force, params.numParts,
                params.compression, params.separator, params._excludeFields).execute().body();
    }

    /**
     * Return all the columns from a Frame.
     */
    public FramesV3 frameColumns(final FrameKeyV3 frameId) throws IOException {
        final Frames s = getService(Frames.class);
        return s.columns(keyToString(frameId)).execute().body();
    }

    public FramesV3 frameColumns(final FramesV3 params) throws IOException {
        final Frames s = getService(Frames.class);
        return s.columns(keyToString(params.frameId), params.column, params.rowOffset, params.rowCount, params.columnOffset,
                params.fullColumnCount, params.columnCount, params.findCompatibleModels, params.path, params.force, params.numParts,
                params.compression, params.separator, params._excludeFields).execute().body();
    }

    /**
     * Return a Frame, including the histograms, after forcing computation of rollups.
     */
    public Call<FramesV3> frameSummary(final FrameKeyV3 frameId) {
        return frameSummary(keyToString(frameId));
    }

    public Call<FramesV3> frameSummary(final String frameId) {
        final Frames s = getService(Frames.class);
        return s.summary(frameId);
    }

    public FramesV3 frameSummary(final FramesV3 params) throws IOException {
        final Frames s = getService(Frames.class);
        return s.summary(keyToString(params.frameId), params.column, params.rowOffset, params.rowCount, params.columnOffset,
                params.fullColumnCount, params.columnCount, params.findCompatibleModels, params.path, params.force, params.numParts,
                params.compression, params.separator, params._excludeFields).execute().body();
    }

    /**
     * Return a basic info about Frame to fill client Rapid expression cache.
     */
    public FramesV3 lightFrame(final FrameKeyV3 frameId) throws IOException {
        final Frames s = getService(Frames.class);
        return s.fetchLight(keyToString(frameId)).execute().body();
    }

    public FramesV3 lightFrame(final FramesV3 params) throws IOException {
        final Frames s = getService(Frames.class);
        return s.fetchLight(keyToString(params.frameId), params.column, params.rowOffset, params.rowCount, params.columnOffset,
                params.fullColumnCount, params.columnCount, params.findCompatibleModels, params.path, params.force, params.numParts,
                params.compression, params.separator, params._excludeFields).execute().body();
    }

    /**
     * Return the specified Frame.
     */
    public FramesV3 frame(final FrameKeyV3 frameId) throws IOException {
        final Frames s = getService(Frames.class);
        return s.fetch(keyToString(frameId)).execute().body();
    }

    public FramesV3 frame(final FramesV3 params) throws IOException {
        final Frames s = getService(Frames.class);
        return s.fetch(keyToString(params.frameId), params.column, params.rowOffset, params.rowCount, params.columnOffset,
                params.fullColumnCount, params.columnCount, params.findCompatibleModels, params.path, params.force, params.numParts,
                params.compression, params.separator, params._excludeFields).execute().body();
    }

    /**
     * Return all Frames in the H2O distributed K/V store.
     */
    public Call<FramesListV3> frames() {
        final Frames s = getService(Frames.class);
        return s.list();
    }

    public Call<FramesListV3> frames(final FrameKeyV3 frameId) {
        final Frames s = getService(Frames.class);
        return s.list(keyToString(frameId), "");
    }

    public Call<FramesListV3> frames(final FrameKeyV3 frameId, final String _excludeFields) {
        final Frames s = getService(Frames.class);
        return s.list(keyToString(frameId), _excludeFields);
    }

    /**
     * Delete the specified Frame from the H2O distributed K/V store.
     */
    public Call<FramesV3> deleteFrame(final FrameKeyV3 frameId) {
        final Frames s = getService(Frames.class);
        return s.delete(keyToString(frameId));
    }

    public Call<FramesV3> deleteFrame(final FramesV3 params) {
        final Frames s = getService(Frames.class);
        return s.delete(keyToString(params.frameId), params.column, params.rowOffset, params.rowCount, params.columnOffset,
                params.fullColumnCount, params.columnCount, params.findCompatibleModels, params.path, params.force, params.numParts,
                params.compression, params.separator, params._excludeFields);
    }

    /**
     * Delete all Frames from the H2O distributed K/V store.
     */
    public Call<FramesV3> deleteAllFrames() {
        final Frames s = getService(Frames.class);
        return s.deleteAll();
    }

    public Call<FramesV3> deleteAllFrames(final FramesV3 params) {
        final Frames s = getService(Frames.class);
        return s.deleteAll(keyToString(params.frameId), params.column, params.rowOffset, params.rowCount, params.columnOffset,
                params.fullColumnCount, params.columnCount, params.findCompatibleModels, params.path, params.force, params.numParts,
                params.compression, params.separator, params._excludeFields);
    }

    /**
     * Return information about chunks for a given frame.
     */
    public FrameChunksV3 frameChunks(final FrameKeyV3 frameId) throws IOException {
        final FrameChunks s = getService(FrameChunks.class);
        return s.fetch(keyToString(frameId)).execute().body();
    }

    /**
     * Return the specified Model from the H2O distributed K/V store, optionally with the list of compatible Frames.
     */
    public Call<ModelsV3> model(final ModelKeyV3 modelId) {
        final Models s = getService(Models.class);
        return s.fetch(keyToString(modelId));
    }

    public Call<ModelsV3> model(final ModelsV3 params) {
        final Models s = getService(Models.class);
        return s.fetch(keyToString(params.modelId), params.preview, params.findCompatibleFrames, params._excludeFields);
    }

    /**
     * Return all Models from the H2O distributed K/V store.
     */
    public Call<ModelsV3> models() {
        final Models s = getService(Models.class);
        return s.list();
    }

    public Call<ModelsV3> models(final ModelsV3 params) {
        final Models s = getService(Models.class);
        return s.list(keyToString(params.modelId), params.preview, params.findCompatibleFrames, params._excludeFields);
    }

    /**
     * Delete the specified Model from the H2O distributed K/V store.
     */
    public ModelsV3 deleteModel(final ModelKeyV3 modelId) throws IOException {
        final Models s = getService(Models.class);
        return s.delete(keyToString(modelId)).execute().body();
    }

    public ModelsV3 deleteModel(final ModelsV3 params) throws IOException {
        final Models s = getService(Models.class);
        return s.delete(keyToString(params.modelId), params.preview, params.findCompatibleFrames, params._excludeFields).execute().body();
    }

    /**
     * Delete all Models from the H2O distributed K/V store.
     */
    public ModelsV3 deleteAllModels() throws IOException {
        final Models s = getService(Models.class);
        return s.deleteAll().execute().body();
    }

    public ModelsV3 deleteAllModels(final ModelsV3 params) throws IOException {
        final Models s = getService(Models.class);
        return s.deleteAll(keyToString(params.modelId), params.preview, params.findCompatibleFrames, params._excludeFields).execute()
                .body();
    }

    /**
     * Return potentially abridged model suitable for viewing in a browser (currently only used for java model code).
     */
    public StreamingSchema modelPreview(final ModelKeyV3 modelId) throws IOException {
        final Models s = getService(Models.class);
        return s.fetchPreview(keyToString(modelId)).execute().body();
    }

    public StreamingSchema modelPreview(final ModelsV3 params) throws IOException {
        final Models s = getService(Models.class);
        return s.fetchPreview(keyToString(params.modelId), params.preview, params.findCompatibleFrames, params._excludeFields).execute()
                .body();
    }

    /**
     * [DEPRECATED] Return the stream containing model implementation in Java code.
     */
    public StreamingSchema modelJavaCode(final ModelKeyV3 modelId) throws IOException {
        final Models s = getService(Models.class);
        return s.fetchJavaCode(keyToString(modelId)).execute().body();
    }

    public StreamingSchema modelJavaCode(final ModelsV3 params) throws IOException {
        final Models s = getService(Models.class);
        return s.fetchJavaCode(keyToString(params.modelId), params.preview, params.findCompatibleFrames, params._excludeFields).execute()
                .body();
    }

    /**
     * Return the model in the MOJO format. This format can then be interpreted by gen_model.jar in order to perform
     * prediction / scoring. Currently works for GBM and DRF algos only.
     */
    public StreamingSchema modelMojo(final ModelKeyV3 modelId) throws IOException {
        final Models s = getService(Models.class);
        return s.fetchMojo(keyToString(modelId)).execute().body();
    }

    public StreamingSchema modelMojo(final ModelsV3 params) throws IOException {
        final Models s = getService(Models.class);
        return s.fetchMojo(keyToString(params.modelId), params.preview, params.findCompatibleFrames, params._excludeFields).execute()
                .body();
    }

    /**
     * Create data for partial dependence plot(s) for the specified model and frame.
     */
    public JobV3 makePDP() throws IOException {
        final PartialDependence s = getService(PartialDependence.class);
        return s.makePartialDependence().execute().body();
    }

    public JobV3 makePDP(final PartialDependenceV3 params) throws IOException {
        final PartialDependence s = getService(PartialDependence.class);
        return s.makePartialDependence(keyToString(params.modelId), keyToString(params.frameId), params.rowIndex, params.cols,
                params.weightColumnIndex, params.addMissingNa, params.nbins, params.userSplits, params.userCols, params.numUserSplits,
                params.colPairs2dpdp, keyToString(params.destinationKey)).execute().body();
    }

    /**
     * Fetch partial dependence data.
     */
    public PartialDependenceV3 fetchPDP(final String name) throws IOException {
        final PartialDependence s = getService(PartialDependence.class);
        return s.fetchPartialDependence(name).execute().body();
    }

    public PartialDependenceV3 fetchPDP(final String name, final String type, final String url) throws IOException {
        final PartialDependence s = getService(PartialDependence.class);
        return s.fetchPartialDependence(name, type, url).execute().body();
    }

    /**
     * Import given binary model into H2O.
     */
    public ModelsV3 importModel(final ModelKeyV3 modelId) throws IOException {
        final Models s = getService(Models.class);
        return s.importModel(keyToString(modelId)).execute().body();
    }

    public ModelsV3 importModel(final ModelImportV3 params) throws IOException {
        final Models s = getService(Models.class);
        return s.importModel(keyToString(params.modelId), params.dir, params.force, params._excludeFields).execute().body();
    }

    /**
     * Export given model.
     */
    public ModelExportV3 exportModel(final ModelKeyV3 modelId) throws IOException {
        final Models s = getService(Models.class);
        return s.exportModel(keyToString(modelId)).execute().body();
    }

    public ModelExportV3 exportModel(final ModelExportV3 params) throws IOException {
        final Models s = getService(Models.class);
        return s.exportModel(keyToString(params.modelId), params.dir, params.force, params._excludeFields).execute().body();
    }

    /**
     * Export given model as Mojo.
     */
    public ModelExportV3 exportMojo(final ModelKeyV3 modelId) throws IOException {
        final Models s = getService(Models.class);
        return s.exportMojo(keyToString(modelId)).execute().body();
    }

    public ModelExportV3 exportMojo(final ModelExportV3 params) throws IOException {
        final Models s = getService(Models.class);
        return s.exportMojo(keyToString(params.modelId), params.dir, params.force, params._excludeFields).execute().body();
    }

    /**
     * Export given model details in json format.
     */
    public ModelExportV3 exportModelDetails(final ModelKeyV3 modelId) throws IOException {
        final Models s = getService(Models.class);
        return s.exportModelDetails(keyToString(modelId)).execute().body();
    }

    public ModelExportV3 exportModelDetails(final ModelExportV3 params) throws IOException {
        final Models s = getService(Models.class);
        return s.exportModelDetails(keyToString(params.modelId), params.dir, params.force, params._excludeFields).execute().body();
    }

    /**
     * Return the specified grid search result.
     */
    public GridSchemaV99 grid(final GridKeyV3 gridId) throws IOException {
        final Grids s = getService(Grids.class);
        return s.fetch(keyToString(gridId)).execute().body();
    }

    public GridSchemaV99 grid(final GridSchemaV99 params) throws IOException {
        final Grids s = getService(Grids.class);
        return s.fetch(keyToString(params.gridId), params.sortBy, params.decreasing, keyArrayToStringArray(params.modelIds)).execute()
                .body();
    }

    /**
     * Return all grids from H2O distributed K/V store.
     */
    public GridsV99 grids() throws IOException {
        final Grids s = getService(Grids.class);
        return s.list().execute().body();
    }

    /**
     * Return a new unique model_id for the specified algorithm.
     */
    public ModelIdV3 newModelId(final String algo) throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.calcModelId(algo).execute().body();
    }

    public ModelIdV3 newModelId(final String algo, final String _excludeFields) throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.calcModelId(algo, _excludeFields).execute().body();
    }

    /**
     * Return the Model Builder metadata for the specified algorithm.
     */
    public ModelBuildersV3 modelBuilder(final String algo) throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.fetch(algo).execute().body();
    }

    public ModelBuildersV3 modelBuilder(final String algo, final String _excludeFields) throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.fetch(algo, _excludeFields).execute().body();
    }

    /**
     * Return the Model Builder metadata for all available algorithms.
     */
    public ModelBuildersV3 modelBuilders() throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.list().execute().body();
    }

    public ModelBuildersV3 modelBuilders(final String algo) throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.list(algo, "").execute().body();
    }

    public ModelBuildersV3 modelBuilders(final String algo, final String _excludeFields) throws IOException {
        final ModelBuilders s = getService(ModelBuilders.class);
        return s.list(algo, _excludeFields).execute().body();
    }

    /**
     * Return the saved scoring metrics for the specified Model and Frame.
     */
    public ModelMetricsListSchemaV3 _mmFetch1(final ModelKeyV3 model, final FrameKeyV3 frame) throws IOException {
        final ModelMetrics s = getService(ModelMetrics.class);
        return s.fetch(keyToString(model), keyToString(frame)).execute().body();
    }

    public ModelMetricsListSchemaV3 _mmFetch1(final ModelMetricsListSchemaV3 params) throws IOException {
        final ModelMetrics s = getService(ModelMetrics.class);
        return s.fetch(keyToString(params.model), keyToString(params.frame), keyToString(params.predictionsFrame),
                keyToString(params.deviancesFrame), params.reconstructionError, params.reconstructionErrorPerFeature,
                params.deepFeaturesHiddenLayer, params.deepFeaturesHiddenLayerName, params.reconstructTrain, params.projectArchetypes,
                params.reverseTransform, params.leafNodeAssignment, params.leafNodeAssignmentType, params.predictStagedProba,
                params.predictContributions, params.featureFrequencies, params.exemplarIndex, params.deviances, params.customMetricFunc,
                params._excludeFields).execute().body();
    }

    /**
     * Return the saved scoring metrics for the specified Model and Frame.
     */
    public ModelMetricsListSchemaV3 _mmDelete1(final ModelKeyV3 model, final FrameKeyV3 frame) throws IOException {
        final ModelMetrics s = getService(ModelMetrics.class);
        return s.delete(keyToString(model), keyToString(frame)).execute().body();
    }

    public ModelMetricsListSchemaV3 _mmDelete1(final ModelMetricsListSchemaV3 params) throws IOException {
        final ModelMetrics s = getService(ModelMetrics.class);
        return s.delete(keyToString(params.model), keyToString(params.frame), keyToString(params.predictionsFrame),
                keyToString(params.deviancesFrame), params.reconstructionError, params.reconstructionErrorPerFeature,
                params.deepFeaturesHiddenLayer, params.deepFeaturesHiddenLayerName, params.reconstructTrain, params.projectArchetypes,
                params.reverseTransform, params.leafNodeAssignment, params.leafNodeAssignmentType, params.predictStagedProba,
                params.predictContributions, params.featureFrequencies, params.exemplarIndex, params.deviances, params.customMetricFunc,
                params._excludeFields).execute().body();
    }

    /**
     * Return the scoring metrics for the specified Frame with the specified Model.  If the Frame has already been scored
     * with the Model then cached results will be returned; otherwise predictions for all rows in the Frame will be
     * generated and the metrics will be returned.
     */
    public ModelMetricsListSchemaV3 score(final ModelKeyV3 model, final FrameKeyV3 frame) throws IOException {
        final ModelMetrics s = getService(ModelMetrics.class);
        return s.score(keyToString(model), keyToString(frame)).execute().body();
    }

    public ModelMetricsListSchemaV3 score(final ModelMetricsListSchemaV3 params) throws IOException {
        final ModelMetrics s = getService(ModelMetrics.class);
        return s.score(keyToString(params.model), keyToString(params.frame), keyToString(params.predictionsFrame),
                keyToString(params.deviancesFrame), params.reconstructionError, params.reconstructionErrorPerFeature,
                params.deepFeaturesHiddenLayer, params.deepFeaturesHiddenLayerName, params.reconstructTrain, params.projectArchetypes,
                params.reverseTransform, params.leafNodeAssignment, params.leafNodeAssignmentType, params.predictStagedProba,
                params.predictContributions, params.featureFrequencies, params.exemplarIndex, params.deviances, params.customMetricFunc,
                params._excludeFields).execute().body();
    }

    /**
     * Score (generate predictions) for the specified Frame with the specified Model.  Both the Frame of predictions and
     * the metrics will be returned.
     */
    public Call<ModelMetricsListSchemaV3> predict(final ModelKeyV3 model, final FrameKeyV3 frame) {
        final Predictions s = getService(Predictions.class);
        return s.predict(keyToString(model), keyToString(frame), null);
    }

    public Call<ModelMetricsListSchemaV3> predict(final ModelMetricsListSchemaV3 params) {
        final Predictions s = getService(Predictions.class);
        return s.predict(keyToString(params.model), keyToString(params.frame), keyToString(params.predictionsFrame),
                keyToString(params.deviancesFrame), params.reconstructionError, params.reconstructionErrorPerFeature,
                params.deepFeaturesHiddenLayer, params.deepFeaturesHiddenLayerName, params.reconstructTrain, params.projectArchetypes,
                params.reverseTransform, params.leafNodeAssignment, params.leafNodeAssignmentType, params.predictStagedProba,
                params.predictContributions, params.featureFrequencies, params.exemplarIndex, params.deviances, params.customMetricFunc,
                params._excludeFields);
    }

    /**
     * Score (generate predictions) for the specified Frame with the specified Model.  Both the Frame of predictions and
     * the metrics will be returned.
     */
    public Call<JobV3> predictAsync(final ModelKeyV3 model, final FrameKeyV3 frame) {
        final Predictions s = getService(Predictions.class);
        return s.predictAsync(keyToString(model), keyToString(frame));
    }

    public Call<JobV3> predictAsync(final ModelMetricsListSchemaV3 params) throws IOException {
        final Predictions s = getService(Predictions.class);
        return s.predictAsync(keyToString(params.model), keyToString(params.frame), keyToString(params.predictionsFrame),
                keyToString(params.deviancesFrame), params.reconstructionError, params.reconstructionErrorPerFeature,
                params.deepFeaturesHiddenLayer, params.deepFeaturesHiddenLayerName, params.reconstructTrain, params.projectArchetypes,
                params.reverseTransform, params.leafNodeAssignment, params.leafNodeAssignmentType, params.predictStagedProba,
                params.predictContributions, params.featureFrequencies, params.exemplarIndex, params.deviances, params.customMetricFunc,
                params._excludeFields);
    }

    /**
     * Create a ModelMetrics object from the predicted and actual values, and a domain for classification problems or a
     * distribution family for regression problems.
     */
    public ModelMetricsMakerSchemaV3 makeMetrics(final String predictionsFrame, final String actualsFrame) throws IOException {
        final ModelMetrics s = getService(ModelMetrics.class);
        return s.make(predictionsFrame, actualsFrame).execute().body();
    }

    public ModelMetricsMakerSchemaV3 makeMetrics(final ModelMetricsMakerSchemaV3 params) throws IOException {
        final ModelMetrics s = getService(ModelMetrics.class);
        return s.make(params.predictionsFrame, params.actualsFrame, params.domain, params.distribution).execute().body();
    }

    /**
     * Return a CPU usage snapshot of all cores of all nodes in the H2O cluster.
     */
    public WaterMeterCpuTicksV3 waterMeterCpuTicks(final int nodeidx) throws IOException {
        final WaterMeterCpuTicks s = getService(WaterMeterCpuTicks.class);
        return s.fetch(nodeidx).execute().body();
    }

    public WaterMeterCpuTicksV3 waterMeterCpuTicks(final int nodeidx, final String _excludeFields) throws IOException {
        final WaterMeterCpuTicks s = getService(WaterMeterCpuTicks.class);
        return s.fetch(nodeidx, _excludeFields).execute().body();
    }

    /**
     * Return IO usage snapshot of all nodes in the H2O cluster.
     */
    public WaterMeterIoV3 waterMeterIoForNode(final int nodeidx) throws IOException {
        final WaterMeterIo s = getService(WaterMeterIo.class);
        return s.fetch(nodeidx).execute().body();
    }

    public WaterMeterIoV3 waterMeterIoForNode(final int nodeidx, final String _excludeFields) throws IOException {
        final WaterMeterIo s = getService(WaterMeterIo.class);
        return s.fetch(nodeidx, _excludeFields).execute().body();
    }

    /**
     * Return IO usage snapshot of all nodes in the H2O cluster.
     */
    public WaterMeterIoV3 waterMeterIoForCluster() throws IOException {
        final WaterMeterIo s = getService(WaterMeterIo.class);
        return s.fetch_all().execute().body();
    }

    public WaterMeterIoV3 waterMeterIoForCluster(final int nodeidx) throws IOException {
        final WaterMeterIo s = getService(WaterMeterIo.class);
        return s.fetch_all(nodeidx, "").execute().body();
    }

    public WaterMeterIoV3 waterMeterIoForCluster(final int nodeidx, final String _excludeFields) throws IOException {
        final WaterMeterIo s = getService(WaterMeterIo.class);
        return s.fetch_all(nodeidx, _excludeFields).execute().body();
    }

    /**
     * Return true or false.
     */
    public NodePersistentStorageV3 npsContains(final String category, final String name) throws IOException {
        final NodePersistentStorage s = getService(NodePersistentStorage.class);
        return s.exists(category, name).execute().body();
    }

    public NodePersistentStorageV3 npsContains(final NodePersistentStorageV3 params) throws IOException {
        final NodePersistentStorage s = getService(NodePersistentStorage.class);
        return s.exists(params.category, params.name, params.value, params._excludeFields).execute().body();
    }

    /**
     * Return true or false.
     */
    public NodePersistentStorageV3 npsEnabled() throws IOException {
        final NodePersistentStorage s = getService(NodePersistentStorage.class);
        return s.configured().execute().body();
    }

    public NodePersistentStorageV3 npsEnabled(final NodePersistentStorageV3 params) throws IOException {
        final NodePersistentStorage s = getService(NodePersistentStorage.class);
        return s.configured(params.category, params.name, params.value, params._excludeFields).execute().body();
    }

    /**
     * Store a named value.
     */
    public NodePersistentStorageV3 npsPut(final String category, final String name) throws IOException {
        final NodePersistentStorage s = getService(NodePersistentStorage.class);
        return s.put_with_name(category, name).execute().body();
    }

    public NodePersistentStorageV3 npsPut(final NodePersistentStorageV3 params) throws IOException {
        final NodePersistentStorage s = getService(NodePersistentStorage.class);
        return s.put_with_name(params.category, params.name, params.value, params._excludeFields).execute().body();
    }

    /**
     * Return value for a given name.
     */
    public NodePersistentStorageV3 npsGet(final String category, final String name) throws IOException {
        final NodePersistentStorage s = getService(NodePersistentStorage.class);
        return s.get_as_string(category, name).execute().body();
    }

    public NodePersistentStorageV3 npsGet(final NodePersistentStorageV3 params) throws IOException {
        final NodePersistentStorage s = getService(NodePersistentStorage.class);
        return s.get_as_string(params.category, params.name, params.value, params._excludeFields).execute().body();
    }

    /**
     * Delete a key.
     */
    public NodePersistentStorageV3 npsRemove(final String category, final String name) throws IOException {
        final NodePersistentStorage s = getService(NodePersistentStorage.class);
        return s.delete(category, name).execute().body();
    }

    public NodePersistentStorageV3 npsRemove(final NodePersistentStorageV3 params) throws IOException {
        final NodePersistentStorage s = getService(NodePersistentStorage.class);
        return s.delete(params.category, params.name, params.value, params._excludeFields).execute().body();
    }

    /**
     * Store a value.
     */
    public NodePersistentStorageV3 npsCreateCategory(final String category) throws IOException {
        final NodePersistentStorage s = getService(NodePersistentStorage.class);
        return s.put(category).execute().body();
    }

    public NodePersistentStorageV3 npsCreateCategory(final NodePersistentStorageV3 params) throws IOException {
        final NodePersistentStorage s = getService(NodePersistentStorage.class);
        return s.put(params.category, params.name, params.value, params._excludeFields).execute().body();
    }

    /**
     * Return all keys stored for a given category.
     */
    public NodePersistentStorageV3 npsKeys(final String category) throws IOException {
        final NodePersistentStorage s = getService(NodePersistentStorage.class);
        return s.list(category).execute().body();
    }

    public NodePersistentStorageV3 npsKeys(final NodePersistentStorageV3 params) throws IOException {
        final NodePersistentStorage s = getService(NodePersistentStorage.class);
        return s.list(params.category, params.name, params.value, params._excludeFields).execute().body();
    }

    /**
     * Get named log file for a node.
     */
    public LogsV3 logs(final String nodeidx, final String name) throws IOException {
        final Logs s = getService(Logs.class);
        return s.fetch(nodeidx, name).execute().body();
    }

    public LogsV3 logs(final String nodeidx, final String name, final String _excludeFields) throws IOException {
        final Logs s = getService(Logs.class);
        return s.fetch(nodeidx, name, _excludeFields).execute().body();
    }

    /**
     * Kill minus 3 on *this* node
     */
    public KillMinus3V3 logThreadDump() throws IOException {
        final KillMinus3 s = getService(KillMinus3.class);
        return s.killm3().execute().body();
    }

    public KillMinus3V3 logThreadDump(final String _excludeFields) throws IOException {
        final KillMinus3 s = getService(KillMinus3.class);
        return s.killm3(_excludeFields).execute().body();
    }

    /**
     * Execute an Rapids AstRoot.
     */
    public Call<RapidsSchemaV3> rapidsExec(final String ast) {
        final Rapids s = getService(Rapids.class);
        return s.rapidsExec(ast);
    }

    public Call<RapidsSchemaV3> rapidsExec(final RapidsSchemaV3 params) {
        final Rapids s = getService(Rapids.class);
        return s.rapidsExec(params.ast, params.sessionId, params.id, params._excludeFields);
    }

    /**
     * Generate a Java POJO from the Assembly
     */
    public AssemblyV99 _assembly_toJava(final String assemblyId, final String pojoName) throws IOException {
        final Assembly s = getService(Assembly.class);
        return s.toJava(assemblyId, pojoName).execute().body();
    }

    public AssemblyV99 _assembly_toJava(final AssemblyV99 params) throws IOException {
        final Assembly s = getService(Assembly.class);
        return s.toJava(params.assemblyId, params.pojoName, params.steps, keyToString(params.frame), params._excludeFields).execute()
                .body();
    }

    /**
     * Fit an assembly to an input frame
     */
    public AssemblyV99 _assembly_fit() throws IOException {
        final Assembly s = getService(Assembly.class);
        return s.fit().execute().body();
    }

    public AssemblyV99 _assembly_fit(final AssemblyV99 params) throws IOException {
        final Assembly s = getService(Assembly.class);
        return s.fit(params.steps, keyToString(params.frame), params.pojoName, params.assemblyId, params._excludeFields).execute().body();
    }

    /**
     * Download dataset as a CSV.
     */
    public DownloadDataV3 _downloadDataset_fetch(final FrameKeyV3 frameId) throws IOException {
        final DownloadDataset s = getService(DownloadDataset.class);
        return s.fetch(keyToString(frameId)).execute().body();
    }

    public DownloadDataV3 _downloadDataset_fetch(final FrameKeyV3 frameId, final boolean hexString) throws IOException {
        final DownloadDataset s = getService(DownloadDataset.class);
        return s.fetch(keyToString(frameId), hexString, "").execute().body();
    }

    public DownloadDataV3 _downloadDataset_fetch(final FrameKeyV3 frameId, final boolean hexString, final String _excludeFields)
            throws IOException {
        final DownloadDataset s = getService(DownloadDataset.class);
        return s.fetch(keyToString(frameId), hexString, _excludeFields).execute().body();
    }

    /**
     * Download dataset as a CSV.
     */
    public DownloadDataV3 _downloadDataset_fetchStreaming(final FrameKeyV3 frameId) throws IOException {
        final DownloadDataset s = getService(DownloadDataset.class);
        return s.fetchStreaming(keyToString(frameId)).execute().body();
    }

    public DownloadDataV3 _downloadDataset_fetchStreaming(final FrameKeyV3 frameId, final boolean hexString) throws IOException {
        final DownloadDataset s = getService(DownloadDataset.class);
        return s.fetchStreaming(keyToString(frameId), hexString, "").execute().body();
    }

    public DownloadDataV3 _downloadDataset_fetchStreaming(final FrameKeyV3 frameId, final boolean hexString, final String _excludeFields)
            throws IOException {
        final DownloadDataset s = getService(DownloadDataset.class);
        return s.fetchStreaming(keyToString(frameId), hexString, _excludeFields).execute().body();
    }

    /**
     * Remove an arbitrary key from the H2O distributed K/V store.
     */
    public RemoveV3 deleteKey(final KeyV3 key) throws IOException {
        final DKV s = getService(DKV.class);
        return s.remove(keyToString(key)).execute().body();
    }

    public RemoveV3 deleteKey(final KeyV3 key, final boolean cascade) throws IOException {
        final DKV s = getService(DKV.class);
        return s.remove(keyToString(key), cascade, "").execute().body();
    }

    public RemoveV3 deleteKey(final KeyV3 key, final boolean cascade, final String _excludeFields) throws IOException {
        final DKV s = getService(DKV.class);
        return s.remove(keyToString(key), cascade, _excludeFields).execute().body();
    }

    /**
     * Remove all keys from the H2O distributed K/V store.
     */
    public RemoveAllV3 deleteAllKeys() throws IOException {
        final DKV s = getService(DKV.class);
        return s.removeAll().execute().body();
    }

    public RemoveAllV3 deleteAllKeys(final KeyV3[] retainedKeys) throws IOException {
        final DKV s = getService(DKV.class);
        return s.removeAll(keyArrayToStringArray(retainedKeys), "").execute().body();
    }

    public RemoveAllV3 deleteAllKeys(final KeyV3[] retainedKeys, final String _excludeFields) throws IOException {
        final DKV s = getService(DKV.class);
        return s.removeAll(keyArrayToStringArray(retainedKeys), _excludeFields).execute().body();
    }

    /**
     * Save a message to the H2O logfile.
     */
    public LogAndEchoV3 logAndEcho() throws IOException {
        final LogAndEcho s = getService(LogAndEcho.class);
        return s.echo().execute().body();
    }

    public LogAndEchoV3 logAndEcho(final String message) throws IOException {
        final LogAndEcho s = getService(LogAndEcho.class);
        return s.echo(message, "").execute().body();
    }

    public LogAndEchoV3 logAndEcho(final String message, final String _excludeFields) throws IOException {
        final LogAndEcho s = getService(LogAndEcho.class);
        return s.echo(message, _excludeFields).execute().body();
    }

    /**
     * Issue a new session ID.
     */
    public InitIDV3 newSession() throws IOException {
        final InitID s = getService(InitID.class);
        return s.startSession().execute().body();
    }

    public InitIDV3 newSession(final String sessionKey) throws IOException {
        final InitID s = getService(InitID.class);
        return s.startSession(sessionKey, "").execute().body();
    }

    public InitIDV3 newSession(final String sessionKey, final String _excludeFields) throws IOException {
        final InitID s = getService(InitID.class);
        return s.startSession(sessionKey, _excludeFields).execute().body();
    }

    /**
     * End a session.
     */
    public InitIDV3 endSession() throws IOException {
        final InitID s = getService(InitID.class);
        return s.endSession().execute().body();
    }

    public InitIDV3 endSession(final String sessionKey) throws IOException {
        final InitID s = getService(InitID.class);
        return s.endSession(sessionKey, "").execute().body();
    }

    public InitIDV3 endSession(final String sessionKey, final String _excludeFields) throws IOException {
        final InitID s = getService(InitID.class);
        return s.endSession(sessionKey, _excludeFields).execute().body();
    }

    /**
     * Explicitly call System.gc().
     */
    public GarbageCollectV3 garbageCollect() throws IOException {
        final GarbageCollect s = getService(GarbageCollect.class);
        return s.gc().execute().body();
    }

    /**
     * Example of an experimental endpoint.  Call via /EXPERIMENTAL/Sample.  Experimental endpoints can change at any
     * moment.
     */
    public CloudV3 _sample_status() throws IOException {
        final Sample s = getService(Sample.class);
        return s.status().execute().body();
    }

    public CloudV3 _sample_status(final boolean skipTicks) throws IOException {
        final Sample s = getService(Sample.class);
        return s.status(skipTicks, "").execute().body();
    }

    public CloudV3 _sample_status(final boolean skipTicks, final String _excludeFields) throws IOException {
        final Sample s = getService(Sample.class);
        return s.status(skipTicks, _excludeFields).execute().body();
    }

    /**
     * Produce help for Rapids AstRoot language.
     */
    public RapidsHelpV3 rapids_help() throws IOException {
        final Rapids s = getService(Rapids.class);
        return s.genHelp().execute().body();
    }

    /**
     * Get metrics for Steam from H2O.
     */
    public SteamMetricsV3 steamMetrics() throws IOException {
        final SteamMetrics s = getService(SteamMetrics.class);
        return s.fetch().execute().body();
    }

    public SteamMetricsV3 steamMetrics(final String _excludeFields) throws IOException {
        final SteamMetrics s = getService(SteamMetrics.class);
        return s.fetch(_excludeFields).execute().body();
    }

    /**
     * List of all registered capabilities
     */
    public CapabilitiesV3 list_all_capabilities() throws IOException {
        final Capabilities s = getService(Capabilities.class);
        return s.listAll().execute().body();
    }

    public CapabilitiesV3 list_all_capabilities(final String _excludeFields) throws IOException {
        final Capabilities s = getService(Capabilities.class);
        return s.listAll(_excludeFields).execute().body();
    }

    /**
     * List registered core capabilities
     */
    public CapabilitiesV3 list_core_capabilities() throws IOException {
        final Capabilities s = getService(Capabilities.class);
        return s.listCore().execute().body();
    }

    public CapabilitiesV3 list_core_capabilities(final String _excludeFields) throws IOException {
        final Capabilities s = getService(Capabilities.class);
        return s.listCore(_excludeFields).execute().body();
    }

    /**
     * List of all registered Rest API capabilities
     */
    public CapabilitiesV3 list_rest_capabilities() throws IOException {
        final Capabilities s = getService(Capabilities.class);
        return s.listRest().execute().body();
    }

    public CapabilitiesV3 list_rest_capabilities(final String _excludeFields) throws IOException {
        final Capabilities s = getService(Capabilities.class);
        return s.listRest(_excludeFields).execute().body();
    }

    /**
     * Import previously saved grid model
     */
    public GridKeyV3 import_grid(final String gridPath) throws IOException {
        final Grid s = getService(Grid.class);
        return s.importGrid(gridPath).execute().body();
    }

    /**
     * Export a Grid and its models.
     */
    public GridKeyV3 export_grid(final String gridId, final String gridDirectory) throws IOException {
        final Grid s = getService(Grid.class);
        return s.exportGrid(gridId, gridDirectory).execute().body();
    }

    /**
     * Returns the list of all REST API (v4) endpoints.
     */
    public EndpointsListV4 endpoints4() throws IOException {
        final Endpoints s = getService(Endpoints.class);
        return s.listRoutes4().execute().body();
    }

    public EndpointsListV4 endpoints4(final String __schema) throws IOException {
        final Endpoints s = getService(Endpoints.class);
        return s.listRoutes4(__schema).execute().body();
    }

    /**
     * Start a new Rapids session, and return the session id.
     */
    public SessionIdV4 newSession4() throws IOException {
        final Sessions s = getService(Sessions.class);
        return s.newSession4().execute().body();
    }

    public SessionIdV4 newSession4(final String _fields) throws IOException {
        final Sessions s = getService(Sessions.class);
        return s.newSession4(_fields).execute().body();
    }

    /**
     * Close the Rapids session.
     */
    public InitIDV3 endSession4(final String sessionKey) throws IOException {
        final Sessions s = getService(Sessions.class);
        return s.endSession(sessionKey).execute().body();
    }

    public InitIDV3 endSession4(final String sessionKey, final String _excludeFields) throws IOException {
        final Sessions s = getService(Sessions.class);
        return s.endSession(sessionKey, _excludeFields).execute().body();
    }

    /**
     * Return basic information about all models available to train.
     */
    public ModelsInfoV4 modelsInfo() throws IOException {
        final Modelsinfo s = getService(Modelsinfo.class);
        return s.modelsInfo().execute().body();
    }

    public ModelsInfoV4 modelsInfo(final String __schema) throws IOException {
        final Modelsinfo s = getService(Modelsinfo.class);
        return s.modelsInfo(__schema).execute().body();
    }

    /**
     * Create frame with random (uniformly distributed) data. You can specify how many columns of each type to make; and
     * what the desired range for each column type.
     */
    public JobV4 createSimpleFrame() throws IOException {
        final Frames s = getService(Frames.class);
        return s.createSimpleFrame().execute().body();
    }

    public JobV4 createSimpleFrame(final CreateFrameSimpleIV4 params) throws IOException {
        final Frames s = getService(Frames.class);
        return s.createSimpleFrame(keyToString(params.dest), params.seed, params.nrows, params.ncolsReal, params.ncolsInt,
                params.ncolsEnum, params.ncolsBool, params.ncolsStr, params.ncolsTime, params.realLb, params.realUb, params.intLb,
                params.intUb, params.enumNlevels, params.boolP, params.timeLb, params.timeUb, params.strLength, params.missingFraction,
                params.responseType, params.responseLb, params.responseUb, params.responseP, params.responseNlevels, params._fields)
                .execute().body();
    }

    /**
     * Retrieve information about the current state of a job.
     */
    public JobV4 getJob4(final String jobId) throws IOException {
        final Jobs s = getService(Jobs.class);
        return s.getJob4(jobId).execute().body();
    }

    public JobV4 getJob4(final String jobId, final String _fields) throws IOException {
        final Jobs s = getService(Jobs.class);
        return s.getJob4(jobId, _fields).execute().body();
    }

    //--------- PRIVATE --------------------------------------------------------------------------------------------------

    private Retrofit retrofit;
    private String url = DEFAULT_URL;
    private int connectTimeout = 15;
    private int writeTimeout = 60;
    private int readTimeout = 60;
    private int pollInterval = 1000;
    private final List<Interceptor> interceptorList = new ArrayList<>();

    private void initializeRetrofit() {
        final Gson gson = createGson();

        final Builder builder =
                new OkHttpClient.Builder().connectTimeout(connectTimeout, TimeUnit.SECONDS).writeTimeout(writeTimeout, TimeUnit.SECONDS)
                        .readTimeout(readTimeout, TimeUnit.SECONDS);
        interceptorList.stream().forEach(builder::addInterceptor);
        final OkHttpClient client = builder.build();

        this.retrofit = new Retrofit.Builder().client(client).baseUrl(url).addConverterFactory(GsonConverterFactory.create(gson)).build();
    }

    public static Gson createGson() {
        return new GsonBuilder().registerTypeAdapterFactory(new ModelV3TypeAdapter()).registerTypeAdapter(KeyV3.class, new KeySerializer())
                .registerTypeAdapter(ColSpecifierV3.class, new ColSerializer())
                .registerTypeAdapter(ModelBuilderSchema.class, new ModelDeserializer())
                .registerTypeAdapter(ModelSchemaBaseV3.class, new ModelSchemaDeserializer())
                .registerTypeAdapter(ModelOutputSchemaV3.class, new ModelOutputDeserializer())
                .registerTypeAdapter(ModelParametersSchemaV3.class, new ModelParametersDeserializer()).setLenient().create();
    }

    private Retrofit getRetrofit() {
        if (retrofit == null) {
            initializeRetrofit();
        }
        return retrofit;
    }

    public <T> T getService(final Class<T> clazz) {
        return getRetrofit().create(clazz);
    }

    /**
     * Keys get sent as Strings and returned as objects also containing the type and URL,
     * so they need a custom GSON serializer.
     */
    private static class KeySerializer implements JsonSerializer<KeyV3>, JsonDeserializer<KeyV3> {
        @Override
        public JsonElement serialize(final KeyV3 key, final Type typeOfKey, final JsonSerializationContext context) {
            return new JsonPrimitive(key.name);
        }

        @Override
        public KeyV3 deserialize(final JsonElement json, final Type typeOfT, final JsonDeserializationContext context) {
            if (json.isJsonNull()) {
                return null;
            }
            if (!json.isJsonObject()) {
                final KeyV3 key = new KeyV3();
                key.name = json.getAsString();
                key.type = "Key<?>";
                key.url = "";
                return key;
            }
            final JsonObject jobj = json.getAsJsonObject();
            final String type = jobj.get("type").getAsString();
            switch (type) {
            // TODO: dynamically generate all possible cases
            case "Key<Model>":
                return context.deserialize(jobj, ModelKeyV3.class);
            case "Key<Job>":
                return context.deserialize(jobj, JobKeyV3.class);
            case "Key<Grid>":
                return context.deserialize(jobj, GridKeyV3.class);
            case "Key<Frame>":
                return context.deserialize(jobj, FrameKeyV3.class);
            case "Key<AutoML>":
                return context.deserialize(jobj, AutoMLKeyV3.class);
            default:
                throw new JsonParseException("Unable to deserialize key of type " + type);
            }
        }
    }

    private static class ColSerializer implements JsonSerializer<ColSpecifierV3> {
        @Override
        public JsonElement serialize(final ColSpecifierV3 col, final Type typeOfCol, final JsonSerializationContext context) {
            return new JsonPrimitive(col.columnName);
        }
    }

    /**
     * Factory method for parsing a ModelBuilderSchema json object into an instance of the model-specific subclass.
     */
    private static class ModelDeserializer implements JsonDeserializer<ModelBuilderSchema> {
        @Override
        public ModelBuilderSchema deserialize(final JsonElement json, final Type typeOfT, final JsonDeserializationContext context)
                throws JsonParseException {
            if (json.isJsonNull()) {
                return null;
            }
            if (json.isJsonObject()) {
                final JsonObject jobj = json.getAsJsonObject();
                if (jobj.has("algo")) {
                    final String algo = jobj.get("algo").getAsJsonPrimitive().getAsString().toLowerCase();
                    switch (algo) {
                    case "xgboost":
                        return context.deserialize(json, XGBoostV3.class);
                    case "targetencoder":
                        return context.deserialize(json, TargetEncoderV3.class);
                    case "deeplearning":
                        return context.deserialize(json, DeepLearningV3.class);
                    case "glm":
                        return context.deserialize(json, GLMV3.class);
                    case "glrm":
                        return context.deserialize(json, GLRMV3.class);
                    case "kmeans":
                        return context.deserialize(json, KMeansV3.class);
                    case "naivebayes":
                        return context.deserialize(json, NaiveBayesV3.class);
                    case "pca":
                        return context.deserialize(json, PCAV3.class);
                    case "svd":
                        return context.deserialize(json, SVDV99.class);
                    case "drf":
                        return context.deserialize(json, DRFV3.class);
                    case "gbm":
                        return context.deserialize(json, GBMV3.class);
                    case "isolationforest":
                        return context.deserialize(json, IsolationForestV3.class);
                    case "aggregator":
                        return context.deserialize(json, AggregatorV99.class);
                    case "deepwater":
                        return context.deserialize(json, DeepWaterV3.class);
                    case "word2vec":
                        return context.deserialize(json, Word2VecV3.class);
                    case "stackedensemble":
                        return context.deserialize(json, StackedEnsembleV99.class);
                    case "coxph":
                        return context.deserialize(json, CoxPHV3.class);
                    case "generic":
                        return context.deserialize(json, GenericV3.class);
                    case "psvm":
                        return context.deserialize(json, PSVMV3.class);
                    default:
                        throw new JsonParseException("Unable to deserialize model of type " + algo);
                    }
                }
            }
            throw new JsonParseException("Invalid ModelBuilderSchema element " + json.toString());
        }
    }

    /**
     * Factory method for parsing a ModelSchemaBaseV3 json object into an instance of the model-specific subclass.
     */
    private static class ModelSchemaDeserializer implements JsonDeserializer<ModelSchemaBaseV3> {
        @Override
        public ModelSchemaBaseV3 deserialize(final JsonElement json, final Type typeOfT, final JsonDeserializationContext context)
                throws JsonParseException {
            if (json.isJsonNull()) {
                return null;
            }
            if (json.isJsonObject()) {
                final JsonObject jobj = json.getAsJsonObject();
                if (jobj.has("algo")) {
                    final String algo = jobj.get("algo").getAsJsonPrimitive().getAsString().toLowerCase();
                    switch (algo) {
                    case "xgboost":
                        return context.deserialize(json, XGBoostModelV3.class);
                    case "targetencoder":
                        return context.deserialize(json, TargetEncoderModelV3.class);
                    case "deeplearning":
                        return context.deserialize(json, DeepLearningModelV3.class);
                    case "glm":
                        return context.deserialize(json, GLMModelV3.class);
                    case "glrm":
                        return context.deserialize(json, GLRMModelV3.class);
                    case "kmeans":
                        return context.deserialize(json, KMeansModelV3.class);
                    case "naivebayes":
                        return context.deserialize(json, NaiveBayesModelV3.class);
                    case "pca":
                        return context.deserialize(json, PCAModelV3.class);
                    case "svd":
                        return context.deserialize(json, SVDModelV99.class);
                    case "drf":
                        return context.deserialize(json, DRFModelV3.class);
                    case "gbm":
                        return context.deserialize(json, GBMModelV3.class);
                    case "isolationforest":
                        return context.deserialize(json, IsolationForestModelV3.class);
                    case "aggregator":
                        return context.deserialize(json, AggregatorModelV99.class);
                    case "deepwater":
                        return context.deserialize(json, DeepWaterModelV3.class);
                    case "word2vec":
                        return context.deserialize(json, Word2VecModelV3.class);
                    case "stackedensemble":
                        return context.deserialize(json, StackedEnsembleModelV99.class);
                    case "coxph":
                        return context.deserialize(json, CoxPHModelV3.class);
                    case "generic":
                        return context.deserialize(json, GenericModelV3.class);
                    case "psvm":
                        return context.deserialize(json, PSVMModelV3.class);
                    default:
                        throw new JsonParseException("Unable to deserialize model of type " + algo);
                    }
                }
            }
            throw new JsonParseException("Invalid ModelSchemaBaseV3 element " + json.toString());
        }
    }

    /**
     * Factory method for parsing a ModelOutputSchemaV3 json object into an instance of the model-specific subclass.
     */
    private static class ModelOutputDeserializer implements JsonDeserializer<ModelOutputSchemaV3> {
        @Override
        public ModelOutputSchemaV3 deserialize(final JsonElement json, final Type typeOfT, final JsonDeserializationContext context)
                throws JsonParseException {
            if (json.isJsonNull()) {
                return null;
            }
            if (json.isJsonObject()) {
                final JsonObject jobj = json.getAsJsonObject();
                if (jobj.has("algo")) {
                    final String algo = jobj.get("algo").getAsJsonPrimitive().getAsString().toLowerCase();
                    switch (algo) {
                    case "xgboost":
                        return context.deserialize(json, XGBoostModelOutputV3.class);
                    case "targetencoder":
                        return context.deserialize(json, TargetEncoderModelOutputV3.class);
                    case "deeplearning":
                        return context.deserialize(json, DeepLearningModelOutputV3.class);
                    case "glm":
                        return context.deserialize(json, GLMModelOutputV3.class);
                    case "glrm":
                        return context.deserialize(json, GLRMModelOutputV3.class);
                    case "kmeans":
                        return context.deserialize(json, KMeansModelOutputV3.class);
                    case "naivebayes":
                        return context.deserialize(json, NaiveBayesModelOutputV3.class);
                    case "pca":
                        return context.deserialize(json, PCAModelOutputV3.class);
                    case "svd":
                        return context.deserialize(json, SVDModelOutputV99.class);
                    case "drf":
                        return context.deserialize(json, DRFModelOutputV3.class);
                    case "gbm":
                        return context.deserialize(json, GBMModelOutputV3.class);
                    case "isolationforest":
                        return context.deserialize(json, IsolationForestModelOutputV3.class);
                    case "aggregator":
                        return context.deserialize(json, AggregatorModelOutputV99.class);
                    case "deepwater":
                        return context.deserialize(json, DeepWaterModelOutputV3.class);
                    case "word2vec":
                        return context.deserialize(json, Word2VecModelOutputV3.class);
                    case "stackedensemble":
                        return context.deserialize(json, StackedEnsembleModelOutputV99.class);
                    case "coxph":
                        return context.deserialize(json, CoxPHModelOutputV3.class);
                    case "generic":
                        return context.deserialize(json, GenericModelOutputV3.class);
                    case "psvm":
                        return context.deserialize(json, PSVMModelOutputV3.class);
                    default:
                        throw new JsonParseException("Unable to deserialize model of type " + algo);
                    }
                }
            }
            throw new JsonParseException("Invalid ModelOutputSchemaV3 element " + json.toString());
        }
    }

    /**
     * Factory method for parsing a ModelParametersSchemaV3 json object into an instance of the model-specific subclass.
     */
    private static class ModelParametersDeserializer implements JsonDeserializer<ModelParametersSchemaV3> {
        @Override
        public ModelParametersSchemaV3 deserialize(final JsonElement json, final Type typeOfT, final JsonDeserializationContext context)
                throws JsonParseException {
            if (json.isJsonNull()) {
                return null;
            }
            if (json.isJsonObject()) {
                final JsonObject jobj = json.getAsJsonObject();
                if (jobj.has("algo")) {
                    final String algo = jobj.get("algo").getAsJsonPrimitive().getAsString().toLowerCase();
                    switch (algo) {
                    case "xgboost":
                        return context.deserialize(json, XGBoostParametersV3.class);
                    case "targetencoder":
                        return context.deserialize(json, TargetEncoderParametersV3.class);
                    case "deeplearning":
                        return context.deserialize(json, DeepLearningParametersV3.class);
                    case "glm":
                        return context.deserialize(json, GLMParametersV3.class);
                    case "glrm":
                        return context.deserialize(json, GLRMParametersV3.class);
                    case "kmeans":
                        return context.deserialize(json, KMeansParametersV3.class);
                    case "naivebayes":
                        return context.deserialize(json, NaiveBayesParametersV3.class);
                    case "pca":
                        return context.deserialize(json, PCAParametersV3.class);
                    case "svd":
                        return context.deserialize(json, SVDParametersV99.class);
                    case "drf":
                        return context.deserialize(json, DRFParametersV3.class);
                    case "gbm":
                        return context.deserialize(json, GBMParametersV3.class);
                    case "isolationforest":
                        return context.deserialize(json, IsolationForestParametersV3.class);
                    case "aggregator":
                        return context.deserialize(json, AggregatorParametersV99.class);
                    case "deepwater":
                        return context.deserialize(json, DeepWaterParametersV3.class);
                    case "word2vec":
                        return context.deserialize(json, Word2VecParametersV3.class);
                    case "stackedensemble":
                        return context.deserialize(json, StackedEnsembleParametersV99.class);
                    case "coxph":
                        return context.deserialize(json, CoxPHParametersV3.class);
                    case "generic":
                        return context.deserialize(json, GenericParametersV3.class);
                    case "psvm":
                        return context.deserialize(json, PSVMParametersV3.class);
                    default:
                        throw new JsonParseException("Unable to deserialize model of type " + algo);
                    }
                }
            }
            throw new JsonParseException("Invalid ModelParametersSchemaV3 element " + json.toString());
        }
    }

    private static class ModelV3TypeAdapter implements TypeAdapterFactory {
        @Override
        public <T> TypeAdapter<T> create(final Gson gson, final TypeToken<T> type) {
            final Class<? super T> rawType = type.getRawType();
            if (!ModelBuilderSchema.class.isAssignableFrom(rawType) && !ModelSchemaBaseV3.class.isAssignableFrom(rawType)) {
                return null;
            }
            final TypeAdapter<T> delegate = gson.getDelegateAdapter(this, type);
            return new TypeAdapter<>() {
                @Override
                public void write(final JsonWriter out, final T value) throws IOException {
                    delegate.write(out, value);
                }

                @Override
                public T read(final JsonReader in) throws IOException {
                    final JsonObject jobj = new JsonParser().parse(in).getAsJsonObject();
                    if (jobj.has("parameters") && jobj.get("parameters").isJsonArray()) {
                        final JsonArray jarr = jobj.get("parameters").getAsJsonArray();
                        final JsonObject paramsNew = new JsonObject();
                        for (final JsonElement item : jarr) {
                            final JsonObject itemObj = item.getAsJsonObject();
                            paramsNew.add(itemObj.get("name").getAsString(), itemObj.get("actual_value"));
                        }
                        jobj.add("parameters", paramsNew);
                    }
                    // noinspection unchecked
                    return (T) new Gson().fromJson(jobj, rawType);
                }
            };
        }
    }

    /**
     * Return an array of Strings for an array of keys.
     */
    public static String[] keyArrayToStringArray(final KeyV3[] keys) {
        if (keys == null) {
            return null;
        }
        final String[] ids = new String[keys.length];
        int i = 0;
        for (final KeyV3 key : keys) {
            ids[i++] = key.name;
        }
        return ids;
    }

    /**
     * Return an array of keys from an array of Strings.
     * @param ids array of string ids to convert to KeyV3's
     * @param clz class of key objects to create. Since we have JobKeyV3, FrameKeyV3, ModelKeyV3, etc -- this
     *            method needs to know which of these keys you want to create
     */
    public static <T extends KeyV3> T[] stringArrayToKeyArray(final String[] ids, final Class<T> clz) {
        if (ids == null) {
            return null;
        }
        // noinspection unchecked
        final T[] keys = (T[]) Array.newInstance(clz, ids.length);
        String keyType = clz.getSimpleName();
        if (keyType.endsWith("KeyV3")) {
            keyType = keyType.substring(0, keyType.length() - 5);
        }
        try {
            int i = 0;
            for (final String id : ids) {
                keys[i] = clz.getConstructor().newInstance();
                keys[i].name = id;
                keys[i].type = keyType;
                i++;
            }
        } catch (final Exception e) {
            e.printStackTrace();
        }
        return keys;
    }

    /**
     *
     */
    public static String keyToString(final KeyV3 key) {
        return key == null ? null : key.name;
    }

    /**
     *
     */
    public static FrameKeyV3 stringToFrameKey(final String key) {
        if (key == null) {
            return null;
        }
        final FrameKeyV3 k = new FrameKeyV3();
        k.name = key;
        return k;
    }

    /**
     *
     */
    private static String colToString(final ColSpecifierV3 col) {
        return col == null ? null : col.columnName;
    }

    /**
     *
     */
    public static String stringToCol(final String col) {
        if (col == null) {
            return null;
        }
        final ColSpecifierV3 c = new ColSpecifierV3();
        c.columnName = col;
        return col;
    }

    public static void copyFields(final Object to, final Object from) {
        final Field[] fromFields = from.getClass().getDeclaredFields();
        to.getClass().getDeclaredFields();

        for (final Field fromField : fromFields) {
            Field toField;
            try {
                toField = to.getClass().getDeclaredField(fromField.getName());
                fromField.setAccessible(true);
                toField.setAccessible(true);
                toField.set(to, fromField.get(from));
            } catch (final Exception ignored) {
                // NoSuchField is the normal case
            }
        }
    }
}
