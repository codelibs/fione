<%@page pageEncoding="UTF-8" contentType="text/html; charset=UTF-8"%><%@taglib prefix="fi" uri="http://fione.codelibs.org/functions" %><!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title><la:message key="labels.fione_brand_title" /> | <la:message key="labels.easyml" /></title>
<jsp:include page="/WEB-INF/view/common/admin/head.jsp"></jsp:include>
</head>
<body class="hold-transition skin-blue sidebar-mini">
	<div class="wrapper">
		<jsp:include page="/WEB-INF/view/common/admin/header.jsp"></jsp:include>
		<jsp:include page="/WEB-INF/view/common/admin/sidebar.jsp">
			<jsp:param name="brandName" value="Fione" />
			<jsp:param name="logoPath" value="${fe:url('/images/fione/logo-head.png')}" />
			<jsp:param name="menuCategoryType" value="fione" />
			<jsp:param name="menuType" value="easyml" />
		</jsp:include>
		<div class="content-wrapper">
			<div class="content-header">
				<div class="container-fluid">
					<div class="row mb-2">
						<div class="col-6">
							<h1><la:message key="labels.easyml_data_analysis_in" arg0="${f:h(project.name)}" /></h1>
						</div>
						<div class="col-6">
							<ol class="breadcrumb float-sm-right">
								<li class="breadcrumb-item"><la:link href="../dataset">
									<la:message key="labels.easyml_dataset" />
								</la:link></li>
								<li class="breadcrumb-item active"><la:message key="labels.easyml_data_analysis" /></li>

							</ol>
						</div>
					</div>
				</div>
			</div>
			<section class="content">
				<la:form action="/admin/easyml" >
					<la:hidden property="projectId"/>
					<la:hidden property="dataSetId"/>
					<la:hidden property="frameId"/>
					<div class="row">
						<div class="col-md-12">
							<la:info id="msg" message="true">
								<div class="alert alert-info">${msg}</div>
							</la:info>
							<la:errors />
						</div>
						<div class="col-md-3">
							<div class="card card-outline card-success">
								<div class="card-header">
									<h3 class="card-title">
										<la:message key="labels.easyml_prediction" />
									</h3>
									<div class="btn-tools pull-right">
									</div>
								</div>
								<div class="card-body">
									<div class="form-group">
										<label for="responseColumn"><la:message key="labels.easyml_predicted_column" /></label>
										<la:errors property="responseColumn" />
										<la:select property="responseColumn" styleId="responseColumn" styleClass="custom-select">
											<c:forEach var="item" items="${columnItems}">
												<la:option value="${f:u(item.id)}">${f:h(item.name)}</la:option>
											</c:forEach>
										</la:select>
									</div>
									<div class="form-group">
										<label><la:message key="labels.easyml_prediction_type" /></label>
										<div class="form-check">
											<la:radio property="predictionType" value="b" styleClass="form-check-input"></la:radio>
											<label class="form-check-label" for="predictionType"><la:message key="labels.easyml_binaryclass_classification" /></label>
										</div>
										<div class="form-check">
											<la:radio property="predictionType" value="m" styleClass="form-check-input"></la:radio>
											<label class="form-check-label" for="predictionType"><la:message key="labels.easyml_multiclass_classification" /></label>
										</div>
										<div class="form-check">
											<la:radio property="predictionType" value="r" styleClass="form-check-input"></la:radio>
											<label class="form-check-label" for="predictionType"><la:message key="labels.easyml_numeric_prediction" /></label>
										</div>
									</div>
									<div class="form-group">
										<label for="maxRuntimeSecs"><la:message key="labels.easyml_max_execution_time" /></label>
										<la:errors property="maxRuntimeSecs" />
										<la:select property="maxRuntimeSecs" styleId="maxRuntimeSecs" styleClass="custom-select">
											<la:option value="0"><la:message key="labels.easyml_unlimited" /></la:option>
											<la:option value="60"><la:message key="labels.easyml_1m" /></la:option>
											<la:option value="300"><la:message key="labels.easyml_5m" /></la:option>
											<la:option value="600"><la:message key="labels.easyml_10m" /></la:option>
											<la:option value="1800"><la:message key="labels.easyml_30m" /></la:option>
											<la:option value="3600"><la:message key="labels.easyml_1h" /></la:option>
											<la:option value="86400"><la:message key="labels.easyml_1d" /></la:option>
										</la:select>
									</div>
								</div>
								<div class="card-footer">
									<c:if test="${editable}">
										<button type="submit" class="btn btn-success" name="runautoml" value="Run">
											<em class="fas fa-hammer"></em> <la:message key="labels.easyml_run" />
										</button>
									</c:if>
								</div>
							</div>
						</div>
						<div class="col-md-9">
							<div class="card card-outline card-success">
								<div class="card-header">
									<h3 class="card-title">
										<la:message key="labels.easyml_input_columns" />
									</h3>
									<div class="btn-tools pull-right">
									</div>
								</div>
								<div class="card-body">
									<table class="table table-bordered table-striped">
										<thead>
											<tr>
												<th style="width:5%" scope="col"></th>
												<th style="width:25%" scope="col"><la:message key="labels.automl_name" /></th>
												<th style="width:20%" class="col-2 text-center" scope="col"><la:message key="labels.automl_type" /></th>
												<th style="width:10%" scope="col"><la:message key="labels.automl_missing" /></th>
												<th style="width:10%" scope="col"><la:message key="labels.automl_min" /></th>
												<th style="width:10%" scope="col"><la:message key="labels.automl_max" /></th>
												<th style="width:10%" scope="col"><la:message key="labels.automl_mean" /></th>
												<th style="width:10%" scope="col"><la:message key="labels.automl_cardinality" /></th>
											</tr>
										</thead>
										<tbody>
											<c:forEach var="data" varStatus="s" items="${columnItems}">
												<tr>
													<td class="text-center"><input type="checkbox" name="columns.${f:h(data.id)}"<c:if test="${columns.containsKey(data.id)}"> checked="checked"</c:if>></td>
													<td>${f:h(data.name)}</td>
													<td class="col-2">
														<select name="columnTypes.${f:h(data.id)}" id="columnTypes.${f:h(data.id)}" class="form-control">
														<c:forEach var="colType" items="${columnTypeItems}">
															<option value="${f:u(colType.value)}" <c:if test="${colType.value == data.value}">selected</c:if>>${f:h(colType.label)}</option>
														</c:forEach>
														</select>
													</td>
													<td>${f:h(data.missing)}</td>
													<td>${fi:formatNumber(data.min,"%.4f")}</td>
													<td>${fi:formatNumber(data.max,"%.4f")}</td>
													<td>${fi:formatNumber(data.mean,"%.4f")}</td>
													<td>
													<c:if test="${data.value=='Enum'}">${f:h(data.cardinality)}</c:if>
													<c:if test="${data.value!='Enum'}">-</c:if>
													</td>
												</tr>
											</c:forEach>
										</tbody>
									</table>
								</div>
							</div>
						</div>
					</div>
				</la:form>
			</section>
		</div>
		<jsp:include page="/WEB-INF/view/common/admin/footer.jsp"></jsp:include>
	</div>
	<jsp:include page="/WEB-INF/view/common/admin/foot.jsp"></jsp:include>
</body>
</html>
