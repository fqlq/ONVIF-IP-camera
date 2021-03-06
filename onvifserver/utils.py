#! -*- coding:utf-8 -*-
#
# Copyright 2017 , donglin-zhang, Hangzhou, China
#
# Licensed under the GNU GENERAL PUBLIC LICENSE, Version 3.0;
# you may not use this file except in compliance with the License.
#
from lxml import etree
import re

# onvif soap namespace defined in <ONVIF-Core-Specification> chap5.3
ns_soap = {
    'tt': 'http://www.onvif.org/ver10/schema',
    'tds': 'http://www.onvif.org/ver10/device/wsdl',
    'trt': 'http://www.onvif.org/ver10/media/wsdl',
    'tev': 'http://www.onvif.org/ver10/events/wsdl',
    'ter': 'http://www.onvif.org/ver10/error',
    'dn': 'http://www.onvif.org/ver10/network/wsdl',
    'tns1': 'http://www.onvif.org/ver10/topics',
    'tan': 'http://www.onvif.org/ver20/analytics/wsdl',
    'timg': 'http://www.onvif.org/ver20/imaging/wsdl',
    'tmd': 'http://www.onvif.org/ver10/deviceIO/wsdl',
    # standard namespace
    'wsdl': 'http://schemas.xmlsoap.org/wsdl/',
    'wsoap12': 'http://schemas.xmlsoap.org/wsdl/soap12/',
    'http': 'http://schemas.xmlsoap.org/wsdl/http/',
    'soapenc': 'http://www.w3.org/2003/05/soap-encoding',
    'soapenv': 'http://www.w3.org/2003/05/soap-envelope',
    'xs': 'http://www.w3.org/2001/XMLSchema',
    'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
    'd': 'http://schemas.xmlsoap.org/ws/2005/04/discovery',
    'wsadis': 'http://schemas.xmlsoap.org/ws/2004/08/addressing',
    'wsa': 'http://www.w3.org/2005/08/addressing',
    'wstop': 'http://docs.oasis-open.org/wsn/t-1',
    'wsnt': 'http://docs.oasis-open.org/wsn/b-2',
    'xop': 'http://www.w3.org/2004/08/xop/include',
    'wsa5': 'http://www.w3.org/2005/08/addressing'
}

def map_reverse(scr_dict):
    reverse_dict = {}
    for key in scr_dict:
        reverse_dict[scr_dict[key]] = key
    return reverse_dict

############## service path ####################
service_addr = {
    'device': '/onvif/device_service',
    'media': '/onvif/Media',
    'event': '/onvif/Events',
    'analytics': '/onvif/Analytics',
    'imaging': '/onvif/Imaging',
    'deviceio': '/onvif/DeviceIo'
}
reversed_service_addr = map_reverse(service_addr)

service_version = {
    'Major': 2,
    'Minor': 20
}

SupportedVersions = [(2, 60), (2, 40), (2, 20), (2, 10), (2, 0)]


namespace_map = {
    'device': ('tds', 'http://www.onvif.org/ver10/device/wsdl'),
    'media': ('trt', 'http://www.onvif.org/ver10/media/wsdl'),
    'event': ('tev', 'http://www.onvif.org/ver10/events/wsdl'),
    'analytics': ('tan', 'http://www.onvif.org/ver20/analytics/wsdl'),
    'imaging': ('timg', 'http://www.onvif.org/ver20/imaging/wsdl'),
    'deviceio':('tmd', 'http://www.onvif.org/ver10/deviceIO/wsdl')
}

# bool-string map
bool_map = {
    True: 'true',
    False: 'false'
}
reversed_bool_map = map_reverse(bool_map)


def soap_encode(params, method, path):
    '''
    构造并返回soap消息体
        params: 要封装的参数，字典形式，如下, 
        字典的值可以是一个列表，但是最小单元必须是一个字典,每一个key都封装为一个xml节点的tag
        如果封装的xml多个同级节点有相同tag，则以字典组成的列表方式封装
        如果不希望将字典的key作为一个xml节点，key设置为NO_WRAP,不影响key对应的子集
        key 值为ATTRI：将对应的值作为节点属性封装
        example1：
            'tds:capcabilities':{
                'tt:device':{
                    'tt:xaddr': 'device_services',
                    'tt:network': 'IPV6',
                    'tt:system': 'discovery'
                },
                'tt:events':{
                    'tt:xaddr': 'Events',
                    'tt:WSSubscriptionPolicySupport': True,
                    'tt:WSPullPointSupport': False
                },
                'respon':[
                    {'server': '123'},
                    {'server': '345'},
                    {'server': '789'}
                ],
                
                'tt:imaging': None
            }}
        example2：
            'NO_WRAP':[     # 没有NO_WRAP节点，只有三个server节点
                {'server': '123'},
                {'server': '345'},
                {'server': '789'}
            ],
        method:
            请求的方法名，如GetCapabilities
        path:
            请求路径
    '''
    response_method = '{0}Response'.format(method)
    if path in reversed_service_addr:
        namespace = namespace_map[reversed_service_addr[path]][0]
    else:
        raise KeyError
    return _wrap_soap_message(namespace, response_method, params)

