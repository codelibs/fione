<%@page pageEncoding="UTF-8" contentType="text/html; charset=UTF-8"%><%@taglib prefix="fi"
	uri="http://fione.codelibs.org/functions"
%><!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title><la:message key="labels.admin_brand_title" /> | <la:message key="labels.easyml" /></title>
<jsp:include page="/WEB-INF/view/common/admin/head.jsp"></jsp:include>
</head>
<body class="skin-blue sidebar-mini">
	<div class="wrapper">
		<jsp:include page="/WEB-INF/view/common/admin/header.jsp"></jsp:include>
		<jsp:include page="/WEB-INF/view/common/admin/sidebar.jsp">
			<jsp:param name="menuCategoryType" value="fione" />
			<jsp:param name="menuType" value="easyml" />
		</jsp:include>
		<div class="content-wrapper">
			<section class="content-header">
				<h1>Prediction Summary</h1>
				<ol class="breadcrumb">
					<li><la:link href="../dataset">
							Data Set
						</la:link></li>
					<li><la:link href="../train/${f:u(projectId)}?did=${f:u(dataSetId)}">
							Data Analysis
						</la:link></li>
					<li class="active">Summary</li>
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
						<div class="info-box">
							<span class="info-box-icon bg-aqua"><i class="fas fa-table"></i></span>
							<div class="info-box-content">
								<span class="info-box-number">${f:h(columnSummaries.rows)} Rows</span>
								<span class="info-box-number">${f:h(columnSummaries.numColumns)} Colmns</span>
								<div style="overflow: hidden;text-overflow: ellipsis;">${fi:frameName(frameId)}</div>
							</div>
						</div>
						<div class="info-box">
							<span class="info-box-icon bg-green"><i class="fas fa-hammer"></i></span>
							<div class="info-box-content">
								<span class="info-box-number">${fn:length(leaderboard.models)} Models</span>
								<span>Best Model</span>
								<div style="overflow: hidden;text-overflow: ellipsis;">${leaderboard.models[0].name}</div>
							</div>
						</div>
						<div class="info-box">
							<span class="info-box-icon bg-yellow"><i class="fas fa-chart-line"></i></span>
							<div class="info-box-content">
								<span class="info-box-number">${f:h(leaderboard.sortMetric)} ${fi:formatNumber(leaderboard.sortMetrics[0],"%.8f")}</span>
								<div style="overflow: hidden;text-overflow: ellipsis;">${f:h(responseColumn)}</div>
							</div>
						</div>
					</div>
					<div class="col-md-9">
						<div class="box box-info">
							<div class="box-header with-border">
								<h3 class="box-title">Evaluation</h3>
								<div class="btn-tools pull-right">
									<button type="button" class="btn btn-box-tool" data-widget="collapse">
										<i class="fa fa-minus"></i>
									</button>
								</div>
							</div>
							<div class="box-body">

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
