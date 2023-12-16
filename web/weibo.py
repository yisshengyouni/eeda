# -*- coding: UTF-8 -*-
import sys
from logging import Formatter
import logging
import os
import requests
from pyquery import PyQuery as pq
from flask import Flask
from flask import render_template
from flask import request, jsonify
import datetime
from dateutil import parser
from sqlalchemy.orm import declarative_base
import sqlalchemy as db

import json

# import eeda.const

# eeda.const.MYSQL_DB      # 数据库名
# eeda.const.MYSQL_USER    # 用户名
# eeda.const.MYSQL_PASS    # 密码
# eeda.const.MYSQL_HOST    # 主库域名（可读写）
# eeda.const.MYSQL_PORT    # 端口，类型为<type 'str'>，请根据框架要求自行转换为int
# eeda.const.MYSQL_HOST_S  # 从库域名（只读）

# reload(sys)
# sys.setdefaultencoding('utf8')


headers = {
    'Host': 'm.weibo.cn',
    'Referer': 'https://m.weibo.cn/u/5687069307',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36',
    'X-Requested-With': 'XMLHttpRequest',
}

app = Flask(__name__)
# app.config['SQLALCHEMY_DATABASE_URI'] = "mysql+pymysql://"+eeda.const.MYSQL_USER+":"+eeda.const.MYSQL_PASS+"@"+eeda.const.MYSQL_HOST+"/"+eeda.const.MYSQL_DB

app.config[
    'SQLALCHEMY_DATABASE_URI'] = ""

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# db = SQLAlchemy(app)
# 创建数据库连接
engine = db.create_engine("postgresql://user:password@localhost/database")

Base = declarative_base()


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
                    json.dumps(data)  # this will fail on non-encodable values, like other classes
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
    return renderResultJson(WxUserInfo.query.all());


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
    openid = get_openid(code)

    if openid is None or openid == '':
        print('获取openid失败')
        return renderResultJson(None, success=False, message='获取openid失败')

    # 校验openid是否已经存在
    user_info = WxUserInfo.query.filter_by(open_id=openid).first()
    if user_info is not None:
        return renderResultJson(None, success=False, message='openid已存在')
    now = datetime.datetime.now()
    a = WxUserInfo(openid, nick_name, '', now)
    db.session.add(a)
    db.session.commit()
    return renderResultJson(None)


@app.route('/<page>')
def hello(page):
    print('get weibo')
    data = get_weibo(page);
    return jsonify({'success': True, 'data': data, 'message': 'suc'})


def get_page(page):
    try:
        url = 'https://m.weibo.cn/api/container/getIndex?type=uid&value=5687069307&containerid=1076035687069307&page='
        url += str(page)
        response = requests.get(url, headers=headers)
        # print(response.text)
        if response.status_code == 200:
            # print(response.json())
            return response.json()
    except requests.ConnectionError as e:
        print('Error', e.args)


def get_detail(id):
    try:
        # 展开全文
        url = 'https://m.weibo.cn/statuses/extend?id='
        url += str(id)
        response = requests.get(url, headers=headers)
        # print(response.text)
        if response.status_code == 200:
            # print(response.json())
            return response.json().get('data').get('longTextContent')
            # .replace('<br />', '\\n')
    except requests.ConnectionError as e:
        print('Error', e.args)


# 解析数据
def parse_page(json):
    # print(json)
    if json:
        items = json.get('data').get('cards')
        for index, item in enumerate(items):
            item = item.get('mblog')

            print("item: ", item)

            weibo = {}
            weibo['id'] = item.get('id')
            if item.get('text').strip():
                weibo['text'] = pq(item.get('text').strip()).text()
            else:
                weibo['text'] = ''
            # .replace('<br />', '\\n')
            weibo['attitudes'] = item.get('attitudes_count')
            weibo['comments'] = item.get('comments_count')
            weibo['reposts'] = item.get('reposts_count')
            weibo['original_pic'] = item.get('original_pic')
            pics = item.get('pics')
            pics_data = []
            if pics:
                for pic in pics:
                    pic_data = {}
                    pic_data['url'] = pic.get('url')
                    pic_data['large_url'] = pic.get('large').get('url')
                    pics_data.append(pic_data)
            weibo['pics'] = pics_data

            weibo['created_at'] = parse_time(item.get('created_at'))

            # weibo = []
            # weibo.append(item.get('id'))
            # weibo.append(pq(item.get('text')).text())
            # weibo.append(item.get('attitudes_count'))
            # weibo.append(item.get('comments_count'))
            # weibo.append(item.get('reposts_count'))
            # # 发出的图片
            # weibo.append(item.get('original_pic'))
            # 遇见重复数据，pass，是根据主键来判断，如果是重复数据，忽略，但是报警告
            # print(weibo)
            if weibo['text'].endswith('...全文'):
                weibo['text'] = get_detail(weibo['id'])
            yield weibo


