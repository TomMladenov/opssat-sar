# opssat-sar

Repository of the Search and Rescue experiment carried out on the European Space Agency's OPS-SAT Space Lab.
First deployment of GNU Radio running on Linux in Low Earth Orbit on an ESA satellite.

Please refer to our publication:
```
@ARTICLE{9684957,
  author={Mladenov, Tom and Evans, David and Zelenevskiy, Vladimir},
  journal={IEEE Aerospace and Electronic Systems Magazine}, 
  title={Implementation of a GNU Radio-Based Search and Rescue Receiver on ESA&#x0027;s OPS-SAT Space Lab}, 
  year={2022},
  volume={37},
  number={5},
  pages={4-12},
  doi={10.1109/MAES.2022.3143875}}
```

File products from orbital runs are contained in the ```archive``` folder in this repo.

The last successful run on the satellite used following versions:
```
2021-06-15 02:09:57,038 INFO Package: sepp-api
2021-06-15 02:09:57,044 INFO Version: 1.8-81-g7519477

2021-06-15 02:09:57,060 INFO Package: sepp-sdr
2021-06-15 02:09:57,062 INFO Version: 1.8-79-ge467a27

2021-06-15 02:09:57,074 INFO Package: exp145
2021-06-15 02:09:57,076 INFO Version: v2.0-clean
2021-06-15 02:09:57,078 INFO Status: install ok installed
```

The burst detector and necessary beacon decoder library are hosted in separate repositories and the runs in orbit were carried out with following versions:
```
2021-06-15 02:09:57,087 INFO {"git_branch":"beaglebone-dev","git_commit_subject":"Use Im component of filtered signal instead of Arg, add DC-block option","git_date":"Tue Jun 1 08:56:06 2021","git_remote":"git@github.com:TomMladenov/epirb-burst-detector.git","git_sha1":"4779ec28a76eaad43c3a01782a993eb121742241"}
2021-06-15 02:09:57,090 INFO {"git_branch":"gr-3.7.13.4-dev","git_commit_subject":"Add version_info() and make function static","git_date":"Sat May 29 14:52:45 2021","git_remote":"git@github.com:TomMladenov/gr-epirb.git","git_sha1":"f5aebe0a97186b660d72d8f439d74e6e9b857bfd"}
```