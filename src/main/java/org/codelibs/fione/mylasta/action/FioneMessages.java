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
package org.codelibs.fione.mylasta.action;

import org.lastaflute.core.message.UserMessage;

/**
 * The keys for message.
 * @author FreeGen
 */
public class FioneMessages extends FioneLabels {

    /** The serial version UID for object serialization. (Default) */
    private static final long serialVersionUID = 1L;

    /** The key of the message: Created Project {0}. */
    public static final String SUCCESS_created_project = "{success.created_project}";

    /** The key of the message: Uploaded DataSet {0}. */
    public static final String SUCCESS_uploaded_dataset = "{success.uploaded_dataset}";

    /** The key of the message: Deleting DataSet {0}. */
    public static final String SUCCESS_deleting_dataset = "{success.deleting_dataset}";

    /** The key of the message: Creating Frame from DataSet {0}. */
    public static final String SUCCESS_creating_frame = "{success.creating_frame}";

    /** The key of the message: Deleted Frame {0}. */
    public static final String SUCCESS_deleted_frame = "{success.deleted_frame}";

    /** The key of the message: Deleted Job {0}. */
    public static final String SUCCESS_deleted_job = "{success.deleted_job}";

    /** The key of the message: Stopped Job {0}. */
    public static final String SUCCESS_stopped_job = "{success.stopped_job}";

    /** The key of the message: Loaded DataSet {0}. */
    public static final String SUCCESS_load_dataset = "{success.load_dataset}";

    /** The key of the message: Building models is started. */
    public static final String SUCCESS_building_models = "{success.building_models}";

    /** The key of the message: Exporting Frame {0} to {1}. */
    public static final String SUCCESS_exporting_frame = "{success.exporting_frame}";

    /** The key of the message: Deleted all jobs. */
    public static final String SUCCESS_deleted_all_jobs = "{success.deleted_all_jobs}";

    /** The key of the message: Renew a session. */
    public static final String SUCCESS_renew_session = "{success.renew_session}";

    /** The key of the message: Deleted Project {0}. */
    public static final String SUCCESS_deleted_project = "{success.deleted_project}";

    /** The key of the message: Deleted Model {0}. */
    public static final String SUCCESS_deleted_model = "{success.deleted_model}";

    /** The key of the message: Exporting Model {0}. */
    public static final String SUCCESS_exporting_model = "{success.exporting_model}";

    /** The key of the message: Exporting all Models. */
    public static final String SUCCESS_exporting_all_models = "{success.exporting_all_models}";

    /** The key of the message: Update DataSet {0}. */
    public static final String SUCCESS_update_dataset = "{success.update_dataset}";

    /** The key of the message: Stopping H2O cluster. */
    public static final String SUCCESS_shutdown_h2o = "{success.shutdown_h2o}";

    /** The key of the message: Running Module {0}. */
    public static final String SUCCESS_run_module = "{success.run_module}";

    /** The key of the message: Reloading Modules. */
    public static final String SUCCESS_reload_modules = "{success.reload_modules}";

    /** The key of the message: Uploaded Module {0}. */
    public static final String SUCCESS_uploaded_module = "{success.uploaded_module}";

    /** The key of the message: Deleted Model Set {0}. */
    public static final String SUCCESS_deleted_leaderboard = "{success.deleted_leaderboard}";

    /** The key of the message: Importing Model {0}. */
    public static final String SUCCESS_importing_model = "{success.importing_model}";

    /** The key of the message: Project {0} is not found. */
    public static final String ERRORS_project_is_not_found = "{errors.project_is_not_found}";

    /** The key of the message: Failed to create Project {0}. */
    public static final String ERRORS_failed_to_create_project = "{errors.failed_to_create_project}";

    /** The key of the message: Failed to load Project {0}. */
    public static final String ERRORS_failed_to_load_project = "{errors.failed_to_load_project}";

    /** The key of the message: Failed to upload DataSet {0}. */
    public static final String ERRORS_failed_to_upload_dataset = "{errors.failed_to_upload_dataset}";

    /** The key of the message: Failed to delete DataSet {0}. */
    public static final String ERRORS_failed_to_delete_dataset = "{errors.failed_to_delete_dataset}";

    /** The key of the message: DataSet {0} is not found. */
    public static final String ERRORS_dataset_is_not_found = "{errors.dataset_is_not_found}";

