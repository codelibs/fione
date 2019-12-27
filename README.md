Fione: Fess AutoML
=========

## Overview

Fione is AutoML extension for Fess.

## Development

### Generate Source Code

For updating fione\_message, use dbflute:freegen

    mvn dbflute:download # (one time command)
    mvn dbflute:freegen

### Build package

    mvn package
    mvn rpm:rpm   # .rpm package
    mvn jdeb:jdeb # .deb package
