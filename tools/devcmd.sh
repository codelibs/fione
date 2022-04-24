#!/bin/bash

subcommand=$1
cd `dirname $0`
cd ..
BASE_DIR=`pwd`

check_fess() {
  ls ../fess 2>&1 > /dev/null
  if [ $? != 0 ] ; then
    echo "fess does not exist."
    exit 1
  fi
}

copy_to_fess() {
  check_fess
  cp -r src/main/java/org/codelibs/fione ../fess/src/main/java/org/codelibs
  cp -r src/main/webapp/WEB-INF/view/admin/automl ../fess/src/main/webapp/WEB-INF/view/admin
  cp -r src/main/webapp/WEB-INF/view/admin/easyml ../fess/src/main/webapp/WEB-INF/view/admin
  cp -r src/main/webapp/WEB-INF/view/admin/systemml ../fess/src/main/webapp/WEB-INF/view/admin
  cp -r src/main/webapp/WEB-INF/env/fione ../fess/src/main/webapp/WEB-INF/env
  cp -r src/main/webapp/images/fione ../fess/src/main/webapp/images
  #cp -r src/main/webapp/css/admin/fione ../fess/src/main/webapp/css/admin
  cp -r src/main/webapp/js/admin/fione ../fess/src/main/webapp/js/admin
  cp src/main/webapp/WEB-INF/fi.tld ../fess/src/main/webapp/WEB-INF
  cp src/main/webapp/WEB-INF/view/common/admin/sidebar_extra.jsp ../fess/src/main/webapp/WEB-INF/view/common/admin
  cp src/main/resources/fione_message*.properties ../fess/src/main/resources
  cp src/main/resources/fione_label*.properties ../fess/src/main/resources
  cp src/main/resources/fess++.xml ../fess/src/main/resources
  cp src/main/resources/lastaflute_director+assistantDirector.xml ../fess/src/main/resources
  cp src/main/resources/fess+systemHelper.xml ../fess/src/main/resources
  echo "smart.package2 = org.codelibs.fione.app" >> ../fess/src/main/resources/lasta_di.properties
  sed -i "s|RPM build -->|RPM build --><retrofit.version>2.9.0</retrofit.version>|" ../fess/pom.xml
  sed -i 's|common library -->|common library --><dependency><groupId>com.squareup.retrofit2</groupId><artifactId>retrofit</artifactId><version>${retrofit.version}</version></dependency><dependency><groupId>com.squareup.retrofit2</groupId><artifactId>converter-gson</artifactId><version>${retrofit.version}</version></dependency>|' ../fess/pom.xml
}

copy_from_fess() {
  check_fess
  cp -r ../fess/src/main/java/org/codelibs/fione src/main/java/org/codelibs
  cp -r ../fess/src/main/webapp/WEB-INF/view/admin/automl src/main/webapp/WEB-INF/view/admin
  cp -r ../fess/src/main/webapp/WEB-INF/view/admin/easyml src/main/webapp/WEB-INF/view/admin
  cp -r ../fess/src/main/webapp/WEB-INF/view/admin/systemml src/main/webapp/WEB-INF/view/admin
  cp -r ../fess/src/main/webapp/WEB-INF/env/fione src/main/webapp/WEB-INF/env
  cp -r ../fess/src/main/webapp/images/fione src/main/webapp/images
  #cp -r ../fess/src/main/webapp/css/admin/fione src/main/webapp/css/admin
  cp -r ../fess/src/main/webapp/js/admin/fione src/main/webapp/js/admin
  cp ../fess/src/main/webapp/WEB-INF/fi.tld src/main/webapp/WEB-INF
  cp ../fess/src/main/webapp/WEB-INF/view/common/admin/sidebar_extra.jsp src/main/webapp/WEB-INF/view/common/admin
  cp ../fess/src/main/resources/fione_message*.properties src/main/resources
  cp ../fess/src/main/resources/fione_label*.properties src/main/resources
  cp ../fess/src/main/resources/fess++.xml src/main/resources
  cp ../fess/src/main/resources/lastaflute_director+assistantDirector.xml src/main/resources
  cp ../fess/src/main/resources/fess+systemHelper.xml src/main/resources
}

clean() {
  check_fess
  rm -fr ../fess/src/main/java/org/codelibs/fione
  rm -fr ../fess/src/main/webapp/WEB-INF/view/admin/automl
  rm -fr ../fess/src/main/webapp/WEB-INF/view/admin/easyml
  rm -fr ../fess/src/main/webapp/WEB-INF/view/admin/systemml
  rm -fr ../fess/src/main/webapp/WEB-INF/env/fione
  rm -fr ../fess/src/main/webapp/WEB-INF/plugin/fione
  rm -fr ../fess/src/main/webapp/images/fione
  rm -fr ../fess/src/main/webapp/css/admin/fione
  rm -fr ../fess/src/main/webapp/js/admin/fione
  rm -f ../fess/src/main/webapp/WEB-INF/fi.tld
  rm -f ../fess/src/main/webapp/WEB-INF/view/common/admin/sidebar_extra.jsp
  rm -f ../fess/src/main/resources/fione_message*.properties
  rm -f ../fess/src/main/resources/fione_label*.properties
  rm -f ../fess/src/main/resources/fess++.xml
  rm -f ../fess/src/main/resources/lastaflute_director+assistantDirector.xml
  rm -f ../fess/src/main/resources/fess+systemHelper.xml
  pushd ../fess
  git checkout -- src/main/resources/lasta_di.properties pom.xml
  popd
}

start_docker() {
  cd $BASE_DIR/tools/docker
  docker compose up &
}

stop_docker() {
  cd $BASE_DIR/tools/docker
  docker compose down
}

if [[ $subcommand = "copy" ]] ; then
  clean
  copy_to_fess
elif [[ $subcommand = "restore" ]] ; then
  copy_from_fess
elif [[ $subcommand = "clean" ]] ; then
  clean
elif [[ $subcommand = "start" ]] ; then
  start_docker
elif [[ $subcommand = "stop" ]] ; then
  stop_docker
else
  echo "unknown command."
fi