    /** The key of the message: Failed to create Frame from DataSet {0}. */
    public static final String ERRORS_failed_to_create_frame = "{errors.failed_to_create_frame}";

    /** The key of the message: Failed to delete Frame {0}. */
    public static final String ERRORS_failed_to_delete_frame = "{errors.failed_to_delete_frame}";

    /** The key of the message: Failed to delete Job {0}. */
    public static final String ERRORS_failed_to_delete_job = "{errors.failed_to_delete_job}";

    /** The key of the message: Failed to load DataSet {0}. */
    public static final String ERRORS_failed_to_load_dataset = "{errors.failed_to_load_dataset}";

    /** The key of the message: Failed to start a build process. */
    public static final String ERRORS_failed_to_start_build = "{errors.failed_to_start_build}";

    /** The key of the message: Failed to export Frame {0}. */
    public static final String ERRORS_failed_to_export_frame = "{errors.failed_to_export_frame}";

    /** The key of the message: Schema of DataSet {0} is not found. */
    public static final String ERRORS_dataset_schema_is_not_found = "{errors.dataset_schema_is_not_found}";

    /** The key of the message: Model information is not found. */
    public static final String ERRORS_leaderboard_is_not_found = "{errors.leaderboard_is_not_found}";

    /** The key of the message: Failed to delete jobs. */
    public static final String ERRORS_failed_to_delete_jobs = "{errors.failed_to_delete_jobs}";

    /** The key of the message: Failed to renew the current session. */
    public static final String ERRORS_failed_to_renew_session = "{errors.failed_to_renew_session}";

    /** The key of the message: Failed to delete Project {0}. */
    public static final String ERRORS_failed_to_delete_project = "{errors.failed_to_delete_project}";

    /** The key of the message: Failed to delete Model {0}. */
    public static final String ERRORS_failed_to_delete_model = "{errors.failed_to_delete_model}";

    /** The key of the message: Failed to export Model {0}. */
    public static final String ERRORS_failed_to_export_model = "{errors.failed_to_export_model}";

    /** The key of the message: Failed to export Models. */
    public static final String ERRORS_failed_to_export_models = "{errors.failed_to_export_models}";

    /** The key of the message: Project {0} exists. */
    public static final String ERRORS_project_exists = "{errors.project_exists}";

    /** The key of the message: Failed to update DataSet {0}. */
    public static final String ERRORS_failed_to_update_dataset = "{errors.failed_to_update_dataset}";

    /** The key of the message: Failed to stop H2O cluster. */
    public static final String ERRORS_failed_to_shutdown_h2o = "{errors.failed_to_shutdown_h2o}";

    /** The key of the message: Failed to run Module {0}. */
    public static final String ERRORS_failed_to_run_module = "{errors.failed_to_run_module}";

    /** The key of the message: Failed to reload modules. */
    public static final String ERRORS_failed_to_reload_modules = "{errors.failed_to_reload_modules}";

    /** The key of the message: Failed to upload Module {0}. */
    public static final String ERRORS_failed_to_upload_module = "{errors.failed_to_upload_module}";

    /** The key of the message: Failed to delete Model Set {0}. */
    public static final String ERRORS_failed_to_delete_leaderboard = "{errors.failed_to_delete_leaderboard}";

    /** The key of the message: Failed to import Model {0}. */
    public static final String ERRORS_failed_to_import_model = "{errors.failed_to_import_model}";

    /** The key of the message: Module is not found. */
    public static final String ERRORS_module_is_not_found = "{errors.module_is_not_found}";

    /**
     * Add the created action message for the key 'success.created_project' with parameters.
     * <pre>
     * message: Created Project {0}.
     * </pre>
     * @param property The property name for the message. (NotNull)
     * @param arg0 The parameter arg0 for message. (NotNull)
     * @return this. (NotNull)
     */
    public FioneMessages addSuccessCreatedProject(final String property, final String arg0) {
        assertPropertyNotNull(property);
        add(property, new UserMessage(SUCCESS_created_project, arg0));
        return this;
    }

    /**
     * Add the created action message for the key 'success.uploaded_dataset' with parameters.
     * <pre>
     * message: Uploaded DataSet {0}.
     * </pre>
     * @param property The property name for the message. (NotNull)
     * @param arg0 The parameter arg0 for message. (NotNull)
     * @return this. (NotNull)
     */
    public FioneMessages addSuccessUploadedDataset(final String property, final String arg0) {
        assertPropertyNotNull(property);
        add(property, new UserMessage(SUCCESS_uploaded_dataset, arg0));
        return this;
    }

