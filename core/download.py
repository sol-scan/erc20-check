from configparser import ConfigParser
from enum import Enum,unique
import json
import os
from typing import Tuple
import requests

@unique
class Chain(Enum):
    def __new__(cls, url:str, index:int):
        obj = object.__new__(cls)
        obj.url = url
        obj._value_ = index
        return obj
    Eth = "http://api.etherscan.io/api", 1
    Bsc = "http://api.bscscan.com/api", 56
    XAVA = "http://api.snowtrace.io/api", 43114


def download_sourceCode(chain:Chain,addr:str,token_name:str) -> Tuple[str, ConfigParser]:
    dir_path = './sols/'+ '_'.join([token_name, chain.name.lower(), addr[-8:].lower()])
    conf_file = dir_path + '/check.ini'
    check_conf = ConfigParser()

    if os.path.exists(dir_path):
        if len(os.listdir(dir_path)) > 0:
            check_conf.read(conf_file, 'utf-8')
            return dir_path, check_conf
    else:
        os.makedirs(dir_path)

    check_conf.add_section('info')
    check_conf.set('info','chain', chain.name)
    check_conf.set('info','address',addr)

    ret = requests.get(chain.url,{
        "module":"contract",
        "action":"getsourcecode",
        "address":addr,
        "apiKey":""
    })
    raw_json = ret.json()
    raw_contract_info = raw_json['result'][0]
    raw_source_info:str = raw_contract_info['SourceCode']
    check_conf.set('info','contract_name',raw_contract_info['ContractName'])
    if raw_source_info.startswith('{'):
        check_conf.set('info','is_single','False')
        if raw_source_info.startswith('{{'):
            raw_source_info = raw_source_info[1:-1]
        mul_source_info = json.loads(raw_source_info)
        if 'sources' in mul_source_info:
            mul_source_info = mul_source_info['sources']
        for file_name, source_info in mul_source_info.items():
            full_file_name = dir_path+'/'+file_name
            temp_dir_path,temp_file_name = os.path.split(full_file_name)
            if not os.path.exists(temp_dir_path):
                os.makedirs(temp_dir_path)
            with open(full_file_name,'w') as fp:
                fp.write(source_info['content'] + "\n\n")
    else:
        check_conf.set('info','is_single','True')
        with open(dir_path+'/'+raw_contract_info['ContractName']+'.sol','w') as fp:
            fp.write(raw_source_info + "\n\n")
    with open(conf_file,'w') as fp:
        check_conf.write(fp)
    return dir_path, check_conf
