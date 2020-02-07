<%@page pageEncoding="UTF-8" contentType="text/html; charset=UTF-8"%><%@taglib prefix="fi" uri="http://fione.codelibs.org/functions" %><!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title><la:message key="labels.fione_brand_title" /> | <la:message key="labels.easyml" /></title>
<jsp:include page="/WEB-INF/view/common/admin/head.jsp"></jsp:include>
<meta http-equiv="refresh" content="5;URL=${contextPath}/admin/easyml/job/${f:u(project.id)}" />
</head>
<body class="hold-transition skin-blue sidebar-mini">
	<div class="wrapper">
		<jsp:include page="/WEB-INF/view/common/admin/header.jsp"></jsp:include>
		<jsp:include page="/WEB-INF/view/common/admin/sidebar.jsp">
			<jsp:param name="menuCategoryType" value="fione" />
			<jsp:param name="menuType" value="easyml" />
		</jsp:include>
		<div class="content-wrapper">
			<section class="content-header">
				<h1><la:message key="labels.easyml_jobs_in" arg0="${f:h(project.name)}" /></h1>
				<ol class="breadcrumb">
					<li><la:link href="../dataset">
							<la:message key="labels.crud_link_list" />
						</la:link></li>
					<li class="active"><la:message key="labels.easyml_jobs" /></li>
				</ol>
			</section>
			<section class="content">
				<div class="row">
					<div class="col-md-12">
						<div class="card card-outline card-success">
							<div class="card-header">
								<h3 class="card-title">
									<la:message key="labels.easyml_jobs" />
								</h3>
								<div class="btn-tools pull-right">
								</div>
							</div>
							<div class="card-body">
								<div>
									<la:info id="msg" message="true">
										<div class="alert alert-info">${msg}</div>
									</la:info>
									<la:errors property="_global" />
								</div>
								<div>
									<i class="fas fa-spinner fa-lg fa-spin"></i>
									<la:message key="labels.easyml_processing" />
								</div>
								<c:if test="${fn:length(project.jobs) == 0}">
									<div class="row top10">
										<div class="col-sm-12">
											<em class="fa fa-info-circle text-primary"></em>
											<la:message key="labels.list_could_not_find_crud_table" />
										</div>
									</div>
								</c:if>
								<c:if test="${fn:length(project.jobs) gt 0}">
									<div class="row top10">
										<div class="col-sm-12">
											<table class="table table-bordered table-striped small">
												<thead>
													<tr>
														<th><la:message key="labels.automl_destination" /></th>
														<th class="col-sm-2 text-center"><la:message key="labels.automl_start_time" /></th>
														<th class="col-sm-2 text-center"><la:message key="labels.automl_end_time" /></th>
														<th class="col-sm-2 text-center"><la:message key="labels.automl_run_time" /></th>
														<th class="col-sm-1 text-center"><la:message key="labels.automl_status" /></th>
													</tr>
												</thead>
												<tbody>
													<c:forEach var="data" varStatus="s" items="${project.jobs}">
														<tr>
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
																			<div class="progress-bar" role="progressbar" aria-valuenow="${f:h(data.progressInt)}"
																				aria-valuemin="0" aria-valuemax="100" style="width:${f:h(data.progressInt)}%;"
																			>
																				<i class="fas fa-running" title="${f:h(data.progressInt)}%"></i>
																			</div>
																		</div>
																	</c:when>
																	<c:when test="${data.status == 'DONE' }">
																		<i class="fas fa-check"></i>
																	</c:when>
																	<c:otherwise>
																		<i class="fas fa-question"></i>
																	</c:otherwise>
																</c:choose></td>
														</tr>
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
