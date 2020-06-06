<%@page pageEncoding="UTF-8" contentType="text/html; charset=UTF-8"%><%@taglib prefix="fi" uri="http://fione.codelibs.org/functions" %><!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title><la:message key="labels.fione_brand_title" /> | <la:message key="labels.automl" /></title>
<jsp:include page="/WEB-INF/view/common/admin/head.jsp"></jsp:include>
<c:if test="${autoReload}"><meta http-equiv="refresh" content="10;URL=${contextPath}/admin/automl/job/${f:u(project.id)}?fid=${f:u(frameId)}&lid=${f:u(leaderboardId)}"/></c:if>
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
							<h1>
								<la:message key="labels.automl_project_title" arg0="${f:h(project.name)}" /> <small style="font-size:50%"><la:link
									href="/admin/automl/job/${f:u(project.id)}?fid=${f:u(frameId)}&lid=${f:u(leaderboardId)}"
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
						<div class="card card-outline">
							<div class="card-body p-2">
								<jsp:include page="/WEB-INF/view/admin/automl/admin_automl_toolbar.jsp"></jsp:include>
							</div>
						</div>
					</div>
					<div class="col-md-3">
						<jsp:include page="/WEB-INF/view/admin/automl/admin_automl_sideview.jsp"></jsp:include>
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
																	<c:when test="${data.iconType == 'hammer' and fn:contains(data.dest.name, '@@')}">
																		<la:link
																			href="/admin/automl/job/${f:u(project.id)}?fid=${f:u(frameId)}&lid=${f:u(data.dest.name)}"
																		>${f:h(fi:jobName(data.dest.name))}</la:link>
																		<c:if test="${data.status == 'RUNNING'}"><br><i class="fas fa-circle-notch fa-spin"></i>${f:h(data.progressMsg)}</c:if>
																	</c:when>
																	<c:otherwise>${f:h(fi:jobName(data.dest.name))}</c:otherwise>
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
																		<button type="button" class="btn btn-link" data-toggle="modal"
																			data-target="#error${f:h(data.key.name)}">
																			<i class="fas fa-times text-danger"></i>
																		</button>
																		<div class="modal fade" id="error${f:h(data.key.name)}" tabindex="-1" role="dialog"
																			aria-labelledby="error${f:h(data.key.name)}Label" aria-hidden="true">
																			<div class="modal-dialog modal-dialog-scrollable">
																				<div class="modal-content">
																					<div class="modal-body text-left">
																						<pre>${f:h(data.exception)}</pre>
																					</div>
																					<div class="modal-footer">
																						<button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button>
																					</div>
																				</div>
																			</div>
																		</div>
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
					</div>
				</div>
			</section>
		</div>
		<jsp:include page="/WEB-INF/view/common/admin/footer.jsp"></jsp:include>
	</div>
	<jsp:include page="/WEB-INF/view/common/admin/foot.jsp"></jsp:include>
</body>
</html>
