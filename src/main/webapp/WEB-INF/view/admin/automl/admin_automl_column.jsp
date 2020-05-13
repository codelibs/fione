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
			<jsp:param name="logoPath" value="${fe:url('/images/fione/logo-head.png')}" />
			<jsp:param name="menuCategoryType" value="fione" />
			<jsp:param name="menuType" value="automl" />
		</jsp:include>
		<div class="content-wrapper">
			<div class="content-header">
				<div class="container-fluid">
					<div class="row mb-2">
						<div class="col-sm-6">
							<h1>
								<la:message key="labels.automl_columnview_title" arg0="${f:h(project.name)}" arg1="${f:h(columnName)}" />
							</h1>
						</div>
						<div class="col-sm-6">
							<ol class="breadcrumb float-sm-right">
								<li class="breadcrumb-item"><la:link href="../list">
									<la:message key="labels.crud_link_list" />
								</la:link></li>
								<li class="breadcrumb-item"><la:link href="/admin/automl/job/${f:u(project.id)}">
									${f:h(project.name)}
								</la:link></li>
								<li class="breadcrumb-item active"><la:message key="labels.automl_columnview" /></li>
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
						<c:if test="${columnData != null and columnData.columnSummaryChart != null}">
							<div class="card card-outline card-primary">
								<div class="card-header">
									<h3 class="card-title"><la:message key="labels.automl_column_summary" arg0="${f:h(columnName)}" /></h3>
									<div class="card-tools">
										<button type="button" class="btn btn-tool" data-card-widget="collapse">
											<i class="fa fa-minus"></i>
										</button>
									</div>
								</div>
								<div class="card-body">
									<c:set var="chart" value="${columnData.columnSummaryChart}"/><div id="columnSummaryChart" style="width:100%;height:100px;"></div>
<script><!--
echarts.init(document.getElementById('columnSummaryChart')).setOption({
    tooltip: {
        trigger: 'item',
        axisPointer: {
            type: 'shadow'
        }
    },
    xAxis: {
        type: 'value',
    },
    yAxis: [<c:forEach var="yAxis" items="${chart.yAxis}">{
        data: ['${f:h(yAxis.name)}'],
        type: 'category',
        axisLabel: {
            formatter: '{value}'
        },
    },</c:forEach>],
    series: [<c:forEach var="data" items="${chart.series}">{
        data: [${data.data}],
        type: 'boxplot',
        tooltip: {
            formatter: function (param) {
                return [
                    'max: ' + param.data[5],
                    'Q3: ' + param.data[4],
                    'median: ' + param.data[3],
                    'Q1: ' + param.data[2],
                    'min: ' + param.data[1]
                ].join('<br/>')
            }
        }
    },</c:forEach>]}
)
// -->
</script>

								</div>
							</div>
						</c:if>
						<c:if test="${columnData != null and columnData.columnCharacteristicsChart != null}">
							<div class="card card-outline card-primary">
								<div class="card-header">
									<h3 class="card-title"><la:message key="labels.automl_column_histogram" arg0="${f:h(columnName)}" /></h3>
									<div class="card-tools">
										<button type="button" class="btn btn-tool" data-card-widget="collapse">
											<i class="fa fa-minus"></i>
										</button>
									</div>
								</div>
								<div class="card-body">
									<c:set var="chart" value="${columnData.columnCharacteristicsChart}"/><div id="columnCharacteristicsChart" style="width:100%;height:300px;"></div>
<script><!--
echarts.init(document.getElementById('columnCharacteristicsChart')).setOption({
    series: [<c:forEach var="data" items="${chart.series}">{
        data: ${data.data},
        type: 'pie',
        label: {
            position: 'outer',
            alignTo: 'edge',
            margin: 20
        },
    },</c:forEach>]}
)
// -->
</script>

								</div>
							</div>
						</c:if>
						<c:if test="${columnData != null and columnData.histogramChart != null}">
							<div class="card card-outline card-primary">
								<div class="card-header">
									<h3 class="card-title"><la:message key="labels.automl_column_histogram" arg0="${f:h(columnName)}" /></h3>
									<div class="card-tools">
										<button type="button" class="btn btn-tool" data-card-widget="collapse">
											<i class="fa fa-minus"></i>
										</button>
									</div>
								</div>
								<div class="card-body">
									<c:set var="chart" value="${columnData.histogramChart}"/><div id="histogramChart" style="width:100%;height:400px;"></div>
<script><!--
echarts.init(document.getElementById('histogramChart')).setOption({
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
        type: 'bar'
    },</c:forEach>]}
)
// -->
</script>

								</div>
							</div>
						</c:if>
						<c:if test="${columnData != null and columnData.labelListChart != null}">
							<div class="card card-outline card-primary">
								<div class="card-header">
									<h3 class="card-title"><la:message key="labels.automl_column_label" arg0="${f:h(columnName)}" /></h3>
									<div class="card-tools">
										<button type="button" class="btn btn-tool" data-card-widget="collapse">
											<i class="fa fa-minus"></i>
										</button>
									</div>
								</div>
								<div class="card-body">
									<c:set var="chart" value="${columnData.labelListChart}"/><div id="labelListChart" style="width:100%;height:${chart.height}px;"></div>
<script><!--
echarts.init(document.getElementById('labelListChart')).setOption({
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
							</div>
						</c:if>
						<c:if test="${columnData == null or not columnData.availableCharts}">
						<div class="alert alert-info"><la:message key="labels.automl_column_noanalysis" arg0="${f:h(columnName)}" /></div>
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
