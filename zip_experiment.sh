#!/bin/bash

version=$(git rev-parse --short HEAD)
package_name=exp145_"$version"_Mladenov.zip

zip -r delivery/$package_name home/*

echo "Finished preparing ZIP file"

ls -lart delivery/$package_name