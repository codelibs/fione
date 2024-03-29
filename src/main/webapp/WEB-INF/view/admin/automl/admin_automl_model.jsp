<%@page pageEncoding="UTF-8" contentType="text/html; charset=UTF-8"%><%@taglib prefix="fi" uri="http://fione.codelibs.org/functions" %><!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title><la:message key="labels.fione_brand_title" /> | <la:message key="labels.automl" /></title>
<jsp:include page="/WEB-INF/view/common/admin/head.jsp"></jsp:include>
<script src="${fe:url('/js/admin/fione/echarts.min.js')}" type="text/javascript"></script>
</head>
<body class="hold-transition skin-blue sidebar-mini">
	<div class="wrapper">
		<jsp:include page="/WEB-INF/view/common/admin/header.jsp"></jsp:include>
		<jsp:include page="/WEB-INF/view/common/admin/sidebar.jsp">
			<jsp:param name="brandName" value="Fione" />
			<jsp:param name="logoPath" value="/images/fione/logo-head.png" />
			<jsp:param name="menuCategoryType" value="fione" />
			<jsp:param name="menuType" value="automl" />
		</jsp:include>
		<div class="content-wrapper">
			<div class="content-header">
				<div class="container-fluid">
					<div class="row mb-2">
						<div class="col-sm-6">
							<h1>${f:h(model.modelId.name)}</h1>
						</div>
						<div class="col-sm-6">
							<ol class="breadcrumb float-sm-right">
								<li class="breadcrumb-item"><la:link href="/admin/automl">
								<la:message key="labels.crud_link_list" /></la:link></li>
								<li class="breadcrumb-item"><la:link href="/admin/automl/job/${f:u(projectId)}?fid=${f:u(frameId)}&lid=${f:u(leaderboardId)}">
									<la:message key="labels.automl_project" />
								</la:link></li>
								<li class="breadcrumb-item active"><la:message key="labels.automl_model" /></li>
							</ol>
						</div>
					</div>
				</div>
			</div>
			<section class="content">
				<div class="row">
					<div class="col-md-12">
						<la:info id="msg" message="true">
							<div class="alert alert-info">${msg}</div>
						</la:info>
						<la:errors />
						<div class="card card-outline">
							<div class="card-body p-2">
								<form method="post" action="${contextPath}/admin/automl/">
								<input type="hidden" name="lastaflute.action.TRANSACTION_TOKEN" value="${f:h(token)}">
								<input type="hidden" name="projectId" value="${f:h(projectId)}">
								<input type="hidden" name="modelId" value="${f:h(model.modelId.name)}">
								<input type="hidden" name="frameId" value="${f:h(frameId)}">
								<input type="hidden" name="leaderboardId" value="${f:h(leaderboardId)}">
								<div class="btn-group" role="toolbar" aria-label="Toolbar">
									<c:if test="${model.inLocal}">
									<button type="submit" name="importmodel" value="import" class="btn btn-default">
										<i class="fas fa-file-import"></i>
										<la:message key="labels.automl_model_import" />
									</button>
									</c:if><c:if test="${not model.inLocal}">
									<a href="${contextPath}/admin/automl/prediction/${f:u(projectId)}/${f:u(frameId)}/${f:u(leaderboardId)}/?mid=${f:u(model.modelId.name)}" class="btn btn-default">
										<i class="fas fa-file-signature"></i>
										<la:message key="labels.automl_predict_dataset" />
									</a>
									<la:link href="/admin/automl/serving/${f:u(projectId)}?fid=${f:u(frameId)}&lid=${f:u(leaderboardId)}&mid=${f:u(model.modelId.name)}" styleClass="btn btn-default">
										<i class="fas fa-server"></i>
										<la:message key="labels.automl_serving" />
									</la:link>
									<button type="submit" name="downloadmojo" value="download" class="btn btn-default">
										<i class="fas fa-download"></i>
										<la:message key="labels.automl_model_mojo" />
									</button>
									<button type="submit" name="exportmodel" value="export" class="btn btn-default">
										<i class="fas fa-file-export"></i>
										<la:message key="labels.automl_model_export" />
									</button>
									</c:if>
									<la:link href="/admin/automl/job/${f:u(projectId)}?fid=${f:u(frameId)}&lid=${f:u(leaderboardId)}" styleClass="btn btn-default">
										<i class="fas fa-tasks"></i>
										<la:message key="labels.automl_job" />
									</la:link>
								</div>
								<div class="float-right">
									<c:if test="${not model.inLocal}">
									<button type="submit" name="deletemodel" value="load" class="btn btn-outline-danger">
										<i class="fas fa-trash-alt"></i>
										<la:message key="labels.automl_delete" />
									</button>
									</c:if>
								</div>
								</form>
							</div>
						</div>
					</div>
					<div class="col-md-6">
						<c:if test="${model.output.scoringHistory != null}">
						<div class="card card-outline card-primary">
							<div class="card-header">
								<h3 class="card-title">${f:h(model.output.scoringHistory.name)}</h3>
								<div class="card-tools">
									<button type="button" class="btn btn-tool" data-card-widget="collapse">
										<i class="fa fa-minus"></i>
									</button>
								</div>
							</div>
							<div class="card-body">
								<c:if test="${model.output.scoringHistory.rowcount == 0}">
									<div class="row top10">
										<div class="col-sm-12">
											<em class="fa fa-info-circle text-primary"></em>
											<la:message key="labels.list_could_not_find_crud_table" />
										</div>
									</div>
								</c:if>
								<c:if test="${model.output.scoringHistory.rowcount gt 0}">
									<div class="row">
										<div class="col-sm-12">
										<ul class="nav nav-tabs" role="tablist" id="scoringHistoryTabs">
											<li class="nav-item"><a class="nav-link active" id="scoringHistoryGraphTab" data-toggle="tab" href="#scoringHistoryGraph" role="tab" aria-controls="scoringHistoryGraph" aria-selected="true"><la:message key="labels.automl_model_graph" /></a></li>
											<li class="nav-item"><a class="nav-link" id="scoringHistoryDetailsTab" data-toggle="tab" href="#scoringHistoryDetails" role="tab" aria-controls="scoringHistoryGraph" aria-selected="false"><la:message key="labels.automl_model_details" /></a></li>
										</ul>
										<div class="tab-content">
										<div role="tabpanel" class="tab-pane fade show active" id="scoringHistoryGraph">
										<c:set var="chart" value="${model.output.scoringHistoryChart}"/><div id="scoringHistoryChart" style="width:100%;height:400px;"></div>