def soap_decode(data):
    '''
    解析客户端的请求消息的操作名称与参数
    '''
    soapenv = etree.fromstring(data)
    if 'Header' in soapenv[0].tag:
        header_node = soapenv[0]
        method = soapenv[1][0]
    else:
        header_node = None
        method = soapenv[0][0]
    # phrase header
    if header_node is not None and len(header_node)>0:
        header_params = _get_params(header_node)
    else:
        header_params = None

    # phrase body
    method_name = _get_node_tag(method)
    if len(method)>0:
        body_params = _get_params(method)
    else:
        body_params = {}
    params = {
        'HEADER': header_params,
        'BODY': body_params
    }
    return method_name, params

def _get_params(node):
    '''
    解析参数信息，将参数打包为一个列表返回。
    return value:
        [{'Category': 'All'}]
        [{'IncludeCapability': 'true'}]
    '''
    tmp_dict = {}
    for param in node:
        param_name = _get_node_tag(param)
        if len(param) > 0:
            sub_param = _get_params(param)   # recursively phrase sub node
            sub_param_name = _get_node_tag(param)
            tmp_dict[sub_param_name] = sub_param
        else:
            if param.text:
                tmp_dict[param_name] = param.text
    return tmp_dict

def _get_node_tag(node):
    '''
    解析出xml节点tag，过滤掉其namespace
    '''
    pattern = r'[^{}]+(?={|$)'
    return re.findall(pattern, node.tag)[0]


def _wrap_soap_message(ns, response_method, params):
    '''封装soap消息'''
    header = _wrap_soap_head()
    param = _wrap_params(params)
    body = '''<soapenv:Body><{0}:{1}>{2}</{0}:{1}>'''.format(ns, response_method, param)
    return '''{0}{1}</soapenv:Body></soapenv:Envelope>'''.format(header, body)


def _wrap_soap_head():
    '''封装soap namespace'''
    response_soap_header = r'''<?xml version="1.0" encoding="UTF-8"?><soapenv:Envelope'''
    for ns in ns_soap:
        ns_string = ''' xmlns:{0}="{1}"'''.format(ns, ns_soap[ns])
        response_soap_header += ns_string
    return '{0}>'.format(response_soap_header)


def _wrap_params(params):
    ''' 封装参数 '''
    body = ''

    for key in params:
        if isinstance(params[key], dict):
            attributes = params[key].pop('ATTRI', None)
            if attributes:
                node = _wrap_attribute(key, attributes)
            else:
                node = key
            sub_node = _wrap_params(params[key])
            if key == 'NO_WRAP':
                body = '''{0}{1}'''.format(body, sub_node)
            else:
                body = '''{0}<{1}>{2}</{3}>'''.format(body, node, sub_node, key)
        elif isinstance(params[key], list):
            list_node = ''
            for item in params[key]:
                list_node += _wrap_params(item)
            if key == 'NO_WRAP':
                body = '''{0}{1}'''.format(body, list_node)
            else:
                body = '''{0}<{1}>{2}</{1}>'''.format(body, key, list_node)
        else:
            if isinstance(params[key], bool):
                params[key] = bool_map[params[key]]
            if params[key] is None:
                body = '''{0}<{1}/>'''.format(body, key)
            else:
                body = '''{0}<{1}>{2}</{1}>'''.format(body, key, params[key])
    return body

def _wrap_attribute(key, attributes):
    node = key
    for attr in attributes:
        if isinstance(attributes[attr], bool):
            attributes[attr] = bool_map[attributes[attr]]
        node = '{0} {1}="{2}"'.format(node, attr, attributes[attr])
    return node

def soap_error(fault_code, subcode, fault_reason, description):
    ''' 封装soap错误信息 '''
    header = _wrap_soap_head()
    err_message = '''{0}<soapenv:Body><soapenv:Fault>'''.format(header)
    if subcode is None:
        err_message += '''<soapenv:Code><soapenv:Value>{0}\
                        </soapenv:Value></soapenv:Code>'''.format(fault_code)
    else:
        err_message += '''<soapenv:Code><soapenv:Value>{0}</soapenv:Value>
                        <soapenv:Subcode><soapenv:Value>{1}</soapenv:Value>
                        </soapenv:Subcode></soapenv:Code>'''.format(fault_code, subcode)
    err_message += '''<soapenv:Reason><soapenv:Text xml:lang="en">{0}\
                    </soapenv:Text></soapenv:Reason>'''.format(fault_reason)
    err_message += '''<soapenv:Node>http://www.w3.org/2003/05/soapenvelope/node/ultimateReceiver</soapenv:Node>
        <soapenv:Role>http://www.w3.org/2003/05/soapenvelope/role/ultimateReceiver</soapenv:Role>'''
    err_message += '''<soapenv:Detail><soapenv:Text>{0}</soapenv:Text></soapenv:Detail>'''.format(description)
    return '''{0}</soapenv:Fault></soapenv:Body></soapenv:Envelope>'''.format(err_message)
