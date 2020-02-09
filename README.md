Fione: Fess AutoML
=========

## Overview

Fione is AutoML extension for Fess.

## Documents

- [fione.codelibs.org](https://fione.codelibs.org/)
- [docker-fione](https://github.com/codelibs/docker-fione/blob/master/README.md#getting-started)
- [discuss.codelibs.org](https://discuss.codelibs.org/c/FioneEN)

## Development

### Generate Source Code

For updating fione\_message, use dbflute:freegen

    mvn dbflute:download # (one time command)
    mvn dbflute:freegen

### Build package

    mvn package
    mvn rpm:rpm   # .rpm package
    mvn jdeb:jdeb # .deb package