    /**
     * Add the created action message for the key 'success.deleting_dataset' with parameters.
     * <pre>
     * message: Deleting DataSet {0}.
     * </pre>
     * @param property The property name for the message. (NotNull)
     * @param arg0 The parameter arg0 for message. (NotNull)
     * @return this. (NotNull)
     */
    public FioneMessages addSuccessDeletingDataset(final String property, final String arg0) {
        assertPropertyNotNull(property);
        add(property, new UserMessage(SUCCESS_deleting_dataset, arg0));
        return this;
    }

    /**
     * Add the created action message for the key 'success.creating_frame' with parameters.
     * <pre>
     * message: Creating Frame from DataSet {0}.
     * </pre>
     * @param property The property name for the message. (NotNull)
     * @param arg0 The parameter arg0 for message. (NotNull)
     * @return this. (NotNull)
     */
    public FioneMessages addSuccessCreatingFrame(final String property, final String arg0) {
        assertPropertyNotNull(property);
        add(property, new UserMessage(SUCCESS_creating_frame, arg0));
        return this;
    }

    /**
     * Add the created action message for the key 'success.deleted_frame' with parameters.
     * <pre>
     * message: Deleted Frame {0}.
     * </pre>
     * @param property The property name for the message. (NotNull)
     * @param arg0 The parameter arg0 for message. (NotNull)
     * @return this. (NotNull)
     */
    public FioneMessages addSuccessDeletedFrame(final String property, final String arg0) {
        assertPropertyNotNull(property);
        add(property, new UserMessage(SUCCESS_deleted_frame, arg0));
        return this;
    }

    /**
     * Add the created action message for the key 'success.deleted_job' with parameters.
     * <pre>
     * message: Deleted Job {0}.
     * </pre>
     * @param property The property name for the message. (NotNull)
     * @param arg0 The parameter arg0 for message. (NotNull)
     * @return this. (NotNull)
     */
    public FioneMessages addSuccessDeletedJob(final String property, final String arg0) {
        assertPropertyNotNull(property);
        add(property, new UserMessage(SUCCESS_deleted_job, arg0));
        return this;
    }

    /**
     * Add the created action message for the key 'success.stopped_job' with parameters.
     * <pre>
     * message: Stopped Job {0}.
     * </pre>
     * @param property The property name for the message. (NotNull)
     * @param arg0 The parameter arg0 for message. (NotNull)
     * @return this. (NotNull)
     */
    public FioneMessages addSuccessStoppedJob(final String property, final String arg0) {
        assertPropertyNotNull(property);
        add(property, new UserMessage(SUCCESS_stopped_job, arg0));
        return this;
    }

    /**
     * Add the created action message for the key 'success.load_dataset' with parameters.
     * <pre>
     * message: Loaded DataSet {0}.
     * </pre>
     * @param property The property name for the message. (NotNull)
     * @param arg0 The parameter arg0 for message. (NotNull)
     * @return this. (NotNull)
     */
    public FioneMessages addSuccessLoadDataset(final String property, final String arg0) {
        assertPropertyNotNull(property);
        add(property, new UserMessage(SUCCESS_load_dataset, arg0));
        return this;
    }

    /**
     * Add the created action message for the key 'success.building_models' with parameters.
     * <pre>
     * message: Building models is started.
     * </pre>
     * @param property The property name for the message. (NotNull)
     * @return this. (NotNull)
     */
    public FioneMessages addSuccessBuildingModels(final String property) {
        assertPropertyNotNull(property);
        add(property, new UserMessage(SUCCESS_building_models));
        return this;
    }

    /**
     * Add the created action message for the key 'success.exporting_frame' with parameters.
     * <pre>
     * message: Exporting Frame {0} to {1}.
     * </pre>
     * @param property The property name for the message. (NotNull)
     * @param arg0 The parameter arg0 for message. (NotNull)
     * @param arg1 The parameter arg1 for message. (NotNull)
     * @return this. (NotNull)
     */
    public FioneMessages addSuccessExportingFrame(final String property, final String arg0, final String arg1) {
        assertPropertyNotNull(property);
        add(property, new UserMessage(SUCCESS_exporting_frame, arg0, arg1));
        return this;
    }

