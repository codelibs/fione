<%@page pageEncoding="UTF-8" contentType="text/html; charset=UTF-8"%><%@taglib prefix="fi" uri="http://fione.codelibs.org/functions" %><!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title><la:message key="labels.admin_brand_title" /> | <la:message key="labels.automl" /></title>
<jsp:include page="/WEB-INF/view/common/admin/head.jsp"></jsp:include>
</head>
<body class="skin-blue sidebar-mini">
	<div class="wrapper">
		<jsp:include page="/WEB-INF/view/common/admin/header.jsp"></jsp:include>
		<jsp:include page="/WEB-INF/view/common/admin/sidebar.jsp">
			<jsp:param name="menuCategoryType" value="fione" />
			<jsp:param name="menuType" value="automl" />
		</jsp:include>
		<div class="content-wrapper">
			<section class="content-header">
				<h1>${f:h(model.modelId.name)}</h1>
				<ol class="breadcrumb">
					<li><la:link href="/admin/automl">
							<la:message key="labels.crud_link_list" />
						</la:link></li>
					<li><la:link href="/admin/automl/details/${f:u(projectId)}?frameId=${f:u(frameId)}&leaderboardId=${f:u(leaderboardId)}">
							Project
						</la:link></li>
					<li class="active">Model</li>
				</ol>
			</section>
			<section class="content">
				<div class="row">
					<div class="col-md-12">
						<la:info id="msg" message="true">
							<div class="alert alert-info">${msg}</div>
						</la:info>
						<la:errors />
					</div>
					<div class="col-md-12">
					<form method="post" action="${contextPath}/admin/automl/">
						<input type="hidden" name="lastaflute.action.TRANSACTION_TOKEN" value="${f:h(token)}">
						<input type="hidden" name="projectId" value="${f:h(projectId)}">
						<input type="hidden" name="modelId" value="${f:h(model.modelId.name)}">
						<input type="hidden" name="frameId" value="${f:h(frameId)}">
						<input type="hidden" name="leaderboardId" value="${f:h(leaderboardId)}">
						<div class="btn-group" role="toolbar" aria-label="Toolbar" style="margin-bottom:5px;">
							<a href="${contextPath}/admin/automl/prediction/${f:u(projectId)}/${f:u(frameId)}/${f:u(leaderboardId)}/?modelId=${f:u(model.modelId.name)}" class="btn btn-default"><i class="fas fa-file-signature"></i>Predict</a>
							<button type="submit" name="downloadmojo" value="load" class="btn btn-default"><i class="fas fa-download"></i>MOJO</button>
							<button type="submit" name="downloadgenmodel" value="load" class="btn btn-default"><i class="fas fa-download"></i>Gen Model</button>
							<button type="submit" name="exportmodel" value="load" class="btn btn-default"><i class="fas fa-file-export"></i>Export</button>
							<la:link href="/admin/automl/details/${f:u(projectId)}?frameId=${f:u(frameId)}&leaderboardId=${f:u(leaderboardId)}" styleClass="btn btn-default"><i class="fas fa-project-diagram"></i>Project</la:link>
						</div>
						<div class="btn-group pull-right" role="toolbar" aria-label="Toolbar" style="margin-bottom:5px;">
							<button type="submit" name="deletemodel" value="load" class="btn btn-default"><i class="fas fa-trash-alt"></i>Delete</button>
						</div>
						</form>
					</div>
					<div class="col-md-6">
						<c:if test="${model.parameters != null}">
						<div class="box box-primary">
							<div class="box-header with-border">
								<h3 class="box-title">Model Parameters</h3>
								<div class="btn-group pull-right">
									<button type="button" class="btn btn-box-tool" data-widget="collapse">
										<i class="fa fa-minus"></i>
									</button>
								</div>
							</div>
							<div class="box-body">
								<c:if test="${fn:length(model.parameters.fieldNames) == 0}">
									<div class="row top10">
										<div class="col-sm-12">
											<em class="fa fa-info-circle text-light-blue"></em>
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
														<th>Parameter</th>
														<th>Value</th>
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
						<div class="box box-primary">
							<div class="box-header with-border">
								<h3 class="box-title">Output</h3>
								<div class="btn-tools pull-right">
									<button type="button" class="btn btn-box-tool" data-widget="collapse">
										<i class="fa fa-minus"></i>
									</button>
								</div>
							</div>
							<div class="box-body">
								<c:if test="${fn:length(model.output.fieldNames) == 0}">
									<div class="row top10">
										<div class="col-sm-12">
											<em class="fa fa-info-circle text-light-blue"></em>
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
														<th>Parameter</th>
														<th>Value</th>
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
						<div class="box box-primary">
							<div class="box-header with-border">
								<h3 class="box-title">Cross Validation</h3>
								<div class="btn-tools pull-right">
									<button type="button" class="btn btn-box-tool" data-widget="collapse">
										<i class="fa fa-minus"></i>
									</button>
								</div>
							</div>
							<div class="box-body">
								<c:if test="${fn:length(model.output.crossValidationModels) == 0}">
									<div class="row top10">
										<div class="col-sm-12">
											<em class="fa fa-info-circle text-light-blue"></em>
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
														<th>Models</th>
														<th>Predictions</th>
													</tr>
												</thead>
												<tbody>
													<c:forEach var="i" varStatus="s" begin="0" end="${fn:length(model.output.crossValidationModels)-1}">
														<tr>
															<td><a href="${contextPath}/admin/automl/model/${f:u(projectId)}/${f:u(model.output.crossValidationModels[i].name)}?frameId=${f:u(frameId)}&leaderboardId=${f:u(leaderboardId)}">${f:h(model.output.crossValidationModels[i].name)}</a></td>
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
						<div class="box box-primary">
							<div class="box-header with-border">
								<h3 class="box-title">${f:h(model.output.modelSummary.name)}</h3>
								<div class="btn-tools pull-right">
									<button type="button" class="btn btn-box-tool" data-widget="collapse">
										<i class="fa fa-minus"></i>
									</button>
								</div>
							</div>
							<div class="box-body">
								<c:if test="${model.output.modelSummary.rowcount == 0}">
									<div class="row top10">
										<div class="col-sm-12">
											<em class="fa fa-info-circle text-light-blue"></em>
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
						<c:if test="${model.output.scoringHistory != null}">
						<div class="box box-primary">
							<div class="box-header with-border">
								<h3 class="box-title">${f:h(model.output.scoringHistory.name)}</h3>
								<div class="btn-tools pull-right">
									<button type="button" class="btn btn-box-tool" data-widget="collapse">
										<i class="fa fa-minus"></i>
									</button>
								</div>
							</div>
							<div class="box-body">
								<c:if test="${model.output.scoringHistory.rowcount == 0}">
									<div class="row top10">
										<div class="col-sm-12">
											<em class="fa fa-info-circle text-light-blue"></em>
											<la:message key="labels.list_could_not_find_crud_table" />
										</div>
									</div>
								</c:if>
								<c:if test="${model.output.scoringHistory.rowcount gt 0}">
									<div class="row">
										<div class="col-sm-12">
											<table class="table table-bordered table-striped small">
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
								</c:if>
							</div>
						</div>
						</c:if>
					</div>
					<div class="col-md-6">
						<c:catch var="vie"><c:if test="${model.output.variableImportances==null}"></c:if></c:catch>
						<c:if test="${empty vie}">
						<div class="box box-primary">
							<div class="box-header with-border">
								<h3 class="box-title">${f:h(model.output.variableImportances.name)}</h3>
								<div class="btn-tools pull-right">
									<button type="button" class="btn btn-box-tool" data-widget="collapse">
										<i class="fa fa-minus"></i>
									</button>
								</div>
							</div>
							<div class="box-body">
								<c:if test="${model.output.variableImportances.rowcount == 0}">
									<div class="row top10">
										<div class="col-sm-12">
											<em class="fa fa-info-circle text-light-blue"></em>
											<la:message key="labels.list_could_not_find_crud_table" />
										</div>
									</div>
								</c:if>
								<c:if test="${model.output.variableImportances.rowcount gt 0}">
									<div class="row">
										<div class="col-sm-12">
											<table class="table table-bordered table-striped small">
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
								</c:if>
							</div>
						</div>
						</c:if>
						<c:if test="${model.output.crossValidationMetricsSummary != null}">
						<div class="box box-primary">
							<div class="box-header with-border">
								<h3 class="box-title">${f:h(model.output.crossValidationMetricsSummary.name)}</h3>
								<div class="btn-tools pull-right">
									<button type="button" class="btn btn-box-tool" data-widget="collapse">
										<i class="fa fa-minus"></i>
									</button>
								</div>
							</div>
							<div class="box-body">
								<c:if test="${model.output.crossValidationMetricsSummary.rowcount == 0}">
									<div class="row top10">
										<div class="col-sm-12">
											<em class="fa fa-info-circle text-light-blue"></em>
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
						<div class="box box-primary">
							<div class="box-header with-border">
								<h3 class="box-title">Training Metrics</h3>
								<div class="btn-tools pull-right">
									<button type="button" class="btn btn-box-tool" data-widget="collapse">
										<i class="fa fa-minus"></i>
									</button>
								</div>
							</div>
							<div class="box-body">
								<c:if test="${fn:length(model.output.trainingMetrics.fieldNames) == 0}">
									<div class="row top10">
										<div class="col-sm-12">
											<em class="fa fa-info-circle text-light-blue"></em>
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
														<th>Parameter</th>
														<th>Value</th>
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
						<div class="box box-primary">
							<div class="box-header with-border">
								<h3 class="box-title">Validation Metrics</h3>
								<div class="btn-tools pull-right">
									<button type="button" class="btn btn-box-tool" data-widget="collapse">
										<i class="fa fa-minus"></i>
									</button>
								</div>
							</div>
							<div class="box-body">
								<c:if test="${fn:length(model.output.validationMetrics.fieldNames) == 0}">
									<div class="row top10">
										<div class="col-sm-12">
											<em class="fa fa-info-circle text-light-blue"></em>
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
														<th>Parameter</th>
														<th>Value</th>
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
						<div class="box box-primary">
							<div class="box-header with-border">
								<h3 class="box-title">Cross Validation Metrics</h3>
								<div class="btn-tools pull-right">
									<button type="button" class="btn btn-box-tool" data-widget="collapse">
										<i class="fa fa-minus"></i>
									</button>
								</div>
							</div>
							<div class="box-body">
								<c:if test="${fn:length(model.output.crossValidationMetrics.fieldNames) == 0}">
									<div class="row top10">
										<div class="col-sm-12">
											<em class="fa fa-info-circle text-light-blue"></em>
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
														<th>Parameter</th>
														<th>Value</th>
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
