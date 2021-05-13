#!/bin/busybox sh

result=`ps aux | grep -i "acquire_samples.sh" | grep -v "grep" | wc -l`
if [ $result -ge 1 ]
	then
		exit 0
	else
		/home/exp145/acquire_samples.sh
		exit 0
fi