    /**
     * Add the created action message for the key 'success.deleted_all_jobs' with parameters.
     * <pre>
     * message: Deleted all jobs.
     * </pre>
     * @param property The property name for the message. (NotNull)
     * @return this. (NotNull)
     */
    public FioneMessages addSuccessDeletedAllJobs(final String property) {
        assertPropertyNotNull(property);
        add(property, new UserMessage(SUCCESS_deleted_all_jobs));
        return this;
    }

    /**
     * Add the created action message for the key 'success.renew_session' with parameters.
     * <pre>
     * message: Renew a session.
     * </pre>
     * @param property The property name for the message. (NotNull)
     * @return this. (NotNull)
     */
    public FioneMessages addSuccessRenewSession(final String property) {
        assertPropertyNotNull(property);
        add(property, new UserMessage(SUCCESS_renew_session));
        return this;
    }

    /**
     * Add the created action message for the key 'success.deleted_project' with parameters.
     * <pre>
     * message: Deleted Project {0}.
     * </pre>
     * @param property The property name for the message. (NotNull)
     * @param arg0 The parameter arg0 for message. (NotNull)
     * @return this. (NotNull)
     */
    public FioneMessages addSuccessDeletedProject(final String property, final String arg0) {
        assertPropertyNotNull(property);
        add(property, new UserMessage(SUCCESS_deleted_project, arg0));
        return this;
    }

    /**
     * Add the created action message for the key 'success.deleted_model' with parameters.
     * <pre>
     * message: Deleted Model {0}.
     * </pre>
     * @param property The property name for the message. (NotNull)
     * @param arg0 The parameter arg0 for message. (NotNull)
     * @return this. (NotNull)
     */
    public FioneMessages addSuccessDeletedModel(final String property, final String arg0) {
        assertPropertyNotNull(property);
        add(property, new UserMessage(SUCCESS_deleted_model, arg0));
        return this;
    }

    /**
     * Add the created action message for the key 'success.exporting_model' with parameters.
     * <pre>
     * message: Exporting Model {0}.
     * </pre>
     * @param property The property name for the message. (NotNull)
     * @param arg0 The parameter arg0 for message. (NotNull)
     * @return this. (NotNull)
     */
    public FioneMessages addSuccessExportingModel(final String property, final String arg0) {
        assertPropertyNotNull(property);
        add(property, new UserMessage(SUCCESS_exporting_model, arg0));
        return this;
    }

    /**
     * Add the created action message for the key 'success.exporting_all_models' with parameters.
     * <pre>
     * message: Exporting all Models.
     * </pre>
     * @param property The property name for the message. (NotNull)
     * @return this. (NotNull)
     */
    public FioneMessages addSuccessExportingAllModels(final String property) {
        assertPropertyNotNull(property);
        add(property, new UserMessage(SUCCESS_exporting_all_models));
        return this;
    }

    /**
     * Add the created action message for the key 'success.update_dataset' with parameters.
     * <pre>
     * message: Update DataSet {0}.
     * </pre>
     * @param property The property name for the message. (NotNull)
     * @param arg0 The parameter arg0 for message. (NotNull)
     * @return this. (NotNull)
     */
    public FioneMessages addSuccessUpdateDataset(final String property, final String arg0) {
        assertPropertyNotNull(property);
        add(property, new UserMessage(SUCCESS_update_dataset, arg0));
        return this;
    }

    /**
     * Add the created action message for the key 'success.shutdown_h2o' with parameters.
     * <pre>
     * message: Stopping H2O cluster.
     * </pre>
     * @param property The property name for the message. (NotNull)
     * @return this. (NotNull)
     */
    public FioneMessages addSuccessShutdownH2o(final String property) {
        assertPropertyNotNull(property);
        add(property, new UserMessage(SUCCESS_shutdown_h2o));
        return this;
    }

    /**
     * Add the created action message for the key 'success.run_module' with parameters.
     * <pre>
     * message: Running Module {0}.
     * </pre>
     * @param property The property name for the message. (NotNull)
     * @param arg0 The parameter arg0 for message. (NotNull)
     * @return this. (NotNull)
     */
    public FioneMessages addSuccessRunModule(final String property, final String arg0) {
        assertPropertyNotNull(property);
        add(property, new UserMessage(SUCCESS_run_module, arg0));
        return this;
    }

