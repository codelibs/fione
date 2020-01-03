<%@page pageEncoding="UTF-8" contentType="text/html; charset=UTF-8"%><!DOCTYPE html>
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
				<h1>Project: ${f:h(project.name)}</i></h1>
				<ol class="breadcrumb">
					<li><la:link href="../list">
							<la:message key="labels.crud_link_list" />
						</la:link></li>
					<li class="active">${f:h(project.name)}</li>
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
					<div class="col-md-3">
						<div class="box box-primary">
							<div class="box-header with-border">
								<h3 class="box-title">Data</h3>
								<div class="btn-group pull-right">
									<la:link href="/admin/automl/newdataset/${f:u(project.id)}"
										styleClass="btn btn-success btn-xs ${f:h(editableClass)}"
									><em class="fa fa-plus"></em></la:link>
								</div>
							</div>
							<div class="box-body">
								<c:if test="${fn:length(project.dataSets) == 0}">
									<div class="row top10">
										<div class="col-sm-12">
											<em class="fa fa-info-circle text-light-blue"></em>
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
														<th class="col-sm-4 text-center">Action</th>
													</tr>
												</thead>
												<tbody>
													<c:forEach var="data" varStatus="s" items="${project.dataSets}">
														<tr><form method="post" action="${contextPath}/admin/automl/">
														<input type="hidden" name="lastaflute.action.TRANSACTION_TOKEN" value="${f:u(token)}">
														<input type="hidden" name="projectId" value="${f:u(project.id)}">
														<input type="hidden" name="dataSetId" value="${f:u(data.id)}">
															<td>${f:h(data.name)}</td>
															<td class="text-center">
															<c:if test="${data.schema != null}">
															<la:link href="/admin/automl/newframe/${f:u(project.id)}/${f:u(data.id)}"><i class="fas fa-table"></i></la:link>
															</c:if>
															<c:if test="${data.schema == null}">
															<button type="submit" name="loaddataset" value="load" class="btn btn-link" style="padding:0;"><i class="fas fa-sync"></i></button>
															</c:if>
															<button type="submit" name="downloaddataset" value="download" class="btn btn-link" style="padding:0;"><i class="fas fa-download"></i></button>
															<button type="submit" name="deletedataset" value="Delete" class="btn btn-link" style="padding:0;"><i class="fas fa-trash-alt"></i></button>
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
						<div class="box box-primary">
							<div class="box-header with-border">
								<h3 class="box-title">Frames</h3>
								<div class="btn-group pull-right"></div>
							</div>
							<div class="box-body">
								<c:if test="${fn:length(project.frameIds) == 0}">
									<div class="row top10">
										<div class="col-sm-12">
											<em class="fa fa-info-circle text-light-blue"></em>
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
														<th class="col-sm-3 text-center">Action</th>
													</tr>
												</thead>
												<tbody>
													<c:forEach var="frameId" varStatus="s" items="${project.frameIds}">
														<tr
															data-href="${contextPath}/admin/automl/details/${f:u(project.id)}?frameId=${f:u(frameId)}&leaderboardId=${f:u(leaderboardId)}"
														>
															<td>${f:h(frameId)}</td>
															<td class="text-center"><la:link href="/admin/automl/deleteframe/${f:u(project.id)}/${f:u(frameId)}">
																	<i class="fas fa-trash-alt"></i>
																</la:link></td>
														</tr>
													</c:forEach>
												</tbody>
											</table>
										</div>
									</div>
								</c:if>
							</div>
						</div>
						<c:if test="${columnSummaries != null}">
							<div class="box box-primary">
								<div class="box-header with-border">
									<h3 class="box-title">Columns</h3>
									<div class="btn-group pull-right"></div>
								</div>
								<div class="box-body">
									<table class="table table-bordered table-striped">
										<thead>
											<tr>
												<th>Label</th>
												<th>Type</th>
											</tr>
										</thead>
										<tbody>
											<c:forEach var="data" varStatus="s" items="${columnSummaries.columns}">
												<tr>
													<td>${f:h(data.label)}</td>
													<td>${f:h(data.type)}</td>
												</tr>
											</c:forEach>
										</tbody>
									</table>
								</div>
							</div>
						</c:if>
					</div>
					<div class="col-md-9">
						<div class="box box-primary">
							<div class="box-header with-border">
								<h3 class="box-title">Jobs</h3>
								<div class="btn-group pull-right">
									<button type="button" class="btn btn-box-tool" data-widget="collapse">
										<i class="fa fa-minus"></i>
									</button>
									<button type="button" class="btn btn-box-tool dropdown-toggle" data-toggle="dropdown" aria-expanded="true">
										<i class="fas fa-th-list"></i>
									</button>
									<ul class="dropdown-menu" role="menu">
										<c:if test="${not empty frameId}">
											<li><la:link href="/admin/automl/setupml/${f:u(project.id)}/${f:u(frameId)}">Run AutoML</la:link></li>
										</c:if>
										<c:if test="${not empty frameId and not empty leaderboardId}">
											<li><la:link href="/admin/automl/prediction/${f:u(project.id)}/${f:u(frameId)}/${f:u(leaderboardId)}">Prediction</la:link></li>
										</c:if>
										<li><a href="#">Delete All</a></li>
									</ul>
								</div>
							</div>
							<div class="box-body">
								<%-- List --%>
								<c:if test="${fn:length(project.jobs) == 0}">
									<div class="row top10">
										<div class="col-sm-12">
											<em class="fa fa-info-circle text-light-blue"></em>
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
														<th>Destination</th>
														<th class="col-sm-2 text-center">Start Time</th>
														<th class="col-sm-2 text-center">End Time</th>
														<th class="col-sm-2 text-center">Run Time</th>
														<th class="col-sm-1 text-center">Status</th>
														<th class="col-sm-1 text-center">&nbsp;</th>
													</tr>
												</thead>
												<tbody>
													<c:forEach var="data" varStatus="s" items="${project.jobs}">
														<tr>
															<td><i class="fas fa-${f:u(data.iconType)}"></i> <c:choose>
																	<c:when test="${data.iconType == 'hammer'}">
																		<la:link
																			href="/admin/automl/details/${f:u(project.id)}?frameId=${f:u(frameId)}&leaderboardId=${f:u(data.dest.name)}"
																		>${f:h(data.dest.name)}</la:link>
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
																		<div class="progress">
																			<div class="progress-bar" role="progressbar" aria-valuenow="${f:h(data.progressInt)}" aria-valuemin="0" aria-valuemax="100"
																				style="width:${f:h(data.progressInt)}%;"><i class="fas fa-running"></i></div>
																		</div>
																	</c:when>
																	<c:when test="${data.status == 'DONE' }">
																		<i class="fas fa-check"></i>
																	</c:when>
																	<c:otherwise>
																		<i class="fas fa-question"></i>
																	</c:otherwise>
																</c:choose></td>
															<td class="text-center"><la:link
																	href="/admin/automl/deletejob/${f:u(project.id)}/${f:u(data.key.name)}"
																>
																	<i class="fas fa-trash-alt"></i>
																</la:link></td>
														</tr>
													</c:forEach>
												</tbody>
											</table>
										</div>
									</div>
								</c:if>
							</div>
						</div>
						<c:if test="${columnSummaries != null}">
							<div class="box box-primary">
								<div class="box-header with-border">
									<h3 class="box-title">Column Summaries in ${f:h(frameId)}</h3>
									<div class="btn-group pull-right">
										<button type="button" class="btn btn-box-tool" data-widget="collapse">
											<i class="fa fa-minus"></i>
										</button>
									</div>
								</div>
								<div class="box-body">
									<%-- List --%>
									<div class="row">
										<div class="col-sm-12">
											<table class="table table-bordered table-striped small">
												<thead>
													<tr>
														<th>Label</th>
														<th>Missing</th>
														<th>Zeros</th>
														<th>+Inf.</th>
														<th>-Inf.</th>
														<th>min</th>
														<th>max</th>
														<th>mean</th>
														<th>sigma</th>
														<th>Card.</th>
													</tr>
												</thead>
												<tbody>
													<c:forEach var="data" varStatus="s" items="${columnSummaries.columns}">
														<tr>
															<td>${f:h(data.label)}</td>
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
							<div class="box box-primary">
								<div class="box-header with-border">
									<h3 class="box-title">Models in ${f:h(leaderboard.projectName)}</h3>
									<div class="btn-group pull-right">
										<button type="button" class="btn btn-box-tool" data-widget="collapse">
											<i class="fa fa-minus"></i>
										</button>
									</div>
								</div>
								<div class="box-body">
									<%-- List --%>
									<c:if test="${fn:length(leaderboard.models) == 0}">
										<div class="row top10">
											<div class="col-sm-12">
												<em class="fa fa-info-circle text-light-blue"></em>
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
																	<td>${f:h(data)}</td>
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
