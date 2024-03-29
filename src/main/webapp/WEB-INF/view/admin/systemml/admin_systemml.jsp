<%@page pageEncoding="UTF-8" contentType="text/html; charset=UTF-8"%><%@taglib prefix="fi" uri="http://fione.codelibs.org/functions" %><!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title><la:message key="labels.fione_brand_title" /> | <la:message key="labels.systemml" /></title>
<jsp:include page="/WEB-INF/view/common/admin/head.jsp"></jsp:include>
</head>
<body class="hold-transition skin-blue sidebar-mini">
	<div class="wrapper">
		<jsp:include page="/WEB-INF/view/common/admin/header.jsp"></jsp:include>
		<jsp:include page="/WEB-INF/view/common/admin/sidebar.jsp">
			<jsp:param name="brandName" value="Fione" />
			<jsp:param name="logoPath" value="/images/fione/logo-head.png" />
			<jsp:param name="menuCategoryType" value="fione" />
			<jsp:param name="menuType" value="systemml" />
		</jsp:include>
		<div class="content-wrapper">
			<div class="content-header">
				<div class="container-fluid">
					<div class="row mb-2">
						<div class="col-sm-6">
							<h1>
								<la:message key="labels.systemml_title_details" />
							</h1>
						</div>
					</div>
				</div>
			</div>
			<section class="content">
				<div class="row">
					<c:if test="${cloudStatus == null}">
					<div class="col-md-12">
						<div class="alert alert-info"><la:message key="labels.systemml_no_servers" /></div>
					</div>
					</c:if>
					<c:if test="${cloudStatus != null}">
					<div class="col-md-12">
						<la:info id="msg" message="true">
							<div class="alert alert-info">${msg}</div>
						</la:info>
						<la:errors />
						<div class="card card-outline">
							<div class="card-body p-2">
								<form method="post" action="${contextPath}/admin/systemml/">
								<input type="hidden" name="lastaflute.action.TRANSACTION_TOKEN" value="${f:h(token)}">
								<div class="btn-group" role="toolbar" aria-label="Toolbar">
									<la:link href="/admin/systemml/" styleClass="btn btn-default">
										<i class="fas fa-redo"></i>
										<la:message key="labels.systemml_reload" />
									</la:link>
								</div>

								<div class="float-right">
									<div class="btn-group" role="group">
										<button type="button" class="btn btn-default dropdown-toggle" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
											<la:message key="labels.systemml_options" />
											</button>
										<ul class="dropdown-menu">
											<li><button type="submit" name="addmodule" value="Add Module" class="btn btn-link"><la:message key="labels.systemml_add_module" /></button></li>
											<li><button type="submit" name="reloadmodule" value="Reload Modules" class="btn btn-link"><la:message key="labels.systemml_reload_module" /></button></li>
											<li><button type="submit" name="shutdowncluster" value="Restart H2O" class="btn btn-link"><la:message key="labels.systemml_restart_h2o" /></button></li>
										</ul>
									</div>
								</div>
								</form>
							</div>
						</div>
						<div class="card card-outline card-primary">
							<div class="card-header">
								<h3 class="card-title">
									<la:message key="labels.systemml_nodes" />
								</h3>
								<div class="card-tools">
								</div>
							</div>
							<div class="card-body">
								<table class="table table-bordered table-striped small">
									<thead>
										<tr>
											<th style="width:160px"><la:message key="labels.systemml_name" /></th>
											<%--<th><la:message key="labels.systemml_ping" /></th>--%>
											<th><la:message key="labels.systemml_core" /></th>
											<th><la:message key="labels.systemml_load" /></th>
											<th><la:message key="labels.systemml_mycpup" /></th>
											<th><la:message key="labels.systemml_syscpup" /></th>
											<th><la:message key="labels.systemml_gflops" /></th>
											<th><la:message key="labels.systemml_membw" /></th>
											<th style="width:120px"><la:message key="labels.systemml_gc" /></th>
											<th style="width:120px"><la:message key="labels.systemml_disk" /></th>
										</tr>
									</thead>
									<tbody>
										<c:forEach var="node" varStatus="s" items="${cloudStatus.nodes}">
										<tr>
											<td>
											<c:if test="${node.healthy}"><i class="fas fa-check-circle" style="color:green"></i></c:if>
											<c:if test="${not node.healthy}"><i class="fas fa-times-circle" style="color:red"></i></c:if>
											${f:h(node.ipPort)}</td>
											<%--<td>${fe:date(node.lastPing)}</td>--%>
											<td>${f:h(node.numCpus)}</td>
											<td>${f:h(node.sysLoad)}</td>
											<td>${f:h(node.myCpuPct)}%</td>
											<td>${f:h(node.sysCpuPct)}%</td>
											<td>${fe:formatNumber(node.gflops, "###,###")}</td>
											<td>${fe:formatFileSize(node.memBw)} GB/s</td>
											<td>${fe:formatFileSize(node.freeMem)} / ${fe:formatFileSize(node.maxMem)}</td>
											<td>${fe:formatFileSize(node.freeDisk)} / ${fe:formatFileSize(node.maxDisk)}</td>
										</tr>
										</c:forEach>
									</tbody>
								</table>
							</div>
						</div>
					</div>
					<div class="col-md-6">
						<div class="card card-outline card-primary">
							<div class="card-header">
								<h3 class="card-title">
									<la:message key="labels.systemml_info" />
								</h3>
								<div class="card-tools">
								</div>
							</div>
							<div class="card-body">
								<table class="table table-bordered table-striped small">
									<tbody>
										<tr>
											<td><la:message key="labels.systemml_cloud_name" /></td>
											<td>${f:h(cloudStatus.cloudName)}</td>
										</tr>
										<tr>
											<td><la:message key="labels.systemml_cloud_size" /> / <la:message key="labels.systemml_bad_nodes" /></td>
											<td>${f:h(cloudStatus.cloudSize)} / ${f:h(cloudStatus.badNodes)}</td>
										</tr>
										<tr>
											<td><la:message key="labels.systemml_node_idx" /> / <la:message key="labels.systemml_leader_idx" /></td>
											<td>${f:h(cloudStatus.nodeIdx)} / ${f:h(cloudStatus.leaderIdx)}</td>
										</tr>
										<tr>
											<td><la:message key="labels.systemml_cloud_uptime" /></td>
											<td>${fe:formatDuration(cloudStatus.cloudUptimeMillis)}</td>
										</tr>
										<tr>
											<td><la:message key="labels.systemml_cloud_internal_tz" /></td>
											<td>${f:h(cloudStatus.cloudInternalTimezone)}</td>
										</tr>
										<tr>
											<td><la:message key="labels.systemml_datafile_parser_tz" /></td>
											<td>${f:h(cloudStatus.datafileParserTimezone)}</td>
										</tr>
										<tr>
											<td><la:message key="labels.systemml_consensus" /></td>
											<td>${f:h(cloudStatus.consensus)}</td>
										</tr>
										<tr>
											<td><la:message key="labels.systemml_locked" /></td>
											<td>${f:h(cloudStatus.locked)}</td>
										</tr>
										<tr>
											<td><la:message key="labels.systemml_is_client" /></td>
											<td>${f:h(cloudStatus.isClient)}</td>
										</tr>
										<tr>
											<td><la:message key="labels.systemml_security" /></td>
											<td>${f:h(cloudStatus.internalSecurityEnabled)}</td>
										</tr>
									</tbody>
								</table>
							</div>
						</div>
					</div>
					<div class="col-md-6">
						<div class="card card-outline card-primary">
							<div class="card-header">
								<h3 class="card-title">
									<la:message key="labels.systemml_buildinfo" />
								</h3>
								<div class="card-tools">
								</div>
							</div>
							<div class="card-body">
								<table class="table table-bordered table-striped small">
									<tbody>
										<tr>
											<td><la:message key="labels.systemml_version" /></td>
											<td>${f:h(cloudStatus.version)}</td>
										</tr>
										<tr>
											<td><la:message key="labels.systemml_branch_name" /></td>
											<td>${f:h(cloudStatus.branchName)}</td>
										</tr>
										<tr>
											<td><la:message key="labels.systemml_last_commit_hash" /></td>
											<td>${f:h(cloudStatus.lastCommitHash)}</td>
										</tr>
										<tr>
											<td><la:message key="labels.systemml_describe" /></td>
											<td>${f:h(cloudStatus.describe)}</td>
										</tr>
										<tr>
											<td><la:message key="labels.systemml_compiledby" /></td>
											<td>${f:h(cloudStatus.compiledBy)}</td>
										</tr>
										<tr>
											<td><la:message key="labels.systemml_compiledon" /></td>
											<td>${f:h(cloudStatus.compiledOn)}</td>
										</tr>
										<tr>
											<td><la:message key="labels.systemml_build_number" /></td>
											<td>${f:h(cloudStatus.buildNumber)}</td>
										</tr>
										<tr>
											<td><la:message key="labels.systemml_build_age" /></td>
											<td>${f:h(cloudStatus.buildAge)}</td>
										</tr>
										<tr>
											<td><la:message key="labels.systemml_build_too_old" /></td>
											<td>${f:h(cloudStatus.buildTooOld)}</td>
										</tr>
									</tbody>
								</table>
							</div>
						</div>
					</div>
					</c:if>
				</div>
			</section>
		</div>
		<jsp:include page="/WEB-INF/view/common/admin/footer.jsp"></jsp:include>
	</div>
	<jsp:include page="/WEB-INF/view/common/admin/foot.jsp"></jsp:include>
</body>
</html>