def get_weibo(page):
    json = get_page(page)
    result = parse_page(json)
    weibo = []
    for res in result:
        weibo.append(res)
    return weibo


def parse_time(create_at):
    # 时间格式有3种, xx小时前, yyyy-MM-dd ,MM-dd, 昨天 HH:mm
    print('parse_time  create_at: ', create_at)

    minutes_index = create_at.find('分钟前')
    # print("hours_index : ", hours_index)
    if minutes_index >= 0:
        minutes = create_at[0:minutes_index]
        now = datetime.datetime.now()
        delta = datetime.timedelta(minutes=int(minutes))
        n_now = now - delta
        res = n_now.strftime('%Y-%m-%d %H:%M:%S')
        app.logger.debug(res)
        return res


    hours_index = create_at.find('小时前')
    # print("hours_index : ", hours_index)
    if hours_index >= 0:
        hours = create_at[0:hours_index]
        now = datetime.datetime.now()
        delta = datetime.timedelta(hours=int(hours))
        n_now = now - delta
        res = n_now.strftime('%Y-%m-%d %H:%M:%S')
        app.logger.debug(res)
        return res

    day_index = create_at.find('昨天')
    if day_index >= 0:
        now = datetime.datetime.now()
        delta = datetime.timedelta(days=1)
        n_now = now - delta
        res = n_now.strftime('%Y-%m-%d')
        res = (res + create_at[2:8])
        app.logger.debug(res)
        return res

    # MM-dd
    if len(create_at) == 5:
        now = datetime.datetime.now()
        res = now.strftime('%Y')
        res = (res + '-' + create_at)
        app.logger.debug(res)
        return res

    if create_at.find('+0800') > 0:
        f_date = parser.parse(create_at)
        return f_date.strftime('%Y-%m-%d %H:%M:%S')
    return create_at


wechat_token = {
    "expire": 0,
    "edit_at": datetime.datetime.now(),
    "token": ""
}

SECRET = os.getenv('wx_secret')
APP_ID = os.getenv('appId')
TEMPLATE_ID = "rJPdhomiyqgRfSkkP-VxopjMkVU8ZuLRIS1tpc9Q3SA"


def get_wechat_token():
    # 每请求一次, 减10s, 这个根据
    delta = datetime.datetime.now() - wechat_token["edit_at"]
    seconds = delta.seconds
    print("token产生时间(s): ", seconds)
    if wechat_token["token"] == "" or seconds > wechat_token["expire"]:
        # 请求获取 token
        url = "https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=" + APP_ID + "&secret=" + SECRET + ""
        response = requests.get(url)
        if response.status_code == 200:
            json = response.json()
            print('token: ', json)
            wechat_token["token"] = json.get("access_token")
            wechat_token["expire"] = json.get("expires_in")
            wechat_token["edit_at"] = datetime.datetime.now()
    return wechat_token["token"]


def get_openid(code):
    url = "https://api.weixin.qq.com/sns/jscode2session?appid=" + APP_ID + "&secret=" + SECRET + "&js_code=" + str(
        code) + "&grant_type=authorization_code"
    print('get_openid  url :', url)
    resp = requests.get(url)
    json = resp.json()
    print(json)
    return json.get('openid')


def send_wechat_msg():
    token = get_wechat_token()


@app.route('/send_msg/<openid>-<con>')
def send_singe_msg(openid, con):
    token = get_wechat_token()
    url = 'https://api.weixin.qq.com/cgi-bin/message/subscribe/send?access_token=' + token;
    now = datetime.datetime.now().strftime('%Y年%m月%d日 %H:%M')
    data = {'date2': {'value': now},
            'thing1': {'value': con},
            'thing3': {'value': 'E大发微博啦'},
            'thing4': {'value': 'weibo'}}

    temp_data = {'touser': openid, 'template_id': TEMPLATE_ID, 'page': 'pages/index/index', 'data': data,
                 'miniprogram_state': 'trial'}
    try:
        print(temp_data)
        resp = requests.post(url, json=temp_data)
        json = resp.json()
        print('send msg result: ', json)
        return renderResultJson(json)
    except RuntimeError as e:
        print('send msg error: ', e)

    return renderResultJson(None)


if __name__ == '__main__':
    # parse_time("16小时前")
    # parse_time("昨天 10:33")
    # parse_time("02-10")

    app.run(host="0.0.0.0", port=os.getenv("PORT", default=5050), debug=True)

