#!/bin/bash

REMOTE=opssat1.esoc.esa.int

USER=exp145
NAME=Mladenov

version=$(git describe --tags)-$(git rev-parse --short HEAD)

if [[ $(git diff --stat) != '' ]]; then
  version="${version}-dirty"
else
  version="${version}-clean"
fi

package_name="$USER"_"$version"_"$NAME".zip

zip -r delivery/$package_name home/*

echo "Finished preparing ZIP file"
ls -lart delivery/$package_name