    /**
     * Add the created action message for the key 'success.reload_modules' with parameters.
     * <pre>
     * message: Reloading Modules.
     * </pre>
     * @param property The property name for the message. (NotNull)
     * @return this. (NotNull)
     */
    public FioneMessages addSuccessReloadModules(final String property) {
        assertPropertyNotNull(property);
        add(property, new UserMessage(SUCCESS_reload_modules));
        return this;
    }

    /**
     * Add the created action message for the key 'success.uploaded_module' with parameters.
     * <pre>
     * message: Uploaded Module {0}.
     * </pre>
     * @param property The property name for the message. (NotNull)
     * @param arg0 The parameter arg0 for message. (NotNull)
     * @return this. (NotNull)
     */
    public FioneMessages addSuccessUploadedModule(final String property, final String arg0) {
        assertPropertyNotNull(property);
        add(property, new UserMessage(SUCCESS_uploaded_module, arg0));
        return this;
    }

    /**
     * Add the created action message for the key 'success.deleted_leaderboard' with parameters.
     * <pre>
     * message: Deleted Model Set {0}.
     * </pre>
     * @param property The property name for the message. (NotNull)
     * @param arg0 The parameter arg0 for message. (NotNull)
     * @return this. (NotNull)
     */
    public FioneMessages addSuccessDeletedLeaderboard(final String property, final String arg0) {
        assertPropertyNotNull(property);
        add(property, new UserMessage(SUCCESS_deleted_leaderboard, arg0));
        return this;
    }

    /**
     * Add the created action message for the key 'success.importing_model' with parameters.
     * <pre>
     * message: Importing Model {0}.
     * </pre>
     * @param property The property name for the message. (NotNull)
     * @param arg0 The parameter arg0 for message. (NotNull)
     * @return this. (NotNull)
     */
    public FioneMessages addSuccessImportingModel(final String property, final String arg0) {
        assertPropertyNotNull(property);
        add(property, new UserMessage(SUCCESS_importing_model, arg0));
        return this;
    }

    /**
     * Add the created action message for the key 'errors.project_is_not_found' with parameters.
     * <pre>
     * message: Project {0} is not found.
     * </pre>
     * @param property The property name for the message. (NotNull)
     * @param arg0 The parameter arg0 for message. (NotNull)
     * @return this. (NotNull)
     */
    public FioneMessages addErrorsProjectIsNotFound(final String property, final String arg0) {
        assertPropertyNotNull(property);
        add(property, new UserMessage(ERRORS_project_is_not_found, arg0));
        return this;
    }

    /**
     * Add the created action message for the key 'errors.failed_to_create_project' with parameters.
     * <pre>
     * message: Failed to create Project {0}.
     * </pre>
     * @param property The property name for the message. (NotNull)
     * @param arg0 The parameter arg0 for message. (NotNull)
     * @return this. (NotNull)
     */
    public FioneMessages addErrorsFailedToCreateProject(final String property, final String arg0) {
        assertPropertyNotNull(property);
        add(property, new UserMessage(ERRORS_failed_to_create_project, arg0));
        return this;
    }

    /**
     * Add the created action message for the key 'errors.failed_to_load_project' with parameters.
     * <pre>
     * message: Failed to load Project {0}.
     * </pre>
     * @param property The property name for the message. (NotNull)
     * @param arg0 The parameter arg0 for message. (NotNull)
     * @return this. (NotNull)
     */
    public FioneMessages addErrorsFailedToLoadProject(final String property, final String arg0) {
        assertPropertyNotNull(property);
        add(property, new UserMessage(ERRORS_failed_to_load_project, arg0));
        return this;
    }

    /**
     * Add the created action message for the key 'errors.failed_to_upload_dataset' with parameters.
     * <pre>
     * message: Failed to upload DataSet {0}.
     * </pre>
     * @param property The property name for the message. (NotNull)
     * @param arg0 The parameter arg0 for message. (NotNull)
     * @return this. (NotNull)
     */
    public FioneMessages addErrorsFailedToUploadDataset(final String property, final String arg0) {
        assertPropertyNotNull(property);
        add(property, new UserMessage(ERRORS_failed_to_upload_dataset, arg0));
        return this;
    }