<script><!--
echarts.init(document.getElementById('scoringHistoryChart')).setOption({
    xAxis: [<c:forEach var="xAxis" items="${chart.xAxis}">{
        name: '${f:h(xAxis.name)}',
        nameLocation: 'center',
        data: ${f:h(xAxis.data)}
    },</c:forEach>],
    yAxis: [<c:forEach var="yAxis" items="${chart.yAxis}">{
        name: '${f:h(yAxis.name)}',
        type: 'value'
    },</c:forEach>],
    series: [<c:forEach var="data" items="${chart.series}">{
        data: ${data.data},
        type: 'line'
    },</c:forEach>]}
)
// -->
</script>
										</div>
										<div role="tabpanel" class="tab-pane fade" id="scoringHistoryDetails">
											<table class="table table-bordered table-striped small mt-1">
												<thead>
													<tr>
													<c:forEach var="i" varStatus="s" begin="0" end="${fn:length(model.output.scoringHistory.columns)-1}">
														<c:if test="${not empty model.output.scoringHistory.columns[i].name}">
														<th>${f:h(model.output.scoringHistory.columns[i].name)}</th>
														</c:if>
													</c:forEach>
													</tr>
												</thead>
												<tbody>
													<c:forEach var="i" begin="0" end="${model.output.scoringHistory.rowcount-1}">
														<tr>
														<c:forEach var="j" begin="0" end="${fn:length(model.output.scoringHistory.columns)-1}">
															<c:if test="${not empty model.output.scoringHistory.columns[j].name}">
															<td>${f:h(model.output.scoringHistory.data[j][i])}</td>
															</c:if>
														</c:forEach>
														</tr>
													</c:forEach>
												</tbody>
											</table>
										</div>
										</div>
										</div>
									</div>
								</c:if>
							</div>
						</div>
						</c:if>
						<c:if test="${model.parameters != null}">
						<div class="card card-outline card-primary">
							<div class="card-header">
								<h3 class="card-title"><la:message key="labels.automl_model_parameters" /></h3>
								<div class="card-tools">
									<button type="button" class="btn btn-tool" data-card-widget="collapse">
										<i class="fa fa-minus"></i>
									</button>
								</div>
							</div>
							<div class="card-body">
								<c:if test="${fn:length(model.parameters.fieldNames) == 0}">
									<div class="row top10">
										<div class="col-sm-12">
											<em class="fa fa-info-circle text-primary"></em>
											<la:message key="labels.list_could_not_find_crud_table" />
										</div>
									</div>
								</c:if>
								<c:if test="${fn:length(model.parameters.fieldNames) gt 0}">
									<div class="row">
										<div class="col-sm-12">
											<table class="table table-bordered table-striped small">
												<thead>
													<tr>
														<th><la:message key="labels.automl_parameter" /></th>
														<th><la:message key="labels.automl_value" /></th>
													</tr>
												</thead>
												<tbody>
													<c:forEach var="i" varStatus="s" begin="0" end="${fn:length(model.parameters.fieldNames)-1}">
														<tr>
															<td>${f:h(model.parameters.fieldNames[i])}</td>
															<td>${f:h(model.parameters.fieldValues[i])}</td>
														</tr>
													</c:forEach>
												</tbody>
											</table>
										</div>
									</div>
								</c:if>
							</div>
						</div>
						</c:if>
						<c:if test="${model.output != null}">
						<div class="card card-outline card-primary">
							<div class="card-header">
								<h3 class="card-title"><la:message key="labels.automl_output" /></h3>
								<div class="card-tools">
									<button type="button" class="btn btn-tool" data-card-widget="collapse">
										<i class="fa fa-minus"></i>
									</button>
								</div>
							</div>
							<div class="card-body">
								<c:if test="${fn:length(model.output.fieldNames) == 0}">
									<div class="row top10">
										<div class="col-sm-12">
											<em class="fa fa-info-circle text-primary"></em>
											<la:message key="labels.list_could_not_find_crud_table" />
										</div>
									</div>
								</c:if>
								<c:if test="${fn:length(model.output.fieldNames) gt 0}">
									<div class="row">
										<div class="col-sm-12">
											<table class="table table-bordered table-striped small">
												<thead>
													<tr>
														<th><la:message key="labels.automl_parameter" /></th>
														<th><la:message key="labels.automl_value" /></th>
													</tr>
												</thead>
												<tbody>
													<c:forEach var="i" varStatus="s" begin="0" end="${fn:length(model.output.fieldNames)-1}">
														<tr>
															<td>${f:h(model.output.fieldNames[i])}</td>
															<td>${f:h(model.output.fieldValues[i])}</td>
														</tr>
													</c:forEach>
												</tbody>
											</table>
										</div>
									</div>
								</c:if>
							</div>
						</div>
						</c:if>
						<c:if test="${model.output.crossValidationModels != null}">
						<div class="card card-outline card-primary">
							<div class="card-header">
								<h3 class="card-title"><la:message key="labels.automl_cross_validation" /></h3>
								<div class="card-tools">
									<button type="button" class="btn btn-tool" data-card-widget="collapse">
										<i class="fa fa-minus"></i>
									</button>
								</div>
							</div>
							<div class="card-body">
								<c:if test="${fn:length(model.output.crossValidationModels) == 0}">
									<div class="row top10">
										<div class="col-sm-12">
											<em class="fa fa-info-circle text-primary"></em>
											<la:message key="labels.list_could_not_find_crud_table" />
										</div>
									</div>
								</c:if>
								<c:if test="${fn:length(model.output.crossValidationModels) gt 0}">
									<div class="row">
										<div class="col-sm-12">
											<table class="table table-bordered table-striped small">
												<thead>
													<tr>
														<th><la:message key="labels.automl_models" /></th>
														<th><la:message key="labels.automl_predictions" /></th>
													</tr>
												</thead>
												<tbody>
													<c:forEach var="i" varStatus="s" begin="0" end="${fn:length(model.output.crossValidationModels)-1}">
														<tr>
															<td><a href="${contextPath}/admin/automl/model/${f:u(projectId)}/${f:u(model.output.crossValidationModels[i].name)}?fid=${f:u(frameId)}&lid=${f:u(leaderboardId)}">${f:h(model.output.crossValidationModels[i].name)}</a></td>
															<td>${f:h(model.output.crossValidationPredictions[i].name)}</td>
														</tr>
													</c:forEach>
												</tbody>
											</table>
										</div>
									</div>
								</c:if>
							</div>
						</div>
						</c:if>
						<c:if test="${model.output.modelSummary != null}">
						<div class="card card-outline card-primary">
							<div class="card-header">
								<h3 class="card-title">${f:h(model.output.modelSummary.name)}</h3>
								<div class="card-tools">
									<button type="button" class="btn btn-tool" data-card-widget="collapse">
										<i class="fa fa-minus"></i>
									</button>
								</div>
							</div>
							<div class="card-body">
								<c:if test="${model.output.modelSummary.rowcount == 0}">
									<div class="row top10">
										<div class="col-sm-12">
											<em class="fa fa-info-circle text-primary"></em>
											<la:message key="labels.list_could_not_find_crud_table" />
										</div>
									</div>
								</c:if>
								<c:if test="${model.output.modelSummary.rowcount gt 0}">
									<div class="row">
										<div class="col-sm-12">
											<table class="table table-bordered table-striped small">
												<thead>
													<tr>
													<c:forEach var="i" varStatus="s" begin="0" end="${fn:length(model.output.modelSummary.columns)-1}">
														<c:if test="${not empty model.output.modelSummary.columns[i].name}">
														<th>${f:h(model.output.modelSummary.columns[i].name)}</th>
														</c:if>
													</c:forEach>
													</tr>
												</thead>
												<tbody>
													<c:forEach var="i" begin="0" end="${model.output.modelSummary.rowcount-1}">
														<tr>
														<c:forEach var="j" begin="0" end="${fn:length(model.output.modelSummary.columns)-1}">
															<c:if test="${not empty model.output.modelSummary.columns[j].name}">
															<td>${f:h(model.output.modelSummary.data[j][i])}</td>
															</c:if>
														</c:forEach>
														</tr>
													</c:forEach>
												</tbody>
											</table>
										</div>
									</div>
								</c:if>
							</div>
						</div>
						</c:if>
					</div>
					<div class="col-md-6">
						<c:catch var="vie"><c:if test="${model.output.variableImportances==null}"></c:if></c:catch>
						<c:if test="${empty vie and model.output.variableImportances!=null}">
						<div class="card card-outline card-primary">
							<div class="card-header">
								<h3 class="card-title">${f:h(model.output.variableImportances.name)}</h3>
								<div class="card-tools">
									<button type="button" class="btn btn-tool" data-card-widget="collapse">
										<i class="fa fa-minus"></i>
									</button>
								</div>
							</div>
							<div class="card-body">
								<c:if test="${model.output.variableImportances.rowcount == 0}">
									<div class="row top10">
										<div class="col-sm-12">
											<em class="fa fa-info-circle text-primary"></em>
											<la:message key="labels.list_could_not_find_crud_table" />
										</div>
									</div>
								</c:if>
								<c:if test="${model.output.variableImportances.rowcount gt 0}">
									<div class="row">
										<div class="col-sm-12">
										<ul class="nav nav-tabs" role="tablist" id="variableImportancesTabs">
											<li class="nav-item"><a class="nav-link active" id="variableImportancesGraphTab" data-toggle="tab" href="#variableImportancesGraph" role="tab" aria-controls="variableImportancesGraph" aria-selected="true"><la:message key="labels.automl_model_graph" /></a></li>
											<li class="nav-item"><a class="nav-link" id="variableImportancesDetailsTab" data-toggle="tab" href="#variableImportancesDetails" role="tab" aria-controls="variableImportancesDetails" aria-selected="false"><la:message key="labels.automl_model_details" /></a></li>
										</ul>
										<div class="tab-content">
										<div role="tabpanel" class="tab-pane fade show active" id="variableImportancesGraph">
										<c:set var="chart" value="${model.output.variableImportancesChart}"/><div id="variableImportancesChart" style="width:100%;height:${chart.height}px;"></div>
