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
package org.codelibs.fione.h2o.bindings.pojos;

import com.google.gson.GsonBuilder;
import com.google.gson.annotations.SerializedName;

public class AutoMLV99 extends SchemaV3 {

    /**
     * Optional AutoML run ID; omitting this returns all runs
     */
    @SerializedName("automl_id")
    public AutoMLKeyV3 automlId;

    /**
     * ID of the actual training frame for this AutoML run after any automatic splitting
     */
    @SerializedName("training_frame")
    public FrameKeyV3 trainingFrame;

    /**
     * ID of the actual validation frame for this AutoML run after any automatic splitting
     */
    @SerializedName("validation_frame")
    public FrameKeyV3 validationFrame;

    /**
     * ID of the actual blending frame used to train the Stacked Ensembles in blending mode
     */
    @SerializedName("blending_frame")
    public FrameKeyV3 blendingFrame;

    /**
     * ID of the actual leaderboard frame for this AutoML run after any automatic splitting
     */
    @SerializedName("leaderboard_frame")
    public FrameKeyV3 leaderboardFrame;

    /**
     * Identifier for models that should be grouped together in the same leaderboard
     */
    @SerializedName("project_name")
    public String projectName;

    /**
     * The leaderboard for this project, potentially including models from other AutoML runs
     */
    public LeaderboardV99 leaderboard;

    /**
     * The leaderboard for this project, potentially including models from other AutoML runs, for easy rendering
     */
    @SerializedName("leaderboard_table")
    public TwoDimTableV3 leaderboardTable;

    /**
     * Event log of this AutoML run
     */
    @SerializedName("event_log")
    public EventLogV99 eventLog;

    /**
     * Event log of this AutoML run, for easy rendering
     */
    @SerializedName("event_log_table")
    public TwoDimTableV3 eventLogTable;

    /**
     * Metric used to sort leaderboard
     */
    @SerializedName("sort_metric")
    public String sortMetric;

    /**
     * The list of modeling steps effectively used during the AutoML run
     */
    @SerializedName("modeling_steps")
    public StepDefinitionV99[] modelingSteps;

    /**
     * Public constructor
     */
    public AutoMLV99() {
        projectName = "";
        leaderboard = new LeaderboardV99();
        leaderboardTable = new TwoDimTableV3();
        //{'__meta': {'schema_version': 3, 'schema_name': 'TwoDimTableV3', 'schema_type': 'TwoDimTable'}, 'name': 'Leaderboard for project null', 'description': 'no models in this leaderboard', 'columns': [{'__meta': {'schema_version': -1, 'schema_name': 'ColumnSpecsBase', 'schema_type': 'Iced'}, 'name': '', 'type': 'string', 'format': '%s', 'description': '-'}, {'__meta': {'schema_version': -1, 'schema_name': 'ColumnSpecsBase', 'schema_type': 'Iced'}, 'name': 'model_id', 'type': 'string', 'format': '%s', 'description': 'model_id'}], 'rowcount': 0, 'data': [[], []]};
        eventLog = new EventLogV99();
        //{'automl_id': None, 'events': [], 'table': {'__meta': {'schema_version': 3, 'schema_name': 'TwoDimTableV3', 'schema_type': 'TwoDimTable'}, 'name': 'Event Log for AutoML:(new)', 'description': 'Actions taken and discoveries made by AutoML', 'columns': [{'__meta': {'schema_version': -1, 'schema_name': 'ColumnSpecsBase', 'schema_type': 'Iced'}, 'name': '', 'type': 'string', 'format': '%s', 'description': '#'}, {'__meta': {'schema_version': -1, 'schema_name': 'ColumnSpecsBase', 'schema_type': 'Iced'}, 'name': 'timestamp', 'type': 'string', 'format': '%s', 'description': 'timestamp'}, {'__meta': {'schema_version': -1, 'schema_name': 'ColumnSpecsBase', 'schema_type': 'Iced'}, 'name': 'level', 'type': 'string', 'format': '%s', 'description': 'level'}, {'__meta': {'schema_version': -1, 'schema_name': 'ColumnSpecsBase', 'schema_type': 'Iced'}, 'name': 'stage', 'type': 'string', 'format': '%s', 'description': 'stage'}, {'__meta': {'schema_version': -1, 'schema_name': 'ColumnSpecsBase', 'schema_type': 'Iced'}, 'name': 'message', 'type': 'string', 'format': '%s', 'description': 'message'}, {'__meta': {'schema_version': -1, 'schema_name': 'ColumnSpecsBase', 'schema_type': 'Iced'}, 'name': 'name', 'type': 'string', 'format': '%s', 'description': 'name'}, {'__meta': {'schema_version': -1, 'schema_name': 'ColumnSpecsBase', 'schema_type': 'Iced'}, 'name': 'value', 'type': 'string', 'format': '%s', 'description': 'value'}], 'rowcount': 0, 'data': [[], [], [], [], [], [], []]}};
        eventLogTable = new TwoDimTableV3();
        //{'__meta': {'schema_version': 3, 'schema_name': 'TwoDimTableV3', 'schema_type': 'TwoDimTable'}, 'name': 'Event Log for AutoML:(new)', 'description': 'Actions taken and discoveries made by AutoML', 'columns': [{'__meta': {'schema_version': -1, 'schema_name': 'ColumnSpecsBase', 'schema_type': 'Iced'}, 'name': '', 'type': 'string', 'format': '%s', 'description': '#'}, {'__meta': {'schema_version': -1, 'schema_name': 'ColumnSpecsBase', 'schema_type': 'Iced'}, 'name': 'timestamp', 'type': 'string', 'format': '%s', 'description': 'timestamp'}, {'__meta': {'schema_version': -1, 'schema_name': 'ColumnSpecsBase', 'schema_type': 'Iced'}, 'name': 'level', 'type': 'string', 'format': '%s', 'description': 'level'}, {'__meta': {'schema_version': -1, 'schema_name': 'ColumnSpecsBase', 'schema_type': 'Iced'}, 'name': 'stage', 'type': 'string', 'format': '%s', 'description': 'stage'}, {'__meta': {'schema_version': -1, 'schema_name': 'ColumnSpecsBase', 'schema_type': 'Iced'}, 'name': 'message', 'type': 'string', 'format': '%s', 'description': 'message'}, {'__meta': {'schema_version': -1, 'schema_name': 'ColumnSpecsBase', 'schema_type': 'Iced'}, 'name': 'name', 'type': 'string', 'format': '%s', 'description': 'name'}, {'__meta': {'schema_version': -1, 'schema_name': 'ColumnSpecsBase', 'schema_type': 'Iced'}, 'name': 'value', 'type': 'string', 'format': '%s', 'description': 'value'}], 'rowcount': 0, 'data': [[], [], [], [], [], [], []]};
        sortMetric = "";
    }

    /**
     * Return the contents of this object as a JSON String.
     */
    @Override
    public String toString() {
        return new GsonBuilder().serializeSpecialFloatingPointValues().create().toJson(this);
    }

}
