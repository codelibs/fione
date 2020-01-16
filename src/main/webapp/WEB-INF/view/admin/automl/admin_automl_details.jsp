<%@page pageEncoding="UTF-8" contentType="text/html; charset=UTF-8"%><%@taglib prefix="fi" uri="http://fione.codelibs.org/functions" %><!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title><la:message key="labels.admin_brand_title" /> | <la:message key="labels.automl" /></title>
<jsp:include page="/WEB-INF/view/common/admin/head.jsp"></jsp:include>
<c:if test="${autoReload}"><meta http-equiv="refresh" content="10;URL=${contextPath}/admin/automl/details/${f:u(project.id)}?frameId=${f:u(frameId)}&leaderboardId=${f:u(leaderboardId)}"/></c:if>
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
				<h1>
					Project: ${f:h(project.name)} <small><la:link
							href="/admin/automl/details/${f:u(project.id)}?frameId=${f:u(frameId)}&leaderboardId=${f:u(leaderboardId)}"
						><i class="fas fa-redo-alt"></i></la:link></small>
				</h1>
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
								<h3 class="box-title">Actions</h3>
								<div class="box-tools pull-right">
									<button type="button" class="btn btn-box-tool" data-widget="collapse"><i class="fa fa-minus"></i></button>
								</div>
							</div>
							<div class="box-body">
								<div class="row">
									<form method="post" action="${contextPath}/admin/automl/">
									<input type="hidden" name="lastaflute.action.TRANSACTION_TOKEN" value="${f:h(token)}">
									<input type="hidden" name="projectId" value="${f:h(project.id)}">
									<div class="btn-group-vertical col-sm-12" role="group" aria-label="Actions">
										<c:if test="${not empty frameId}">
										<div class="input-group">
											<span class="input-group-addon" id="basic-addon1"><i class="fas fa-table"></i></span>
											<span class="form-control">${f:h(fi:frameName(frameId))}</span>
										</div>
										</c:if>
										<c:if test="${not empty frameId and leaderboard != null}">
										<div class="input-group">
											<span class="input-group-addon" id="basic-addon1"><i class="fas fa-hammer"></i></span>
											<span class="form-control">${f:h(leaderboardId)}</span>
										</div>
										</c:if>
										<la:link href="/admin/automl/newdataset/${f:u(project.id)}" styleClass="btn btn-default">Upload DataSet</la:link>
										<c:if test="${not empty frameId}">
											<la:link href="/admin/automl/setupml/${f:u(project.id)}/${f:u(frameId)}" styleClass="btn btn-default">Run AutoML</la:link>
										</c:if>
										<c:if test="${not empty frameId and leaderboard != null}">
											<la:link href="/admin/automl/prediction/${f:u(project.id)}/${f:u(frameId)}/${f:u(leaderboardId)}" styleClass="btn btn-default">Predict DataSet</la:link>
										</c:if>

										<div class="btn-group" role="group">
											<button type="button" class="btn btn-default dropdown-toggle" data-toggle="dropdown" aria-haspopup="true"
												aria-expanded="false">Options <i class="fas fa-caret-down"></i></button>
											<ul class="dropdown-menu">
												<li><button type="submit" name="newsession" value="New Session" class="btn btn-link">New Session</button></li>
												<li><button type="submit" name="deleteproject" value="Delete Project" class="btn btn-link">Delete Project</button></li>
											</ul>
										</div>
									</div>
									</form>
								</div>
							</div>
						</div>
						<c:if test="${columnSummaries != null}">
							<div class="box box-primary">
								<div class="box-header with-border">
									<h3 class="box-title">${f:h(fi:frameName(frameId))}</h3>
									<div class="box-tools pull-right">
										<button type="button" class="btn btn-box-tool" data-widget="collapse"><i class="fa fa-minus"></i></button>
									</div>
								</div>
								<div class="box-body">
									<table class="table table-bordered table-striped">
										<tbody>
											<tr>
												<th>Rows</th>
												<td style="text-align:right;">${f:h(columnSummaries.rows)}</td>
											</tr>
											<tr>
												<th>Columns</th>
												<td style="text-align:right;">${f:h(columnSummaries.totalColumnCount)}</td>
											</tr>
											<tr>
												<th>Compressed Size</th>
												<td style="text-align:right;">${fe:formatFileSize(columnSummaries.byteSize)}</td>
											</tr>
										</tbody>
									</table>
								</div>
							</div>
						</c:if>
						<div class="box box-primary">
							<div class="box-header with-border">
								<h3 class="box-title">DataSets</h3>
								<div class="box-tools pull-right">
									<button type="button" class="btn btn-box-tool" data-widget="collapse"><i class="fa fa-minus"></i></button>
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
														<input type="hidden" name="lastaflute.action.TRANSACTION_TOKEN" value="${f:h(token)}">
														<input type="hidden" name="projectId" value="${f:h(project.id)}">
														<input type="hidden" name="dataSetId" value="${f:h(data.id)}">
														<input type="hidden" name="frameId" value="${f:h(frameId)}">
														<input type="hidden" name="leaderboardId" value="${f:h(leaderboardId)}">
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
								<div class="box-tools pull-right">
									<button type="button" class="btn btn-box-tool" data-widget="collapse"><i class="fa fa-minus"></i></button>
								</div>
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
													<c:forEach var="data" varStatus="s" items="${project.frameIds}">
														<tr><form method="post" action="${contextPath}/admin/automl/">
														<input type="hidden" name="lastaflute.action.TRANSACTION_TOKEN" value="${f:h(token)}">
														<input type="hidden" name="projectId" value="${f:h(project.id)}">
														<input type="hidden" name="frameId" value="${f:h(frameId)}">
														<input type="hidden" name="leaderboardId" value="${f:h(leaderboardId)}">
															<td>${f:h(fi:frameName(data))}</td>
															<td class="text-center">
															<c:if test="${frameId == data}"><i class="far fa-check-square" style="color:#3c8dbc;"></i></c:if>
															<c:if test="${frameId != data}"><la:link href="/admin/automl/details/${f:u(project.id)}?frameId=${f:u(data)}&leaderboardId=${f:u(leaderboardId)}"><i class="far fa-square"></i></la:link></c:if>
															<button type="submit" name="deleteframe" value="Delete" class="btn btn-link" style="padding:0;"><i class="fas fa-trash-alt"></i></button>
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
						<div class="box box-primary">
							<div class="box-header with-border">
								<h3 class="box-title">Jobs</h3>
								<div class="box-tools pull-right">
									<button type="button" class="btn btn-box-tool" data-widget="collapse">
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
										<button type="submit" name="deletealljobs" value="Delete All" class="btn btn-link">Delete All</button>
										</form></li>
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
														<tr><form method="post" action="${contextPath}/admin/automl/">
														<input type="hidden" name="lastaflute.action.TRANSACTION_TOKEN" value="${f:h(token)}">
														<input type="hidden" name="projectId" value="${f:h(project.id)}">
														<input type="hidden" name="jobId" value="${f:h(data.key.name)}">
														<input type="hidden" name="frameId" value="${f:h(frameId)}">
														<input type="hidden" name="leaderboardId" value="${f:h(leaderboardId)}">
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
															<td class="text-center">
																<button type="submit" name="deletejob" value="Delete" class="btn btn-link" style="padding:0;"><i class="fas fa-trash-alt"></i></button>
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
							<div class="box box-primary">
								<div class="box-header with-border">
									<h3 class="box-title">Column Summaries in ${f:h(fi:frameName(frameId))}</h3>
									<div class="box-tools pull-right">
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
														<th>Type</th>
														<th>Missing</th>
														<th>Zeros</th>
														<th>+Inf.</th>
														<th>-Inf.</th>
														<th>Min</th>
														<th>Max</th>
														<th>Mean</th>
														<th>Sigma</th>
														<th>Card.</th>
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
						<c:if test="${frameData != null}">
							<div class="box box-primary">
								<div class="box-header with-border">
									<h3 class="box-title">Data in ${f:h(fi:frameName(frameId))}</h3>
									<div class="box-tools pull-right">
										<span class="label label-info">${f:h(frameData.rows)} Data, ${f:h(frameData.numColumns)} Columns</span>
										<c:if test="${frameData.columnOffset > 0}"><a href="${contextPath}/admin/automl/details/${f:u(project.id)}/?frameId=${f:u(frameId)}&leaderboardId=${f:u(leaderboardId)}&data.row_offset=${f:u(frameData.rowOffset)}&data.column_offset=${f:u(frameData.columnOffset-10)}" class="btn btn-box-tool"><i class="fas fa-arrow-left"></i></a></c:if>
										<c:if test="${frameData.columnOffset + 10 < frameData.numColumns}"><a href="${contextPath}/admin/automl/details/${f:u(project.id)}/?frameId=${f:u(frameId)}&leaderboardId=${f:u(leaderboardId)}&data.row_offset=${f:u(frameData.rowOffset)}&data.column_offset=${f:u(frameData.columnOffset+10)}" class="btn btn-box-tool"><i class="fas fa-arrow-right"></i></a></c:if>
										<c:if test="${frameData.rowOffset > 0}"><a href="${contextPath}/admin/automl/details/${f:u(project.id)}/?frameId=${f:u(frameId)}&leaderboardId=${f:u(leaderboardId)}&data.row_offset=${f:u(frameData.rowOffset-10)}&data.column_offset=${f:u(frameData.columnOffset)}" class="btn btn-box-tool"><i class="fas fa-arrow-up"></i></a></c:if>
										<c:if test="${frameData.rowOffset + 10 < frameData.rows}"><a href="${contextPath}/admin/automl/details/${f:u(project.id)}/?frameId=${f:u(frameId)}&leaderboardId=${f:u(leaderboardId)}&data.row_offset=${f:u(frameData.rowOffset+10)}&data.column_offset=${f:u(frameData.columnOffset)}" class="btn btn-box-tool"><i class="fas fa-arrow-down"></i></a></c:if>
										<button type="button" class="btn btn-box-tool" data-widget="collapse">
											<i class="fa fa-minus"></i>
										</button>
									</div>
								</div>
								<div class="box-body">
									<%-- List --%>
									<c:if test="${frameData.rows == 0}">
										<div class="row top10">
											<div class="col-sm-12">
												<em class="fa fa-info-circle text-light-blue"></em>
												<la:message key="labels.list_could_not_find_crud_table" />
											</div>
										</div>
									</c:if>
									<c:if test="${frameData.rows gt 0}">
										<div class="row">
											<div class="col-sm-12">
												<table class="table table-bordered table-striped small">
													<thead>
														<tr>
															<c:forEach var="data" varStatus="s" items="${frameData.columnNames}">
																<th>${f:h(data)}</th>
															</c:forEach>
														</tr>
													</thead>
													<tbody>
														<c:forEach var="data" varStatus="s" begin="0" end="${frameData.rowSize}">
															<tr>
																<c:forEach var="data" varStatus="x" items="${frameData.row}">
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
						<c:if test="${leaderboard != null}">
							<div class="box box-primary">
								<div class="box-header with-border">
									<h3 class="box-title">Models in ${f:h(leaderboard.projectName)}</h3>
									<div class="box-tools pull-right">
										<button type="button" class="btn btn-box-tool" data-widget="collapse">
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
											<button type="submit" name="exportallmodels" value="Export All" class="btn btn-link">Export All</button>
											</form></li>
										</ul>
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
																	<c:if test="${fn:contains(data, 'AutoML')}"><td><a href="${contextPath}/admin/automl/model/${f:u(project.id)}/${f:u(data)}?frameId=${f:u(frameId)}&leaderboardId=${f:u(leaderboardId)}">${f:h(data)}</a></td></c:if>
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