<script><!--
echarts.init(document.getElementById('variableImportancesChart')).setOption({
    tooltip: {
        trigger: 'axis',
        axisPointer: {
            type: 'shadow'
        }
    },
    xAxis: [<c:forEach var="xAxis" items="${chart.yAxis}">{
        name: '${f:h(xAxis.name)}',
        nameLocation: 'center',
        type: 'value'
    },</c:forEach>],
    yAxis: [<c:forEach var="yAxis" items="${chart.xAxis}">{
        name: '${f:h(yAxis.name)}',
        type: 'category',
        data: ${yAxis.data}
    },</c:forEach>],
    series: [<c:forEach var="data" items="${chart.series}">{
        data: ${data.data},
        type: 'bar'
    },</c:forEach>]}
)
// -->
</script>
										</div>
										<div role="tabpanel" class="tab-pane fade" id="variableImportancesDetails">
											<table class="table table-bordered table-striped small mt-1">
												<thead>
													<tr>
													<c:forEach var="i" varStatus="s" begin="0" end="${fn:length(model.output.variableImportances.columns)-1}">
														<c:if test="${not empty model.output.variableImportances.columns[i].name}">
														<th>${f:h(model.output.variableImportances.columns[i].name)}</th>
														</c:if>
													</c:forEach>
													</tr>
												</thead>
												<tbody>
													<c:forEach var="i" begin="0" end="${model.output.variableImportances.rowcount-1}">
														<tr>
														<c:forEach var="j" begin="0" end="${fn:length(model.output.variableImportances.columns)-1}">
															<c:if test="${not empty model.output.variableImportances.columns[j].name}">
															<td>${f:h(model.output.variableImportances.data[j][i])}</td>
															</c:if>
														</c:forEach>
														</tr>
													</c:forEach>
												</tbody>
											</table>
										</div>
										</div>
										</div>
									</div>
								</c:if>
							</div>
						</div>
						</c:if>
						<c:if test="${model.output.crossValidationMetricsSummary != null}">
						<div class="card card-outline card-primary">
							<div class="card-header">
								<h3 class="card-title">${f:h(model.output.crossValidationMetricsSummary.name)}</h3>
								<div class="card-tools">
									<button type="button" class="btn btn-tool" data-card-widget="collapse">
										<i class="fa fa-minus"></i>
									</button>
								</div>
							</div>
							<div class="card-body">
								<c:if test="${model.output.crossValidationMetricsSummary.rowcount == 0}">
									<div class="row top10">
										<div class="col-sm-12">
											<em class="fa fa-info-circle text-primary"></em>
											<la:message key="labels.list_could_not_find_crud_table" />
										</div>
									</div>
								</c:if>
								<c:if test="${model.output.crossValidationMetricsSummary.rowcount gt 0}">
									<div class="row">
										<div class="col-sm-12">
											<table class="table table-bordered table-striped small">
												<thead>
													<tr>
													<c:forEach var="i" varStatus="s" begin="0" end="${fn:length(model.output.crossValidationMetricsSummary.columns)-1}">
														<c:if test="${not empty model.output.crossValidationMetricsSummary.columns[i].name}">
														<th>${f:h(model.output.crossValidationMetricsSummary.columns[i].name)}</th>
														</c:if>
													</c:forEach>
													</tr>
												</thead>
												<tbody>
													<c:forEach var="i" begin="0" end="${model.output.modelSummary.rowcount}">
														<tr>
														<c:forEach var="j" begin="0" end="${fn:length(model.output.crossValidationMetricsSummary.columns)-1}">
															<c:if test="${not empty model.output.crossValidationMetricsSummary.columns[j].name}">
															<td>${f:h(model.output.crossValidationMetricsSummary.data[j][i])}</td>
															</c:if>
														</c:forEach>
														</tr>
													</c:forEach>
												</tbody>
											</table>
										</div>
									</div>
								</c:if>
							</div>
						</div>
						</c:if>
						<c:if test="${model.output.trainingMetrics != null}">
						<div class="card card-outline card-primary">
							<div class="card-header">
								<h3 class="card-title"><la:message key="labels.automl_training_metrics" /></h3>
								<div class="card-tools">
									<button type="button" class="btn btn-tool" data-card-widget="collapse">
										<i class="fa fa-minus"></i>
									</button>
								</div>
							</div>
							<div class="card-body">
								<c:if test="${fn:length(model.output.trainingMetrics.fieldNames) == 0}">
									<div class="row top10">
										<div class="col-sm-12">
											<em class="fa fa-info-circle text-primary"></em>
											<la:message key="labels.list_could_not_find_crud_table" />
										</div>
									</div>
								</c:if>
								<c:if test="${fn:length(model.output.trainingMetrics.fieldNames) gt 0}">
									<div class="row">
										<div class="col-sm-12">
											<table class="table table-bordered table-striped small">
												<thead>
													<tr>
														<th><la:message key="labels.automl_parameter" /></th>
														<th><la:message key="labels.automl_value" /></th>
													</tr>
												</thead>
												<tbody>
													<c:forEach var="i" varStatus="s" begin="0" end="${fn:length(model.output.trainingMetrics.fieldNames)-1}">
														<tr>
															<td>${f:h(model.output.trainingMetrics.fieldNames[i])}</td>
															<td>${f:h(model.output.trainingMetrics.fieldValues[i])}</td>
														</tr>
													</c:forEach>
												</tbody>
											</table>
										</div>
									</div>
								</c:if>
							</div>
						</div>
						</c:if>
						<c:if test="${model.output.validationMetrics != null}">
						<div class="card card-outline card-primary">
							<div class="card-header">
								<h3 class="card-title"><la:message key="labels.automl_validation_metrics" /></h3>
								<div class="card-tools">
									<button type="button" class="btn btn-tool" data-card-widget="collapse">
										<i class="fa fa-minus"></i>
									</button>
								</div>
							</div>
							<div class="card-body">
								<c:if test="${fn:length(model.output.validationMetrics.fieldNames) == 0}">
									<div class="row top10">
										<div class="col-sm-12">
											<em class="fa fa-info-circle text-primary"></em>
											<la:message key="labels.list_could_not_find_crud_table" />
										</div>
									</div>
								</c:if>
								<c:if test="${fn:length(model.output.validationMetrics.fieldNames) gt 0}">
									<div class="row">
										<div class="col-sm-12">
											<table class="table table-bordered table-striped small">
												<thead>
													<tr>
														<th><la:message key="labels.automl_parameter" /></th>
														<th><la:message key="labels.automl_value" /></th>
													</tr>
												</thead>
												<tbody>
													<c:forEach var="i" varStatus="s" begin="0" end="${fn:length(model.output.validationMetrics.fieldNames)-1}">
														<tr>
															<td>${f:h(model.output.validationMetrics.fieldNames[i])}</td>
															<td>${f:h(model.output.validationMetrics.fieldValues[i])}</td>
														</tr>
													</c:forEach>
												</tbody>
											</table>
										</div>
									</div>
								</c:if>
							</div>
						</div>
						</c:if>
						<c:if test="${model.output.crossValidationMetrics != null}">
						<div class="card card-outline card-primary">
							<div class="card-header">
								<h3 class="card-title"><la:message key="labels.automl_cross_validation_metrics" /></h3>
								<div class="card-tools">
									<button type="button" class="btn btn-tool" data-card-widget="collapse">
										<i class="fa fa-minus"></i>
									</button>
								</div>
							</div>
							<div class="card-body">
								<c:if test="${fn:length(model.output.crossValidationMetrics.fieldNames) == 0}">
									<div class="row top10">
										<div class="col-sm-12">
											<em class="fa fa-info-circle text-primary"></em>
											<la:message key="labels.list_could_not_find_crud_table" />
										</div>
									</div>
								</c:if>
								<c:if test="${fn:length(model.output.crossValidationMetrics.fieldNames) gt 0}">
									<div class="row">
										<div class="col-sm-12">
											<table class="table table-bordered table-striped small">
												<thead>
													<tr>
														<th><la:message key="labels.automl_parameter" /></th>
														<th><la:message key="labels.automl_value" /></th>
													</tr>
												</thead>
												<tbody>
													<c:forEach var="i" varStatus="s" begin="0" end="${fn:length(model.output.crossValidationMetrics.fieldNames)-1}">
														<tr>
															<td>${f:h(model.output.crossValidationMetrics.fieldNames[i])}</td>
															<td>${f:h(model.output.crossValidationMetrics.fieldValues[i])}</td>
														</tr>
													</c:forEach>
												</tbody>
											</table>
										</div>
									</div>
								</c:if>
							</div>
						</div>
						</c:if>
					</div>
				</div>
			</section>
		</div>
		<jsp:include page="/WEB-INF/view/common/admin/footer.jsp"></jsp:include>
	</div>
	<jsp:include page="/WEB-INF/view/common/admin/foot.jsp"></jsp:include>
</body>
</html>
