#!/usr/bin/env python3
"""Explicit opt-in HTTPS download of ONE selected image to an owned run directory.
Never fetches packages, websites, scripts, PDFs, documents, or arbitrary files.
Requires --allow-image-download. No third-party libraries.
"""
from __future__ import annotations
import argparse
import hashlib
import ipaddress
import json
from pathlib import Path
import socket
import sys
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler

MAX = 12 * 1024 * 1024


def validate_url(url):
    u=urlsplit(url)
    if u.scheme!='https' or not u.hostname or u.username or u.password or u.port not in (None,443):
        raise ValueError('仅支持无凭据、标准端口的公开 HTTPS 图片 URL')
    if len(url)>4096 or u.hostname.endswith('.local'):
        raise ValueError('URL 不安全或过长')
    try:
        addrs=socket.getaddrinfo(u.hostname,443,type=socket.SOCK_STREAM)
    except OSError as exc:
        raise ValueError('无法解析图片主机') from exc
    if not addrs or any(not ipaddress.ip_address(a[4][0]).is_global for a in addrs):
        raise ValueError('目标指向本地、内网、保留地址或非公共地址')


class SafeRedirect(HTTPRedirectHandler):
    def __init__(self):self.count=0
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        self.count+=1
        if self.count>3:raise ValueError('图片重定向次数过多')
        validate_url(newurl)
        return super().redirect_request(req,fp,code,msg,headers,newurl)


def signature(data):
    if data.startswith(b'\x89PNG\r\n\x1a\n') and data[12:16] == b'IHDR':return '.png'
    if data.startswith(b'\xff\xd8\xff'):return '.jpg'
    if data[:4]==b'RIFF' and data[8:12]==b'WEBP':return '.webp'
    return None


def main():
    p=argparse.ArgumentParser(description='明确批准后，安全下载一张候选原图；不安装/下载其他文件')
    p.add_argument('--root',required=True)
    p.add_argument('--run-id',required=True)
    p.add_argument('--image-url',required=True)
    p.add_argument('--allow-image-download',action='store_true')
    args=p.parse_args()
    try:
        if not args.allow_image_download:raise ValueError('必须明确指定 --allow-image-download 才能下载')
        if not args.run_id.isascii() or not args.run_id.replace('-','').replace('_','').replace('.','').isalnum() or args.run_id in ('.','..'):
            raise ValueError('非法 run ID')
        root=Path(args.root).resolve(strict=True)
        pid=json.loads((root/'project-assets'/'project.json').read_text('utf-8'))['project_id']
        owned=root/'.skill-tmp'/'technical-visual-assets'/args.run_id
        marker=owned/'.owned-by-technical-visual-assets'
        if not owned.is_dir() or owned.is_symlink() or owned.resolve().parent!=(root/'.skill-tmp'/'technical-visual-assets').resolve() or not marker.is_file() or marker.read_text('utf-8')!=pid:
            raise ValueError('运行目录未验证所有权，拒绝下载')
        validate_url(args.image_url)
        opener=build_opener(SafeRedirect())
        request=Request(args.image_url,headers={'User-Agent':'ThesisDocSuite/0.2 academic image verification','Accept':'image/png,image/jpeg,image/webp'})
        with opener.open(request,timeout=18) as response:
            if response.status!=200:raise ValueError(f'HTTP 状态 {response.status}')
            content_type=response.headers.get('Content-Type','').lower().split(';')[0].strip()
            if content_type not in ('image/png','image/jpeg','image/webp'):
                raise ValueError('返回的不是明确图片 MIME 类型')
            data=response.read(MAX+1)
        if len(data)>MAX:raise ValueError('图像超过 12MiB 上限')
        ext=signature(data)
        if not ext:raise ValueError('文件签名不是 PNG/JPEG/WEBP')
        if {'image/png':'.png','image/jpeg':'.jpg','image/webp':'.webp'}[content_type]!=ext:
            raise ValueError('MIME 类型与实际文件签名不一致')
        sha=hashlib.sha256(data).hexdigest()
        path=owned/('candidate-'+sha[:16]+ext)
        if not path.exists():
            with path.open('xb') as f:f.write(data)
        print(json.dumps({'status':'CANDIDATE_DOWNLOADED','file':str(path),'bytes':len(data),'sha256':sha,
            'notice':'尚未验证模块型号、主体是否完整及复用授权；后续需 add-external + review。'},ensure_ascii=False,indent=2))
    except Exception as exc:
        print(json.dumps({'status':'FAIL','reason':str(exc)},ensure_ascii=False),file=sys.stderr)
        return 2
    return 0

if __name__=='__main__':sys.exit(main())
