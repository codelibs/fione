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
import javax.servlet.ServletContext;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.codelibs.core.io.CopyUtil;
import org.codelibs.core.io.FileUtil;
import org.codelibs.core.lang.StringUtil;
import org.codelibs.fess.crawler.Constants;
import org.codelibs.fess.exception.JobProcessingException;
import org.codelibs.fess.helper.ProcessHelper;
import org.codelibs.fess.mylasta.direction.FessConfig;
import org.codelibs.fess.util.ComponentUtil;
import org.codelibs.fess.util.InputStreamThread;
import org.codelibs.fess.util.JobProcess;
import org.codelibs.fess.util.ResourceUtil;
import org.codelibs.fione.exception.PythonExecutionException;
import org.elasticsearch.common.xcontent.LoggingDeprecationHandler;
import org.elasticsearch.common.xcontent.NamedXContentRegistry;
import org.elasticsearch.common.xcontent.json.JsonXContent;

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
                final String jsonString = executePython(pyFile, null, null);
                if (logger.isDebugEnabled()) {
                    logger.debug("Python Module: {} => {}", pyFile.getAbsolutePath(), jsonString);
                }

                final PythonModule pythonModule = new PythonModule(pyFile, jsonString);
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
        final PythonModule module = findPythonModule(id);
        if (module == null) {
            throw new PythonExecutionException(id + " is not found.");
        }
        final File iniFile = ComponentUtil.getSystemHelper().createTempFile("fione_", ".ini");
        try {
            writeIniFile(iniFile, params);
            progress.accept("progress:0.2:");
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
        final FessConfig fessConfig = ComponentUtil.getFessConfig();
        final ProcessHelper processHelper = ComponentUtil.getProcessHelper();
        final ServletContext servletContext = ComponentUtil.getComponent(ServletContext.class);
        final File baseDir = new File(servletContext.getRealPath("/WEB-INF")).getParentFile();
        final String pythonCommand = fessConfig.getSystemProperty("fione.python.path", "python3");
        final List<String> cmdList = Lists.newArrayList(pythonCommand, pyFile.getAbsolutePath());
        if (iniFile != null) {
            cmdList.add(iniFile.getAbsolutePath());
        }

        if (logger.isDebugEnabled()) {
            logger.debug("Execute Python: {}", cmdList);
        }

        final String sessionId = UUID.randomUUID().toString().replace("-", StringUtil.EMPTY);
        try {
            final JobProcess jobProcess = processHelper.startProcess(sessionId, cmdList, pb -> {
                pb.directory(baseDir);
                pb.redirectErrorStream(true);
            }, 10000, progress);

            final InputStreamThread it = jobProcess.getInputStreamThread();
            it.start();

            final Process currentProcess = jobProcess.getProcess();
            currentProcess.waitFor();
            it.join(5000);

            final int exitValue = currentProcess.exitValue();

            if (logger.isInfoEnabled()) {
                logger.info("Python: Exit Code={} - Process Output:\n{}", exitValue, it.getOutput());
            }
            if (exitValue != 0) {
                final StringBuilder out = new StringBuilder();
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
        final String endpoint = ((CustomSystemHelper) ComponentUtil.getSystemHelper()).getH2oEndpoint();
        try (final Writer writer = new BufferedWriter(new FileWriter(iniFile, Constants.UTF_8_CHARSET))) {
            writer.write("[h2o]\n");
            writer.write("url = " + endpoint + "\n");
            writer.write("[parameters]\n");
            for (final Map.Entry<String, Object> e : params.entrySet()) {
                Object value = e.getValue();
                if (value instanceof String[]) {
                    final String[] values = (String[]) value;
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
        final String name = fileName.endsWith(".py") ? fileName : fileName + ".py";
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
            final Map<String, Object> params =
                    JsonXContent.jsonXContent.createParser(NamedXContentRegistry.EMPTY, LoggingDeprecationHandler.INSTANCE, jsonString)
                            .map();
            id = (String) params.get("id");
            name = (String) params.get("name");
            description = (String) params.get("description");
            type =
                    Arrays.stream(ModuleType.values())
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
            final PythonHelper pythonHelper = ComponentUtil.getComponent(PythonHelper.class);
            pythonHelper.execute(id, params, progress);
        }

    }

    public enum ModuleType {
        FRAME, TRAIN, PREDICT, UNKNOWN;
    }

}
