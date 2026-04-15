# -*- coding: UTF-8 -*-
import sys
from logging import Formatter
import logging
import os
import requests
from flask import Flask
from flask import render_template
from flask import request, jsonify
import datetime
from sqlalchemy.orm import declarative_base
import sqlalchemy as db

import json
from web.weixin_client import WeixinClient

from web.weibo_client import WeiboClient

# import eeda.const

# eeda.const.MYSQL_DB      # 数据库名
# eeda.const.MYSQL_USER    # 用户名
# eeda.const.MYSQL_PASS    # 密码
# eeda.const.MYSQL_HOST    # 主库域名（可读写）
# eeda.const.MYSQL_PORT    # 端口，类型为<type 'str'>，请根据框架要求自行转换为int
# eeda.const.MYSQL_HOST_S  # 从库域名（只读）

# reload(sys)
# sys.setdefaultencoding('utf8')


app = Flask(__name__)
# app.config['SQLALCHEMY_DATABASE_URI'] = "mysql+pymysql://"+eeda.const.MYSQL_USER+":"+eeda.const.MYSQL_PASS+"@"+eeda.const.MYSQL_HOST+"/"+eeda.const.MYSQL_DB

app.config[
    'SQLALCHEMY_DATABASE_URI'] = ""

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# db = SQLAlchemy(app)
# 创建数据库连接
engine = db.create_engine("postgresql://user:password@localhost/database")

Base = declarative_base()

weixin_client = WeixinClient()
weibo_client = WeiboClient()


def renderResultJson(data, success=True, message=''):
    obj = {}
    if data is not None:
        app.logger.info('data: %s', data)
        jsonStr = json.dumps(data, cls=SQLAlchemyEncoder)
        app.logger.debug('jsonStr: %s ', jsonStr)
        obj = json.loads(jsonStr)
    return jsonify({'success': success, 'data': obj, 'message': message})


# 自定义的json数据解析类
class SQLAlchemyEncoder(json.JSONEncoder):
    def default(self, obj):
        app.logger.debug('obj : %s ', obj)
        if isinstance(obj.__class__, Base):
            # an SQLAlchemy class
            fields = {}
            for field in [x for x in dir(obj) if not x.startswith('_') and x != 'metadata']:
                # 这两个参数不能解析,需要过滤
                if field == 'query' or field == 'query_class':
                    continue
                data = obj.__getattribute__(field)
                # print field,data
                try:
                    if isinstance(data, datetime.datetime):
                        data = data.strftime('%Y-%m-%d %H:%M:%S')
                    # this will fail on non-encodable values, like other classes
                    json.dumps(data)
                    fields[field] = data
                except TypeError as e:
                    print('parse json error field: %s', field)
                    print(e)
                    fields[field] = None
            # a json-encodable dict
            return fields
        return json.JSONEncoder.default(self, obj)


class WxUserInfo(Base):
    __tablename__ = 'wx_user_info'
    id = db.Column(db.Integer, primary_key=True)
    open_id = db.Column(db.String(111))
    nick_name = db.Column(db.String(111))
    attr = db.Column(db.String(512))
    create_time = db.Column(db.DateTime)

    def __init__(self, open_id, nick_name, attr, create_time):
        self.open_id = open_id
        self.nick_name = nick_name
        self.attr = attr
        self.create_time = create_time


@app.route('/get_wx_user')
def get_wx_user():
    return renderResultJson(WxUserInfo.query.all())


# 添加微信openId
# form表单取值
# request.form.get('xxx')  POST
# request.args.get('xxx')  GET
# request.values.get('xxx')
@app.route('/addWxUser')
def add_wx_user():
    print(' add wx user')
    code = request.args.get('code')
    nick_name = request.args.get('nickName')

    print('code: ', code, 'nick_name: ', nick_name)
    openid = weixin_client.get_openid(code)

    if openid is None or openid == '':
        print('获取openid失败')
        return renderResultJson(None, success=False, message='获取openid失败')

    # 校验openid是否已经存在
    user_info = db.session.query(WxUserInfo).filter_by(open_id=openid).first()
    if user_info is not None:
        return renderResultJson(None, success=False, message='openid已存在')
    now = datetime.datetime.now()
    a = WxUserInfo(openid, nick_name, '', now)
    db.session.add(a)
    db.session.commit()
    return renderResultJson(None)


@app.route('/<page>')
@app.route('/<page>/<prefix>')
@app.route('/<page>/<prefix>/<uid>')
def hello(page, prefix='230413', uid='7519797263'):
    print('get weibo, page -> ', page)
    containerid = prefix + uid
    data = weibo_client.get_weibo(page, containerid)
    return jsonify({'success': True, 'data': data, 'message': 'suc'})


@app.route('/get_weibo_buyer/<uid>')
def get_weibo_buyer(uid):
    return weibo_client.get_user_info(uid)


@app.route('/get_detail/<id>')
def get_detail(id):
    return weibo_client.get_detail(id)


# 获取评论
@app.route('/get_comment/<id>')
def get_comment(id):
    return weibo_client.get_comments(id)


@app.route('/send_msg/<openid>-<con>')
def send_singe_msg(openid, con):
    result = weixin_client.send_subscribe_message(openid, con)
    return renderResultJson(result)


if __name__ == '__main__':
    # parse_time("16小时前")
    # parse_time("昨天 10:33")
    # parse_time("02-10")

    app.run(host="0.0.0.0", port=os.getenv("PORT", default=5050), debug=True)
