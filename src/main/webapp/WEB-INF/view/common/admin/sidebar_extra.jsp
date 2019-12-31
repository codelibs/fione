<%@page pageEncoding="UTF-8" contentType="text/html; charset=UTF-8"%>
<li class="treeview <c:if test="${param.menuCategoryType=='fione'}">active</c:if>"><a href="#"><em
		class='fas fa-robot' style="width:20px;"
	></em> <span><la:message key="labels.menu_fione" /></span> <em class="fa fa-angle-left pull-right"></em></a>
	<ul class="treeview-menu">
		<li <c:if test="${param.menuType=='automl'}">class="active"</c:if>><la:link href="/admin/automl/">
				<em class='fa fa-genderless'></em>
				<span><la:message key="labels.menu_automl" /></span>
			</la:link></li>
	</ul></li>

