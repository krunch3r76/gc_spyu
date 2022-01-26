#!/usr/bin/env python3
import pprint
import json
from collections import namedtuple

_CpuData_nt = namedtuple('_CpuData_nt', ['essentials', 'vulnerabilities', 'caches'])

def marshal_result(objects):
    """parse the json from lscpu into essentials vulnerablities and caches"""
    marshalled=dict()
    lscpu_objects=objects[0]["lscpu"]
    lscpu_marshalled_dict=dict()
    for lscpu_object in lscpu_objects:
        lscpu_marshalled_dict[lscpu_object["k"][:-1]]=lscpu_object["v"]

    vulnerabilities=dict()
    vulnerabilities_keys=[]
    for lscpu_obj_key in lscpu_marshalled_dict.keys():
        if 'Vulnerability' in lscpu_obj_key:
            vulnerabilities_keys.append(lscpu_obj_key)
    for vulnerabilities_key in vulnerabilities_keys:
        vulnerabilities[vulnerabilities_key] = lscpu_marshalled_dict.pop(vulnerabilities_key) 

    return _CpuData_nt(lscpu_marshalled_dict, vulnerabilities, objects[1]['caches'])

if __name__ == '__main__':
    marshalled=None
    with open("output.txt") as f:
        objects=(json.loads(f.read()))
    data = marshal_result(objects)
    pprint.pprint(data.essentials)
