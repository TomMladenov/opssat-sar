#!/bin/bash

version=$(git rev-parse --short HEAD)

if [[ $(git diff --stat) != '' ]]; then
  version="${version}-dirty"
else
  version="${version}-clean"
fi




package_name=exp145_"$version"_Mladenov.zip

#zip -r delivery/$package_name home/*

echo "Finished preparing ZIP file"

ls -lart delivery/$package_name