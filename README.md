Fione: AutoML on Fess
=========

## Overview

TBD...

## Development

### Generate Source Code

For updating fione\_message, use dbflute:freegen

    mvn dbflute:download # (one time command)
    mvn dbflute:freegen

### Build package

    mvn package
    mvn rpm:rpm   # .rpm package
    mvn jdeb:jdeb # .deb package
