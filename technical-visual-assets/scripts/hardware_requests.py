#!/usr/bin/env python3
"""Conservative hardware-photo requirements from ONE project technical Markdown.

No network, inferred BOM, product lookup, execution of user code, or writes here.
A mention is a request for user confirmation, not proof that a product was installed.
"""
from __future__ import annotations
from hashlib import sha256
import re

# Pattern expressions return the exact matched text, never a normalized fabricated model.
PATTERNS = [
    r'(?:树莓派\s*(?:Raspberry\s*Pi\s*)?\d\s*[A-Z]?(?:\s*[（(]\s*\d+\s*GB\s*[)）]|\s+\d+\s*GB)?)',
    r'(?:Raspberry\s*Pi\s*\d(?:\s*Model\s*[AB])?(?:\s*\d+\s*GB)?)',
    r'(?:STM32\s*[A-Z]?\d{3}[A-Z0-9]{0,9}\s*(?:开发板|核心板|控制板|主控板|模块)?)',
    r'(?:ESP32(?:-[A-Z0-9-]+)?\s*(?:开发板|模块)?)',
    r'(?:SHT\d{2}\s*(?:传感器(?:模块)?|模组|模块|芯片)?)',
    r'(?:DHT\d{2}\s*(?:传感器(?:模块)?|模组|模块)?)',
    r'(?:Air\d{3,4}[A-Z0-9]*\s*(?:模组|模块)?)',
    r'(?:NRF24L01\+?\s*(?:模组|模块)?)',
    r'(?:LoRa\s*(?:通讯|通信)?\s*(?:模组|模块))',
    r'(?:RS[- ]?485\s*(?:通信|通讯|转换|收发)?\s*(?:模组|模块|芯片))',
    r'(?:GPS\s*(?:定位)?\s*(?:模组|模块))',
    r'(?:\d+G\s*(?:通信|通讯)?\s*(?:模组|模块))',
    r'(?:摄像头(?:模组|模块)?|麦克风(?:模组|模块)?|扬声器(?:模组|模块)?|显示屏(?:模组|模块)?|OLED(?:显示屏|模块)?|LCD(?:显示屏|模块)?|步进电机|舵机|水泵|继电器(?:模块)?|电源模块|太阳能板)',
    r'(?:温湿度|温度|湿度|水浸|倾角|倾斜|有害气体|甲烷|二氧化碳|氧气|粉尘|光照|距离|超声波|红外|风速|烟雾|雨量|液位|土壤|空气质量|压力|气压|pH|PH|电导率)(?:传感器|模块|模组)',
]
PATS=[re.compile(p,re.I) for p in PATTERNS]
BAD_CONTEXT=re.compile(r'备用|未使用|未启用|不采用|规划|待确认|尚未实现|未接入|原本计划|不涉及|仅示例|演示',re.I)
ONLY_DOC=re.compile(r'资料声明|README|计划|设计目标|拟采用|面向',re.I)
# Ignore headings, citations and third-party service name rather than inventing new hardware.
SKIP=re.compile(r'^\s*(?:>|\[|\*\s*来源|[-*]\s*\[|https?://)')


def identify_modules(body:str, md_ref:str, md_hash:str):
    found={}; in_fence=False
    lines=body.splitlines()
    for n,line in enumerate(lines,1):
        if line.strip().startswith('```'):
            in_fence=not in_fence;continue
        if in_fence or len(line)>950 or SKIP.search(line):continue
        # Markdown table rows frequently contain concise hardware BOM data, allow rows
        # and avoid table delimiter lines.
        if re.match(r'^\s*\|',line) and re.fullmatch(r'[\s\-|:]+',line):continue
        for pat in PATS:
            for match in pat.finditer(line):
                raw=match.group(0).strip(' ,.\t、:：；，。')
                if len(raw)<2 or raw.lower() in {'模块','开发板','传感器','模组'}:continue
                key=re.sub(r'\s+','',raw.casefold())
                # Generic Pi 4B and explicit RAM SKU refer to one physical board
                # request. Preserve each verbatim mention as evidence; do not guess RAM.
                if re.match(r'^树莓派\s*4\s*b',raw,re.I):
                    key='树莓派4b'
                if key not in found:
                    rid='MOD-'+sha256(key.encode('utf-8')).hexdigest()[:12].upper()
                    found[key]={
                        'id':rid,'name_from_md':raw,'status':'user-photo-required',
                        'claim_strength':'not_verified',
                        'requested_object':'请上传完整设备、模组或整板的实物照片；若MD只写芯片型号，先确认实际板型',
                        'model_specificity':'requires-user-confirmation',
                        'evidence':{'technical_md':md_ref,'technical_md_sha256':md_hash,'lines':[], 'excerpts':[]},
                        'user_upload_status':'missing',
                    }
                item=found[key]
                if key=='树莓派4b' and re.search(r'\d+\s*GB',raw,re.I):
                    # Prefer the more explicit *verbatim* phrase from the MD.
                    item['name_from_md']=raw
                if n not in item['evidence']['lines']:
                    item['evidence']['lines'].append(n)
                    item['evidence']['excerpts'].append(line.strip()[:200])
                if BAD_CONTEXT.search(line):
                    item['claim_strength']='spare-or-unconfirmed'
                elif ONLY_DOC.search(line) and item['claim_strength']!='spare-or-unconfirmed':
                    item['claim_strength']='documentation-only'
                elif item['claim_strength']=='not_verified':
                    item['claim_strength']='mentioned-in-md'
                if re.search(r'\b\d+\s*GB\b|STM32|ESP32|NRF24L01|SHT\d\d|DHT\d\d|Air\d+',raw,re.I):
                    item['model_specificity']='model-mentioned-needs-object-confirmation'
    return list(found.values())