    /**
     * Add the created action message for the key 'errors.failed_to_delete_dataset' with parameters.
     * <pre>
     * message: Failed to delete DataSet {0}.
     * </pre>
     * @param property The property name for the message. (NotNull)
     * @param arg0 The parameter arg0 for message. (NotNull)
     * @return this. (NotNull)
     */
    public FioneMessages addErrorsFailedToDeleteDataset(final String property, final String arg0) {
        assertPropertyNotNull(property);
        add(property, new UserMessage(ERRORS_failed_to_delete_dataset, arg0));
        return this;
    }

    /**
     * Add the created action message for the key 'errors.dataset_is_not_found' with parameters.
     * <pre>
     * message: DataSet {0} is not found.
     * </pre>
     * @param property The property name for the message. (NotNull)
     * @param arg0 The parameter arg0 for message. (NotNull)
     * @return this. (NotNull)
     */
    public FioneMessages addErrorsDatasetIsNotFound(final String property, final String arg0) {
        assertPropertyNotNull(property);
        add(property, new UserMessage(ERRORS_dataset_is_not_found, arg0));
        return this;
    }

    /**
     * Add the created action message for the key 'errors.failed_to_create_frame' with parameters.
     * <pre>
     * message: Failed to create Frame from DataSet {0}.
     * </pre>
     * @param property The property name for the message. (NotNull)
     * @param arg0 The parameter arg0 for message. (NotNull)
     * @return this. (NotNull)
     */
    public FioneMessages addErrorsFailedToCreateFrame(final String property, final String arg0) {
        assertPropertyNotNull(property);
        add(property, new UserMessage(ERRORS_failed_to_create_frame, arg0));
        return this;
    }

    /**
     * Add the created action message for the key 'errors.failed_to_delete_frame' with parameters.
     * <pre>
     * message: Failed to delete Frame {0}.
     * </pre>
     * @param property The property name for the message. (NotNull)
     * @param arg0 The parameter arg0 for message. (NotNull)
     * @return this. (NotNull)
     */
    public FioneMessages addErrorsFailedToDeleteFrame(final String property, final String arg0) {
        assertPropertyNotNull(property);
        add(property, new UserMessage(ERRORS_failed_to_delete_frame, arg0));
        return this;
    }

    /**
     * Add the created action message for the key 'errors.failed_to_delete_job' with parameters.
     * <pre>
     * message: Failed to delete Job {0}.
     * </pre>
     * @param property The property name for the message. (NotNull)
     * @param arg0 The parameter arg0 for message. (NotNull)
     * @return this. (NotNull)
     */
    public FioneMessages addErrorsFailedToDeleteJob(final String property, final String arg0) {
        assertPropertyNotNull(property);
        add(property, new UserMessage(ERRORS_failed_to_delete_job, arg0));
        return this;
    }

    /**
     * Add the created action message for the key 'errors.failed_to_load_dataset' with parameters.
     * <pre>
     * message: Failed to load DataSet {0}.
     * </pre>
     * @param property The property name for the message. (NotNull)
     * @param arg0 The parameter arg0 for message. (NotNull)
     * @return this. (NotNull)
     */
    public FioneMessages addErrorsFailedToLoadDataset(final String property, final String arg0) {
        assertPropertyNotNull(property);
        add(property, new UserMessage(ERRORS_failed_to_load_dataset, arg0));
        return this;
    }

    /**
     * Add the created action message for the key 'errors.failed_to_start_build' with parameters.
     * <pre>
     * message: Failed to start a build process.
     * </pre>
     * @param property The property name for the message. (NotNull)
     * @return this. (NotNull)
     */
    public FioneMessages addErrorsFailedToStartBuild(final String property) {
        assertPropertyNotNull(property);
        add(property, new UserMessage(ERRORS_failed_to_start_build));
        return this;
    }

    /**
     * Add the created action message for the key 'errors.failed_to_export_frame' with parameters.
     * <pre>
     * message: Failed to export Frame {0}.
     * </pre>
     * @param property The property name for the message. (NotNull)
     * @param arg0 The parameter arg0 for message. (NotNull)
     * @return this. (NotNull)
     */
    public FioneMessages addErrorsFailedToExportFrame(final String property, final String arg0) {
        assertPropertyNotNull(property);
        add(property, new UserMessage(ERRORS_failed_to_export_frame, arg0));
        return this;
    }

