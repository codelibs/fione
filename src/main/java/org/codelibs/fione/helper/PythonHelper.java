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
import java.io.Writer;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.function.Consumer;

import javax.annotation.PostConstruct;
import javax.servlet.ServletContext;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
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

import com.github.jknack.handlebars.Context;
import com.github.jknack.handlebars.Handlebars;
import com.github.jknack.handlebars.Template;
import com.github.jknack.handlebars.io.FileTemplateLoader;
import com.google.common.collect.Lists;

public class PythonHelper {
    private static final Logger logger = LogManager.getLogger(PythonHelper.class);

    protected Handlebars handlebars;

    @PostConstruct
    public void init() {
        final FileTemplateLoader loader = new FileTemplateLoader(ResourceUtil.getPluginPath("fione", "python").toFile());
        handlebars = new Handlebars(loader);
    }

    public void execute(String name, Map<String, Object> params, Consumer<Float> progress) {
        final File pyFile = ComponentUtil.getSystemHelper().createTempFile("fione_", ".py");
        try {
            writePythonFile(name, params, pyFile);
            progress.accept(0.25f);
            executePython(pyFile, progress);
        } finally {
            if (pyFile != null && !pyFile.delete()) {
                logger.warn("Failed to delete {}.", pyFile.getAbsolutePath());
            }
        }
    }

    protected void executePython(final File pyFile, Consumer<Float> progress) {
        final FessConfig fessConfig = ComponentUtil.getFessConfig();
        final ProcessHelper processHelper = ComponentUtil.getProcessHelper();
        final ServletContext servletContext = ComponentUtil.getComponent(ServletContext.class);
        final File baseDir = new File(servletContext.getRealPath("/WEB-INF")).getParentFile();
        final String pythonCommand = fessConfig.getSystemProperty("fione.python.path", "python3");
        final List<String> cmdList = Lists.newArrayList(pythonCommand, pyFile.getAbsolutePath());

        final String sessionId = UUID.randomUUID().toString().replace("-", StringUtil.EMPTY);
        try {
            final JobProcess jobProcess = processHelper.startProcess(sessionId, cmdList, pb -> {
                pb.directory(baseDir);
                pb.redirectErrorStream(true);
            });

            final InputStreamThread it = jobProcess.getInputStreamThread();
            it.start();

            final Process currentProcess = jobProcess.getProcess();
            currentProcess.waitFor();
            it.join(5000);

            final int exitValue = currentProcess.exitValue();

            if (logger.isInfoEnabled()) {
                logger.info("Crawler: Exit Code={} - Process Output:\n{}", exitValue, it.getOutput());
            }
            if (exitValue != 0) {
                final StringBuilder out = new StringBuilder();
                out.append("Exit Code: ").append(exitValue).append("\nOutput:\n").append(it.getOutput());
                throw new PythonExecutionException(out.toString());
            }
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

    protected void writePythonFile(String name, Map<String, Object> params, final File pyFile) {
        Map<String, Object> h2oParams = new HashMap<>();
        String endpoint = ((CustomSystemHelper) ComponentUtil.getSystemHelper()).getH2oEndpoint();
        h2oParams.put("url", endpoint);
        params.put("h2o", h2oParams);
        try (final Writer writer = new BufferedWriter(new FileWriter(pyFile, Constants.UTF_8_CHARSET))) {
            final Template template = handlebars.compile(name);
            final Context hbsContext = Context.newContext(params);
            template.apply(hbsContext, writer);
            writer.flush();
        } catch (IOException e) {
            throw new PythonExecutionException("Failed to write " + pyFile.getAbsolutePath(), e);
        }
    }
}
