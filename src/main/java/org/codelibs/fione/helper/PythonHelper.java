/*
 * Copyright 2012-2023 CodeLibs Project and the Others.
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

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.io.InputStream;
import java.io.Writer;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.function.Consumer;
import java.util.stream.Collectors;

import javax.annotation.PostConstruct;

import org.apache.commons.text.StringEscapeUtils;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.codelibs.core.io.CopyUtil;
import org.codelibs.core.io.FileUtil;
import org.codelibs.core.lang.StringUtil;
import org.codelibs.fess.crawler.Constants;
import org.codelibs.fess.exception.JobProcessingException;
import org.codelibs.fess.util.ComponentUtil;
import org.codelibs.fess.util.ResourceUtil;
import org.codelibs.fione.exception.PythonExecutionException;
import org.opensearch.common.xcontent.LoggingDeprecationHandler;
import org.opensearch.common.xcontent.NamedXContentRegistry;
import org.opensearch.common.xcontent.json.JsonXContent;

import com.google.common.collect.Lists;

public class PythonHelper {
    private static final Logger logger = LogManager.getLogger(PythonHelper.class);

    private PythonModule[] frameModules;

    private PythonModule[] trainModules;

    private PythonModule[] predictModules;

    @PostConstruct
    public void init() {
        try {
            Class.forName("javax.servlet.ServletContext");
        } catch (final ClassNotFoundException e) {
            return;
        }
        reload();
    }

    public void reload() {
        final List<PythonModule> frameModuleList = new ArrayList<>();
        final List<PythonModule> trainModuleList = new ArrayList<>();
        final List<PythonModule> predictModuleList = new ArrayList<>();
        for (final File pyFile : ResourceUtil.getEnvPath("fione", "python").toFile().listFiles((dir, name) -> name.endsWith(".py"))) {
            try {
                final var jsonString = executePython(pyFile, null, null);
                if (logger.isDebugEnabled()) {
                    logger.debug("Python Module: {} => {}", pyFile.getAbsolutePath(), jsonString);
                }

                final var pythonModule = new PythonModule(pyFile, jsonString);
                logger.info("Load Module: {}", pythonModule.getId());
                switch (pythonModule.getType()) {
                case FRAME:
                    frameModuleList.add(pythonModule);
                    break;
                case TRAIN:
                    trainModuleList.add(pythonModule);
                    break;
                case PREDICT:
                    predictModuleList.add(pythonModule);
                    break;
                case LIBRARY:
                    // no op
                    break;
                default:
                    logger.warn("Unknown module: {} => {}", pyFile.getAbsolutePath(), jsonString);
                    break;
                }
            } catch (final Exception e) {
                logger.warn("Failed to load {}", pyFile.getAbsolutePath(), e);
            }

        }

        frameModuleList.sort((x, y) -> x.getPriority() - y.getPriority());
        trainModuleList.sort((x, y) -> x.getPriority() - y.getPriority());
        predictModuleList.sort((x, y) -> x.getPriority() - y.getPriority());
        frameModules = frameModuleList.toArray(n -> new PythonModule[n]);
        trainModules = trainModuleList.toArray(n -> new PythonModule[n]);
        predictModules = predictModuleList.toArray(n -> new PythonModule[n]);
    }

    public void execute(final String id, final Map<String, Object> params, final Consumer<String> progress) {
        final var module = findPythonModule(id);
        if (module == null) {
            throw new PythonExecutionException(id + " is not found.");
        }
        final var iniFile = ComponentUtil.getSystemHelper().createTempFile("fione_", ".ini");
        try {
            writeIniFile(iniFile, params);
            progress.accept("FIONE:{\"type\":\"ini_file\",\"content\":\""
                    + StringEscapeUtils.escapeJson(FileUtil.readText(iniFile, Constants.UTF_8)) + "\",\"progress\":0.2}");
            executePython(module.getPyFile(), iniFile, progress);
        } finally {
            if (iniFile != null && !iniFile.delete()) {
                logger.warn("Failed to delete {}.", iniFile.getAbsolutePath());
            }
        }
    }

    public PythonModule findPythonModule(final String id) {
        for (final PythonModule module : frameModules) {
            if (module.getId().equals(id)) {
                return module;
            }
        }
        for (final PythonModule module : trainModules) {
            if (module.getId().equals(id)) {
                return module;
            }
        }
        for (final PythonModule module : predictModules) {
            if (module.getId().equals(id)) {
                return module;
            }
        }
        return null;
    }

    protected String executePython(final File pyFile, final File iniFile, final Consumer<String> progress) {
        final var fessConfig = ComponentUtil.getFessConfig();
        final var processHelper = ComponentUtil.getProcessHelper();
        final var baseDir = ResourceUtil.getEnvPath("fione", "python").toFile();
        final var pythonCommand = fessConfig.getSystemProperty("fione.python.path", "python3");
        final List<String> cmdList = Lists.newArrayList(pythonCommand, pyFile.getAbsolutePath());
        if (iniFile != null) {
            cmdList.add(iniFile.getAbsolutePath());
        }

        if (logger.isDebugEnabled()) {
            logger.debug("Execute Python: {}", cmdList);
        }

        final var sessionId = UUID.randomUUID().toString().replace("-", StringUtil.EMPTY);
        try {
            final var jobProcess = processHelper.startProcess(sessionId, cmdList, pb -> {
                pb.directory(baseDir);
                pb.redirectErrorStream(true);
            }, 10000, progress);

            final var it = jobProcess.getInputStreamThread();
            it.start();

            final var currentProcess = jobProcess.getProcess();
            currentProcess.waitFor();
            it.join(5000);

            final var exitValue = currentProcess.exitValue();

            if (logger.isInfoEnabled()) {
                logger.info("Python: Exit Code={} - Process Output:\n{}", exitValue, it.getOutput());
            }
            if (exitValue != 0) {
                final var out = new StringBuilder();
                out.append("Exit Code: ").append(exitValue).append("\nOutput:\n").append(it.getOutput());
                throw new PythonExecutionException(out.toString());
            }
            return it.getOutput();
        } catch (final PythonExecutionException e) {
            throw e;
        } catch (final JobProcessingException e) {
            throw new PythonExecutionException(e);
        } catch (final Exception e) {
            throw new PythonExecutionException("Crawler Process terminated.", e);
        } finally {
            processHelper.destroyProcess(sessionId);
        }
    }

    protected void writeIniFile(final File iniFile, final Map<String, Object> params) {
        final var endpoint = ((CustomSystemHelper) ComponentUtil.getSystemHelper()).getH2oEndpoint();
        try (final Writer writer = new BufferedWriter(new FileWriter(iniFile, Constants.UTF_8_CHARSET))) {
            writer.write("[h2o]\n");
            writer.write("url = " + endpoint + "\n");
            writer.write("[parameters]\n");
            for (final Map.Entry<String, Object> e : params.entrySet()) {
                var value = e.getValue();
                if (value instanceof final String[] values) {
                    value = "[" + Arrays.stream(values).map(s -> "\"" + s + "\"").collect(Collectors.joining(",")) + "]";
                }
                writer.write(e.getKey() + " = " + value + "\n");
            }
            writer.flush();
        } catch (final IOException e) {
            throw new PythonExecutionException("Failed to write " + iniFile.getAbsolutePath(), e);
        }

        if (logger.isDebugEnabled()) {
            logger.debug("INI File:\n{}", FileUtil.readText(iniFile));
        }
    }

    public void addModule(final String fileName, final InputStream in) {
        final var name = fileName.endsWith(".py") ? fileName : fileName + ".py";
        CopyUtil.copy(in, ResourceUtil.getEnvPath("fione", "python", name).toFile());
        reload();
    }

    public PythonModule[] getFrameModules() {
        return frameModules;
    }

    public PythonModule[] getTrainModules() {
        return trainModules;
    }

    public PythonModule[] getPredictModules() {
        return predictModules;
    }

    public static class PythonModule {

        private final String id;

        private final String name;

        private final String description;

        private final ModuleType type;

        private final List<Map<String, Object>> components;

        private final int priority;

        private final File pyFile;

        @SuppressWarnings("unchecked")
        public PythonModule(final File pyFile, final String jsonString) throws IOException {
            this.pyFile = pyFile;
            final var params = JsonXContent.jsonXContent
                    .createParser(NamedXContentRegistry.EMPTY, LoggingDeprecationHandler.INSTANCE, jsonString).map();
            id = (String) params.get("id");
            name = (String) params.get("name");
            description = (String) params.get("description");
            type = Arrays.stream(ModuleType.values())
                    .filter(s -> s.name().equalsIgnoreCase((String) params.getOrDefault("type", "unknown"))).findFirst()
                    .orElse(ModuleType.UNKNOWN);
            priority = Integer.parseInt((String) params.getOrDefault("priority", "999"));
            components = (List<Map<String, Object>>) params.get("components");
        }

        public String getId() {
            return id;
        }

        public String getName() {
            return name;
        }

        public String getDescription() {
            return description;
        }

        public ModuleType getType() {
            return type;
        }

        public List<Map<String, Object>> getComponents() {
            return components;
        }

        public int getPriority() {
            return priority;
        }

        public File getPyFile() {
            return pyFile;
        }

        public void execute(final Map<String, Object> params, final Consumer<String> progress) {
            final var pythonHelper = ComponentUtil.getComponent(PythonHelper.class);
            pythonHelper.execute(id, params, progress);
        }

    }

    public enum ModuleType {
        FRAME, TRAIN, PREDICT, LIBRARY, UNKNOWN;
    }

}
