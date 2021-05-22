#!/bin/busybox sh

result=`ps aux | grep -i "sar_processor.py" | grep -v "grep" | wc -l`
if [ $result -ge 1 ]
	then
		exit 0
	else
		python3 /home/exp145/sar_processor.py
		exit 0
fi