    /**
     * Add the created action message for the key 'errors.dataset_schema_is_not_found' with parameters.
     * <pre>
     * message: Schema of DataSet {0} is not found.
     * </pre>
     * @param property The property name for the message. (NotNull)
     * @param arg0 The parameter arg0 for message. (NotNull)
     * @return this. (NotNull)
     */
    public FioneMessages addErrorsDatasetSchemaIsNotFound(final String property, final String arg0) {
        assertPropertyNotNull(property);
        add(property, new UserMessage(ERRORS_dataset_schema_is_not_found, arg0));
        return this;
    }

    /**
     * Add the created action message for the key 'errors.leaderboard_is_not_found' with parameters.
     * <pre>
     * message: Model information is not found.
     * </pre>
     * @param property The property name for the message. (NotNull)
     * @return this. (NotNull)
     */
    public FioneMessages addErrorsLeaderboardIsNotFound(final String property) {
        assertPropertyNotNull(property);
        add(property, new UserMessage(ERRORS_leaderboard_is_not_found));
        return this;
    }

    /**
     * Add the created action message for the key 'errors.failed_to_delete_jobs' with parameters.
     * <pre>
     * message: Failed to delete jobs.
     * </pre>
     * @param property The property name for the message. (NotNull)
     * @return this. (NotNull)
     */
    public FioneMessages addErrorsFailedToDeleteJobs(final String property) {
        assertPropertyNotNull(property);
        add(property, new UserMessage(ERRORS_failed_to_delete_jobs));
        return this;
    }

    /**
     * Add the created action message for the key 'errors.failed_to_renew_session' with parameters.
     * <pre>
     * message: Failed to renew the current session.
     * </pre>
     * @param property The property name for the message. (NotNull)
     * @return this. (NotNull)
     */
    public FioneMessages addErrorsFailedToRenewSession(final String property) {
        assertPropertyNotNull(property);
        add(property, new UserMessage(ERRORS_failed_to_renew_session));
        return this;
    }

    /**
     * Add the created action message for the key 'errors.failed_to_delete_project' with parameters.
     * <pre>
     * message: Failed to delete Project {0}.
     * </pre>
     * @param property The property name for the message. (NotNull)
     * @param arg0 The parameter arg0 for message. (NotNull)
     * @return this. (NotNull)
     */
    public FioneMessages addErrorsFailedToDeleteProject(final String property, final String arg0) {
        assertPropertyNotNull(property);
        add(property, new UserMessage(ERRORS_failed_to_delete_project, arg0));
        return this;
    }

    /**
     * Add the created action message for the key 'errors.failed_to_delete_model' with parameters.
     * <pre>
     * message: Failed to delete Model {0}.
     * </pre>
     * @param property The property name for the message. (NotNull)
     * @param arg0 The parameter arg0 for message. (NotNull)
     * @return this. (NotNull)
     */
    public FioneMessages addErrorsFailedToDeleteModel(final String property, final String arg0) {
        assertPropertyNotNull(property);
        add(property, new UserMessage(ERRORS_failed_to_delete_model, arg0));
        return this;
    }

    /**
     * Add the created action message for the key 'errors.failed_to_export_model' with parameters.
     * <pre>
     * message: Failed to export Model {0}.
     * </pre>
     * @param property The property name for the message. (NotNull)
     * @param arg0 The parameter arg0 for message. (NotNull)
     * @return this. (NotNull)
     */
    public FioneMessages addErrorsFailedToExportModel(final String property, final String arg0) {
        assertPropertyNotNull(property);
        add(property, new UserMessage(ERRORS_failed_to_export_model, arg0));
        return this;
    }

    /**
     * Add the created action message for the key 'errors.failed_to_export_models' with parameters.
     * <pre>
     * message: Failed to export Models.
     * </pre>
     * @param property The property name for the message. (NotNull)
     * @return this. (NotNull)
     */
    public FioneMessages addErrorsFailedToExportModels(final String property) {
        assertPropertyNotNull(property);
        add(property, new UserMessage(ERRORS_failed_to_export_models));
        return this;
    }

    /**
     * Add the created action message for the key 'errors.project_exists' with parameters.
     * <pre>
     * message: Project {0} exists.
     * </pre>
     * @param property The property name for the message. (NotNull)
     * @param arg0 The parameter arg0 for message. (NotNull)
     * @return this. (NotNull)
     */
    public FioneMessages addErrorsProjectExists(final String property, final String arg0) {
        assertPropertyNotNull(property);
        add(property, new UserMessage(ERRORS_project_exists, arg0));
        return this;
    }

