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

    /**
     * Add the created action message for the key 'success.created_project' with parameters.
     * <pre>
     * message: Created Project {0}.
     * </pre>
     * @param property The property name for the message. (NotNull)
     * @param arg0 The parameter arg0 for message. (NotNull)
     * @return this. (NotNull)
     */
    public FioneMessages addSuccessCreatedProject(String property, String arg0) {
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
    public FioneMessages addSuccessUploadedDataset(String property, String arg0) {
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
    public FioneMessages addSuccessDeletingDataset(String property, String arg0) {
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
    public FioneMessages addSuccessCreatingFrame(String property, String arg0) {
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
    public FioneMessages addSuccessDeletedFrame(String property, String arg0) {
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
    public FioneMessages addSuccessDeletedJob(String property, String arg0) {
        assertPropertyNotNull(property);
        add(property, new UserMessage(SUCCESS_deleted_job, arg0));
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
    public FioneMessages addSuccessLoadDataset(String property, String arg0) {
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
    public FioneMessages addSuccessBuildingModels(String property) {
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
    public FioneMessages addSuccessExportingFrame(String property, String arg0, String arg1) {
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
    public FioneMessages addSuccessDeletedAllJobs(String property) {
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
    public FioneMessages addSuccessRenewSession(String property) {
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
    public FioneMessages addSuccessDeletedProject(String property, String arg0) {
        assertPropertyNotNull(property);
        add(property, new UserMessage(SUCCESS_deleted_project, arg0));
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
    public FioneMessages addErrorsProjectIsNotFound(String property, String arg0) {
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
    public FioneMessages addErrorsFailedToCreateProject(String property, String arg0) {
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
    public FioneMessages addErrorsFailedToLoadProject(String property, String arg0) {
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
    public FioneMessages addErrorsFailedToUploadDataset(String property, String arg0) {
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
    public FioneMessages addErrorsFailedToDeleteDataset(String property, String arg0) {
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
    public FioneMessages addErrorsDatasetIsNotFound(String property, String arg0) {
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
    public FioneMessages addErrorsFailedToCreateFrame(String property, String arg0) {
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
    public FioneMessages addErrorsFailedToDeleteFrame(String property, String arg0) {
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
    public FioneMessages addErrorsFailedToDeleteJob(String property, String arg0) {
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
    public FioneMessages addErrorsFailedToLoadDataset(String property, String arg0) {
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
    public FioneMessages addErrorsFailedToStartBuild(String property) {
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
    public FioneMessages addErrorsFailedToExportFrame(String property, String arg0) {
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
    public FioneMessages addErrorsDatasetSchemaIsNotFound(String property, String arg0) {
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
    public FioneMessages addErrorsLeaderboardIsNotFound(String property) {
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
    public FioneMessages addErrorsFailedToDeleteJobs(String property) {
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
    public FioneMessages addErrorsFailedToRenewSession(String property) {
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
    public FioneMessages addErrorsFailedToDeleteProject(String property, String arg0) {
        assertPropertyNotNull(property);
        add(property, new UserMessage(ERRORS_failed_to_delete_project, arg0));
        return this;
    }
}
