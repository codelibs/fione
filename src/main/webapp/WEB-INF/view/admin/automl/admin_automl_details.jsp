<%@page pageEncoding="UTF-8" contentType="text/html; charset=UTF-8"%><%@taglib prefix="fi" uri="http://fione.codelibs.org/functions" %><!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title><la:message key="labels.fione_brand_title" /> | <la:message key="labels.automl" /></title>
<jsp:include page="/WEB-INF/view/common/admin/head.jsp"></jsp:include>
<c:if test="${autoReload}"><meta http-equiv="refresh" content="10;URL=${contextPath}/admin/automl/details/${f:u(project.id)}?fid=${f:u(frameId)}&lid=${f:u(leaderboardId)}"/></c:if>
</head>
<body class="hold-transition skin-blue sidebar-mini">
	<div class="wrapper">
		<jsp:include page="/WEB-INF/view/common/admin/header.jsp"></jsp:include>
		<jsp:include page="/WEB-INF/view/common/admin/sidebar.jsp">
			<jsp:param name="menuCategoryType" value="fione" />
			<jsp:param name="menuType" value="automl" />
		</jsp:include>
		<div class="content-wrapper">
			<div class="content-header">
				<div class="container-fluid">
					<div class="row mb-2">
						<div class="col-sm-6">
							<h1>
								<la:message key="labels.automl_project_title" arg0="${f:h(project.name)}" /> <small style="font-size:50%"><la:link
									href="/admin/automl/details/${f:u(project.id)}?fid=${f:u(frameId)}&lid=${f:u(leaderboardId)}"
							><i class="fas fa-redo-alt"></i></la:link></small>
							</h1>
						</div>
						<div class="col-sm-6">
							<ol class="breadcrumb float-sm-right">
								<li class="breadcrumb-item"><la:link href="../list">
									<la:message key="labels.crud_link_list" />
								</la:link></li>
								<li class="breadcrumb-item active">${f:h(project.name)}</li>
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
					</div>
					<div class="col-md-3">
						<div class="card card-outline card-primary">
							<div class="card-header">
								<h3 class="card-title"><la:message key="labels.automl_actions" /></h3>
								<div class="card-tools">
									<button type="button" class="btn btn-tool" data-card-widget="collapse"><i class="fa fa-minus"></i></button>
								</div>
							</div>
							<div class="card-body">
								<div class="row">
									<form method="post" action="${contextPath}/admin/automl/">
									<input type="hidden" name="lastaflute.action.TRANSACTION_TOKEN" value="${f:h(token)}">
									<input type="hidden" name="projectId" value="${f:h(project.id)}">
									<div class="btn-group-vertical" role="group" aria-label="Actions" style="display:block">
										<c:if test="${not empty frameId}">
										<div class="input-group">
											<div class="input-group-prepend" id="basic-addon1"><div class="input-group-text"><i class="fas fa-table"></i></div></div>
											<span class="form-control">${f:h(fi:frameName(frameId))}</span>
										</div>
										</c:if>
										<c:if test="${not empty frameId and leaderboard != null}">
										<div class="input-group">
											<div class="input-group-prepend" id="basic-addon1"><div class="input-group-text"><i class="fas fa-hammer"></i></div></div>
											<span class="form-control">${f:h(leaderboardId)}</span>
										</div>
										</c:if>
										<la:link href="/admin/automl/newdataset/${f:u(project.id)}" styleClass="btn btn-default"><la:message key="labels.automl_upload_dataset" /></la:link>
										<c:if test="${not empty frameId}">
											<la:link href="/admin/automl/setupml/${f:u(project.id)}/${f:u(frameId)}" styleClass="btn btn-default"><la:message key="labels.automl_run_automl" /></la:link>
										</c:if>
										<c:if test="${not empty frameId and leaderboard != null}">
											<la:link href="/admin/automl/prediction/${f:u(project.id)}/${f:u(frameId)}/${f:u(leaderboardId)}" styleClass="btn btn-default"><la:message key="labels.automl_predict_dataset" /></la:link>
										</c:if>

										<div class="btn-group" role="group">
											<button type="button" class="btn btn-default dropdown-toggle" data-toggle="dropdown" aria-haspopup="true"
												aria-expanded="false"><la:message key="labels.automl_options" /></button>
											<ul class="dropdown-menu">
												<li><button type="submit" name="newsession" value="New Session" class="btn btn-link"><la:message key="labels.automl_new_session" /></button></li>
												<li><button type="submit" name="deleteproject" value="Delete Project" class="btn btn-link"><la:message key="labels.automl_delete_project" /></button></li>
											</ul>
										</div>
									</div>
									</form>
								</div>
							</div>
						</div>
						<c:if test="${columnSummaries != null}">
							<div class="card card-outline card-primary">
								<div class="card-header">
									<h3 class="card-title">${f:h(fi:frameName(frameId))}</h3>
									<div class="card-tools">
										<button type="button" class="btn btn-tool" data-card-widget="collapse"><i class="fa fa-minus"></i></button>
									</div>
								</div>
								<div class="card-body">
									<table class="table table-bordered table-striped">
										<tbody>
											<tr>
												<th><la:message key="labels.automl_rows" /></th>
												<td style="text-align:right;">${f:h(columnSummaries.rows)}</td>
											</tr>
											<tr>
												<th><la:message key="labels.automl_columns" /></th>
												<td style="text-align:right;">${f:h(columnSummaries.totalColumnCount)}</td>
											</tr>
											<tr>
												<th><la:message key="labels.automl_compressed_size" /></th>
												<td style="text-align:right;">${fe:formatFileSize(columnSummaries.byteSize)}</td>
											</tr>
										</tbody>
									</table>
								</div>
							</div>
						</c:if>
						<div class="card card-outline card-primary">
							<div class="card-header">
								<h3 class="card-title"><la:message key="labels.automl_datasets" /></h3>
								<div class="card-tools">
									<button type="button" class="btn btn-tool" data-card-widget="collapse"><i class="fa fa-minus"></i></button>
								</div>
							</div>
							<div class="card-body">
								<c:if test="${fn:length(project.dataSets) == 0}">
									<div class="row top10">
										<div class="col-sm-12">
											<em class="fa fa-info-circle text-primary"></em>
											<la:message key="labels.list_could_not_find_crud_table" />
										</div>
									</div>
								</c:if>
								<c:if test="${fn:length(project.dataSets) gt 0}">
									<div class="row">
										<div class="col-sm-12">
											<table class="table table-bordered table-striped">
												<thead>
													<tr>
														<th><la:message key="labels.automl_name" /></th>
														<th style="width:35%"></th>
													</tr>
												</thead>
												<tbody>
													<c:forEach var="data" varStatus="s" items="${project.dataSets}">
														<tr><form method="post" action="${contextPath}/admin/automl/">
														<input type="hidden" name="lastaflute.action.TRANSACTION_TOKEN" value="${f:h(token)}">
														<input type="hidden" name="projectId" value="${f:h(project.id)}">
														<input type="hidden" name="dataSetId" value="${f:h(data.id)}">
														<input type="hidden" name="frameId" value="${f:h(frameId)}">
														<input type="hidden" name="leaderboardId" value="${f:h(leaderboardId)}">
															<td class="text-break">
															<c:choose>
															<c:when test="${data.type == 'train' and data.schema != null}">
															<button type="submit" name="datasettype" value="test" class="btn btn-link" style="padding:0;"><i class="fas fa-chart-area" title="<la:message key="labels.automl_training_data" />"></i></button>
															</c:when>
															<c:when test="${data.type == 'test'}">
															<button type="submit" name="datasettype" value="train" class="btn btn-link" style="padding:0;"><i class="fas fa-chart-bar" title="<la:message key="labels.automl_test_data" />"></i></button>
															</c:when>
															<c:when test="${data.type == 'predict'}">
															<button type="submit" name="datasettype" value="train" class="btn btn-link" style="padding:0;"><i class="fas fa-chart-line" title="<la:message key="labels.automl_predicted_data" />"></i></button>
															</c:when>
															<c:otherwise><em class="fas fa-question" style="color:#337ab7;" title="<la:message key="labels.automl_unknown" />"></em></c:otherwise>
															</c:choose>
															${f:h(data.name)}</td>
															<td class="text-center">
															<c:if test="${data.schema != null}">
															<la:link href="/admin/automl/newframe/${f:u(project.id)}/${f:u(data.id)}"><i class="fas fa-table" title="<la:message key="labels.automl_create_frame" />"></i></la:link>
															</c:if>
															<c:if test="${data.schema == null}">
															<button type="submit" name="loaddataset" value="load" class="btn btn-link" style="padding:0;"><i class="fas fa-sync" title="<la:message key="labels.automl_load_schema" />"></i></button>
															</c:if>
															<button type="submit" name="downloaddataset" value="download" class="btn btn-link" style="padding:0;"><i class="fas fa-download" title="<la:message key="labels.automl_download" />"></i></button>
															<button type="submit" name="deletedataset" value="Delete" class="btn btn-link" style="padding:0;"><i class="fas fa-trash-alt" title="<la:message key="labels.automl_delete" />"></i></button>
															</td>
														</form></tr>
													</c:forEach>
												</tbody>
											</table>
										</div>
									</div>
								</c:if>
							</div>
						</div>
						<div class="card card-outline card-primary">
							<div class="card-header">
								<h3 class="card-title"><la:message key="labels.automl_frames" /></h3>
								<div class="card-tools">
									<button type="button" class="btn btn-tool" data-card-widget="collapse"><i class="fa fa-minus"></i></button>
								</div>
							</div>
							<div class="card-body">
								<c:if test="${fn:length(project.frameIds) == 0}">
									<div class="row top10">
										<div class="col-sm-12">
											<em class="fa fa-info-circle text-primary"></em>
											<la:message key="labels.list_could_not_find_crud_table" />
										</div>
									</div>
								</c:if>
								<c:if test="${fn:length(project.frameIds) gt 0}">
									<div class="row">
										<div class="col-sm-12">
											<table class="table table-bordered table-striped">
												<thead>
													<tr>
														<th><la:message key="labels.automl_name" /></th>
														<th style="width:35%"></th>
													</tr>
												</thead>
												<tbody>
													<c:forEach var="data" varStatus="s" items="${project.frameIds}">
														<tr><form method="post" action="${contextPath}/admin/automl/">
														<input type="hidden" name="lastaflute.action.TRANSACTION_TOKEN" value="${f:h(token)}">
														<input type="hidden" name="projectId" value="${f:h(project.id)}">
														<input type="hidden" name="frameId" value="${f:h(frameId)}">
														<input type="hidden" name="leaderboardId" value="${f:h(leaderboardId)}">
															<td>${f:h(fi:frameName(data))}</td>
															<td class="text-center">
															<c:if test="${frameId == data}"><i class="far fa-check-square" style="color:#3c8dbc;"></i></c:if>
															<c:if test="${frameId != data}"><la:link href="/admin/automl/details/${f:u(project.id)}?fid=${f:u(data)}&lid=${f:u(leaderboardId)}"><i class="far fa-square"></i></la:link></c:if>
															<la:link href="/admin/automl/dataview/${f:u(project.id)}?fid=${f:u(data)}&lid=${f:u(leaderboardId)}"><i class="far fa-eye"></i></la:link>
															<button type="submit" name="deleteframe" value="Delete" class="btn btn-link" style="padding:0;"><i class="fas fa-trash-alt" title="<la:message key="labels.automl_delete" />"></i></button>
															</td>
														</form></tr>
													</c:forEach>
												</tbody>
											</table>
										</div>
									</div>
								</c:if>
							</div>
						</div>
					</div>
					<div class="col-md-9">
						<div class="card card-outline card-primary">
							<div class="card-header">
								<h3 class="card-title"><la:message key="labels.automl_jobs" /></h3>
								<div class="card-tools">
									<button type="button" class="btn btn-tool" data-card-widget="collapse">
										<i class="fa fa-minus"></i>
									</button>
									<button type="button" class="btn btn-box-tool dropdown-toggle" data-toggle="dropdown" aria-expanded="true">
										<i class="fas fa-th-list"></i>
									</button>
									<ul class="dropdown-menu" role="menu">
										<li><form method="post" action="${contextPath}/admin/automl/">
										<input type="hidden" name="lastaflute.action.TRANSACTION_TOKEN" value="${f:h(token)}">
										<input type="hidden" name="projectId" value="${f:h(project.id)}">
										<input type="hidden" name="frameId" value="${f:h(frameId)}">
										<input type="hidden" name="leaderboardId" value="${f:h(leaderboardId)}">
										<input type="hidden" name="jobId" value="_all_">
										<button type="submit" name="deletealljobs" value="Delete All" class="btn btn-link"><la:message key="labels.automl_delete_all" /></button>
										</form></li>
									</ul>
								</div>
							</div>
							<div class="card-body">
								<%-- List --%>
								<c:if test="${fn:length(project.jobs) == 0}">
									<div class="row top10">
										<div class="col-sm-12">
											<em class="fa fa-info-circle text-primary"></em>
											<la:message key="labels.list_could_not_find_crud_table" />
										</div>
									</div>
								</c:if>
								<c:if test="${fn:length(project.jobs) gt 0}">
									<div class="row">
										<div class="col-sm-12">
											<table class="table table-bordered table-striped small">
												<thead>
													<tr>
														<th style="width:35%"><la:message key="labels.automl_destination" /></th>
														<th style="width:15%" class="text-center"><la:message key="labels.automl_start_time" /></th>
														<th style="width:15%" class="text-center"><la:message key="labels.automl_end_time" /></th>
														<th style="width:15%" class="text-center"><la:message key="labels.automl_run_time" /></th>
														<th style="width:15%" class="text-center"><la:message key="labels.automl_status" /></th>
														<th style="width:5%" class="text-center">&nbsp;</th>
													</tr>
												</thead>
												<tbody>
													<c:forEach var="data" varStatus="s" items="${project.jobs}">
														<tr><form method="post" action="${contextPath}/admin/automl/">
														<input type="hidden" name="lastaflute.action.TRANSACTION_TOKEN" value="${f:h(token)}">
														<input type="hidden" name="projectId" value="${f:h(project.id)}">
														<input type="hidden" name="jobId" value="${f:h(data.key.name)}">
														<input type="hidden" name="frameId" value="${f:h(frameId)}">
														<input type="hidden" name="leaderboardId" value="${f:h(leaderboardId)}">
															<td><i class="fas fa-${f:u(data.iconType)}"></i> <c:choose>
																	<c:when test="${data.iconType == 'hammer'}">
																		<la:link
																			href="/admin/automl/details/${f:u(project.id)}?fid=${f:u(frameId)}&lid=${f:u(data.dest.name)}"
																		>${f:h(data.dest.name)}</la:link>
																		<c:if test="${data.status == 'RUNNING'}"><br><i class="fas fa-circle-notch fa-spin"></i>${f:h(data.progressMsg)}</c:if>
																	</c:when>
																	<c:otherwise>${f:h(data.dest.name)}</c:otherwise>
																</c:choose></td>
															<td class="text-center"><fmt:formatDate value="${fe:date(data.startTime)}" type="BOTH" /></td>
															<td class="text-center"><c:if test="${data.status == 'RUNNING'}">-</c:if> <c:if
																	test="${data.status != 'RUNNING'}"
																>
																	<fmt:formatDate value="${fe:date(data.startTime+data.msec)}" type="BOTH" />
																</c:if></td>
															<td class="text-center"><c:if test="${data.status == 'RUNNING'}">-</c:if> <c:if
																	test="${data.status != 'RUNNING'}"
																>${fe:formatDuration(data.msec)}</c:if></td>
															<td class="text-center"><c:choose>
																	<c:when test="${data.status == 'CANCELLED' }">
																		<i class="fas fa-ban"></i>
																	</c:when>
																	<c:when test="${data.status == 'FAILED' }">
																		<i class="fas fa-times"></i>
																	</c:when>
																	<c:when test="${data.status == 'RUNNING' }">
																		<div class="progress" style="background-color:#999;">
																			<div class="progress-bar" role="progressbar" aria-valuenow="${f:h(data.progressInt)}" aria-valuemin="0" aria-valuemax="100"
																				style="width:${f:h(data.progressInt)}%;"><i class="fas fa-running" title="${f:h(data.progressInt)}%"></i></div>
																		</div>
																	</c:when>
																	<c:when test="${data.status == 'DONE' }">
																		<i class="fas fa-check"></i>
																	</c:when>
																	<c:otherwise>
																		<i class="fas fa-question"></i>
																	</c:otherwise>
																</c:choose></td>
															<td class="text-center">
																<button type="submit" name="deletejob" value="Delete" class="btn btn-link" style="padding:0;"><i class="fas fa-trash-alt" title="<la:message key="labels.automl_delete" />"></i></button>
															</td>
														</form></tr>
													</c:forEach>
												</tbody>
											</table>
										</div>
									</div>
								</c:if>
							</div>
						</div>
						<c:if test="${columnSummaries != null}">
							<div class="card card-outline card-primary">
								<div class="card-header">
									<h3 class="card-title"><la:message key="labels.automl_column_summaries" arg0="${f:h(fi:frameName(frameId))}" /></h3>
									<div class="card-tools">
										<button type="button" class="btn btn-tool" data-card-widget="collapse">
											<i class="fa fa-minus"></i>
										</button>
									</div>
								</div>
								<div class="card-body">
									<%-- List --%>
									<div class="row">
										<div class="col-sm-12">
											<table class="table table-bordered table-striped small">
												<thead>
													<tr>
														<th><la:message key="labels.automl_label" /></th>
														<th><la:message key="labels.automl_type" /></th>
														<th><la:message key="labels.automl_missing" /></th>
														<th><la:message key="labels.automl_zeros" /></th>
														<th><la:message key="labels.automl_posinf" /></th>
														<th><la:message key="labels.automl_neginf" /></th>
														<th><la:message key="labels.automl_min" /></th>
														<th><la:message key="labels.automl_max" /></th>
														<th><la:message key="labels.automl_mean" /></th>
														<th><la:message key="labels.automl_sigma" /></th>
														<th><la:message key="labels.automl_cardinality" /></th>
													</tr>
												</thead>
												<tbody>
													<c:forEach var="data" varStatus="s" items="${columnSummaries.columns}">
														<tr>
															<td>${f:h(data.label)}</td>
															<td>${f:h(data.type)}</td>
															<td>${f:h(data.missingCount)}</td>
															<td>${f:h(data.zeroCount)}</td>
															<td>${f:h(data.positiveInfinityCount)}</td>
															<td>${f:h(data.negativeInfinityCount)}</td>
															<td><fmt:formatNumber value="${data.mins[0]}" maxFractionDigits="6" /></td>
															<td><fmt:formatNumber value="${data.maxs[0]}" maxFractionDigits="6" /></td>
															<td><fmt:formatNumber value="${data.mean}" maxFractionDigits="6" /></td>
															<td><fmt:formatNumber value="${data.sigma}" maxFractionDigits="6" /></td>
															<td>${f:h(data.domainCardinality)}</td>
														</tr>
													</c:forEach>
												</tbody>
											</table>
										</div>
									</div>
								</div>
							</div>
						</c:if>
						<c:if test="${leaderboard != null}">
							<div class="card card-outline card-primary">
								<div class="card-header">
									<h3 class="card-title"><la:message key="labels.automl_model_summaries" arg0="${f:h(leaderboard.projectName)}" /></h3>
									<div class="card-tools">
										<button type="button" class="btn btn-tool" data-card-widget="collapse">
											<i class="fa fa-minus"></i>
										</button>
										<button type="button" class="btn btn-box-tool dropdown-toggle" data-toggle="dropdown" aria-expanded="true">
											<i class="fas fa-th-list"></i>
										</button>
										<ul class="dropdown-menu" role="menu">
											<li><form method="post" action="${contextPath}/admin/automl/">
											<input type="hidden" name="lastaflute.action.TRANSACTION_TOKEN" value="${f:h(token)}">
											<input type="hidden" name="projectId" value="${f:h(project.id)}">
											<input type="hidden" name="frameId" value="${f:h(frameId)}">
											<input type="hidden" name="leaderboardId" value="${f:h(leaderboardId)}">
											<button type="submit" name="exportallmodels" value="Export All" class="btn btn-link"><la:message key="labels.automl_export_all" /></button>
											</form></li>
										</ul>
									</div>
								</div>
								<div class="card-body">
									<%-- List --%>
									<c:if test="${fn:length(leaderboard.models) == 0}">
										<div class="row top10">
											<div class="col-sm-12">
												<em class="fa fa-info-circle text-primary"></em>
												<la:message key="labels.list_could_not_find_crud_table" />
											</div>
										</div>
									</c:if>
									<c:if test="${fn:length(leaderboard.models) gt 0}">
										<div class="row">
											<div class="col-sm-12">
												<table class="table table-bordered table-striped small">
													<thead>
														<tr>
															<c:forEach var="data" varStatus="s" items="${leaderboard.columnNames}">
																<th>${f:h(data)}</th>
															</c:forEach>
														</tr>
													</thead>
													<tbody>
														<c:forEach var="data" varStatus="s" items="${leaderboard.models}">
															<tr>
																<c:forEach var="data" varStatus="x" items="${leaderboard.row}">
																	<c:if test="${fn:contains(data, 'AutoML')}"><td><a href="${contextPath}/admin/automl/model/${f:u(project.id)}/${f:u(data)}?fid=${f:u(frameId)}&lid=${f:u(leaderboardId)}">${f:h(data)}</a></td></c:if>
																	<c:if test="${not fn:contains(data, 'AutoML')}"><td>${f:h(data)}</td></c:if>
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
				</div>
			</section>
		</div>
		<jsp:include page="/WEB-INF/view/common/admin/footer.jsp"></jsp:include>
	</div>
	<jsp:include page="/WEB-INF/view/common/admin/foot.jsp"></jsp:include>
</body>
</html>