    /**
     * Add the created action message for the key 'errors.failed_to_update_dataset' with parameters.
     * <pre>
     * message: Failed to update DataSet {0}.
     * </pre>
     * @param property The property name for the message. (NotNull)
     * @param arg0 The parameter arg0 for message. (NotNull)
     * @return this. (NotNull)
     */
    public FioneMessages addErrorsFailedToUpdateDataset(final String property, final String arg0) {
        assertPropertyNotNull(property);
        add(property, new UserMessage(ERRORS_failed_to_update_dataset, arg0));
        return this;
    }

    /**
     * Add the created action message for the key 'errors.failed_to_shutdown_h2o' with parameters.
     * <pre>
     * message: Failed to stop H2O cluster.
     * </pre>
     * @param property The property name for the message. (NotNull)
     * @return this. (NotNull)
     */
    public FioneMessages addErrorsFailedToShutdownH2o(final String property) {
        assertPropertyNotNull(property);
        add(property, new UserMessage(ERRORS_failed_to_shutdown_h2o));
        return this;
    }

    /**
     * Add the created action message for the key 'errors.failed_to_run_module' with parameters.
     * <pre>
     * message: Failed to run Module {0}.
     * </pre>
     * @param property The property name for the message. (NotNull)
     * @param arg0 The parameter arg0 for message. (NotNull)
     * @return this. (NotNull)
     */
    public FioneMessages addErrorsFailedToRunModule(final String property, final String arg0) {
        assertPropertyNotNull(property);
        add(property, new UserMessage(ERRORS_failed_to_run_module, arg0));
        return this;
    }

    /**
     * Add the created action message for the key 'errors.failed_to_reload_modules' with parameters.
     * <pre>
     * message: Failed to reload modules.
     * </pre>
     * @param property The property name for the message. (NotNull)
     * @return this. (NotNull)
     */
    public FioneMessages addErrorsFailedToReloadModules(final String property) {
        assertPropertyNotNull(property);
        add(property, new UserMessage(ERRORS_failed_to_reload_modules));
        return this;
    }

    /**
     * Add the created action message for the key 'errors.failed_to_upload_module' with parameters.
     * <pre>
     * message: Failed to upload Module {0}.
     * </pre>
     * @param property The property name for the message. (NotNull)
     * @param arg0 The parameter arg0 for message. (NotNull)
     * @return this. (NotNull)
     */
    public FioneMessages addErrorsFailedToUploadModule(final String property, final String arg0) {
        assertPropertyNotNull(property);
        add(property, new UserMessage(ERRORS_failed_to_upload_module, arg0));
        return this;
    }

    /**
     * Add the created action message for the key 'errors.failed_to_delete_leaderboard' with parameters.
     * <pre>
     * message: Failed to delete Model Set {0}.
     * </pre>
     * @param property The property name for the message. (NotNull)
     * @param arg0 The parameter arg0 for message. (NotNull)
     * @return this. (NotNull)
     */
    public FioneMessages addErrorsFailedToDeleteLeaderboard(final String property, final String arg0) {
        assertPropertyNotNull(property);
        add(property, new UserMessage(ERRORS_failed_to_delete_leaderboard, arg0));
        return this;
    }

    /**
     * Add the created action message for the key 'errors.failed_to_import_model' with parameters.
     * <pre>
     * message: Failed to import Model {0}.
     * </pre>
     * @param property The property name for the message. (NotNull)
     * @param arg0 The parameter arg0 for message. (NotNull)
     * @return this. (NotNull)
     */
    public FioneMessages addErrorsFailedToImportModel(final String property, final String arg0) {
        assertPropertyNotNull(property);
        add(property, new UserMessage(ERRORS_failed_to_import_model, arg0));
        return this;
    }

    /**
     * Add the created action message for the key 'errors.module_is_not_found' with parameters.
     * <pre>
     * message: Module is not found.
     * </pre>
     * @param property The property name for the message. (NotNull)
     * @return this. (NotNull)
     */
    public FioneMessages addErrorsModuleIsNotFound(final String property) {
        assertPropertyNotNull(property);
        add(property, new UserMessage(ERRORS_module_is_not_found));
        return this;
    }
}
