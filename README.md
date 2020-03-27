Fione: Fess AutoML
=========

## Overview

Fione is AutoML extension for Fess.

## Documents

- [fione.codelibs.org](https://fione.codelibs.org/)
- [docker-fione](https://github.com/codelibs/docker-fione/blob/master/README.md#getting-started)
- [discuss.codelibs.org](https://discuss.codelibs.org/c/FioneEN)

## Getting Started

See [Quick Start](https://fione.codelibs.org/quick-start.html) guide.

## Development

### Create Source Code For Development

    git clone https://github.com/codelibs/fione.git
    git clone https://github.com/codelibs/fess.git
    cd fione
    bash ./tools/devcmd.sh copy
    bash ./tools/devcmd.sh start
    cd ../fess

See [Development Guide](https://fess.codelibs.org/dev/getting-started.html) for Fess.

### Generate Source Code

For updating fione\_message, use dbflute:freegen

    mvn dbflute:download # (one time command)
    mvn dbflute:freegen

### Build package

    mvn package
    mvn rpm:rpm   # .rpm package
    mvn jdeb:jdeb # .deb package
