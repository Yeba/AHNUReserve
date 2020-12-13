import requests
import json
import datetime
from multiprocessing import Pool
from multiprocessing.dummy import Pool as ThreadPool
import time

DAY1 = str(datetime.date.today() + datetime.timedelta(days=1))
DAY2 = str(datetime.date.today() + datetime.timedelta(days=2))

JUST_ONE_SET = True  # 就认准这一个位置；失败换下一个位置
FROM_TIME = [23, 59, 50]  # 开始抢的时间
END_TIME = [0, 0, 50]

INFOs = [
    {
        'account': '171104',
        'password': '171104',
        'sid': 'nsk1201',
        'atDate': DAY1,
        'st': DAY1 + ' 08:00',
        'et': DAY1 + ' 22:00'
    },
    {
        'account': '171104',
        'password': '171104',
        'sid': 'nsk1202',
        'atDate': DAY1,
        'st': DAY1 + ' 08:00',
        'et': DAY1 + ' 22:00'
    },
]


class Reserve:
    def __init__(self, **kwargs):
        self.info = kwargs
        self.session = requests.Session()
        self.logok = False
        while not self.logok:
            self.login()

    def login(self):
        print('''start  with self.info['account']:{0}, self.info['password']:{1}, seatid:{2}. From {3} to {4}.'''
              .format(self.info['account'], self.info['password'], self.info['sid'], self.info['st'],
                      self.info['et']))

        # 开始登陆
        postUrl = 'http://libzwxt.ahnu.edu.cn/SeatWx/login.aspx'
        postData = {
            '__VIEWSTATE': '/wEPDwULLTE0MTcxNzMyMjZkZJoL/NVYL0T+r5y3cXpfEFEzXz+dxNVtb7TlDKf8jIxz',
            '__VIEWSTATEGENERATOR': 'F2D227C8',
            '__EVENTVALIDATION': '/wEWBQKV1czoDALyj/OQAgKXtYSMCgKM54rGBgKj48j5D1AZa5C6Zak6btNjhoHWy1AzD9qoyayyu5qGeLnFyXKG',
            'tbUserName': self.info['account'],
            'tbPassWord': self.info['password'],
            'Button1': '登 录',
            'hfurl': ''
        }
        headers = {
            # 'Connection': 'Keep-Alive',
            'Accept': 'text/html, application/xhtml+xml, */*',
            'Accept-Language': 'en-US,en;q=0.8,zh-Hans-CN;q=0.5,zh-Hans;q=0.3',
            'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.129 Safari/537.36 Edg/81.0.416.68"
        }

        login = self.session.post(postUrl, data=postData, headers=headers)

        if '个人中心' in login.content.decode():
            print('login successfully!')
            self.info['_sid'] = self.info['sid']
            self.info['sid'] = self.convert(self.info['sid'])
            self.logok = True
        else:
            print("login failed")

    @staticmethod
    def convert(seat_code):
        sid = 0
        if seat_code[:3] == 'nzr':
            sid = int(seat_code[3:]) + 437
        elif seat_code[:3] == 'nsk' and seat_code[3] == '1':
            sid = int(seat_code[3:]) + 95
        elif seat_code[:3] == 'nsk' and seat_code[3] == '3':
            sid = int(seat_code[3:]) - 2477
        elif seat_code[:3] == 'nsk' and seat_code[3] == '2':
            sid = int(seat_code[3:]) - 1177
        elif seat_code[:3] == 'nbz':
            sid = int(seat_code[3:])
        return sid


def reserve(self: Reserve):
    ok = False
    name = self.info['account']
    tab = self.info['_sid']
    try:
        # 开始预约
        print('name:{},set:{}  '.format(name, tab), 'begin to reserve...')
        header = {
            # 设定报文头
            'Host': 'libzwxt.ahnu.edu.cn',
            'Origin': 'http://libzwxt.ahnu.edu.cn',
            'Referer': 'http://libzwxt.ahnu.edu.cn/SeatWx/Seat.aspx?fid=3&sid=1438',
            'User-Agent': "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36",
            'X-AjaxPro-Method': 'AddOrder',
        }
        reserveUrl = 'http://libzwxt.ahnu.edu.cn/SeatWx/ajaxpro/SeatManage.Seat,SeatManage.ashx'
        reserverData = {
            'atDate': self.info['atDate'],
            'sid': self.info['sid'],
            'st': self.info['st'],
            'et': self.info['et'],
        }

        # 尝试进行预约
        reserve = self.session.post(reserveUrl, data=json.dumps(reserverData), headers=header)
        if '成功' in reserve.text:
            print('name:{},set:{}  '.format(name, tab), reserve.text)
            print('name:{},set:{}  '.format(name, tab),
                  'reserve successfully! Your seat id is {0}'.format(self.info['sid']))
            ok = True

        while '预约成功' not in reserve.text and not ok:
            dt = datetime.datetime.now()
            if dt.hour == END_TIME[0] and dt.minute == END_TIME[1] and dt.second >= END_TIME[1]:
                return
            # 预约未成功，再次尝试
            reserve = self.session.post(reserveUrl, data=json.dumps(reserverData), headers=header)

            # 服务器时间不一致
            if '提前' in reserve.text:
                print('name:{},set:{}  '.format(name, tab), '!! ', reserve.text)
                continue
            elif '冲突' or '重复' in reserve.text:
                # 时间和其他人有冲突，顺延下一个座位
                print('name:{},set:{}  '.format(name, tab), reserve.text)
                print('name:{},set:{}  '.format(name, tab), 'Appointment failed, trying to reserve another seat...')
                if not JUST_ONE_SET:
                    self.info['sid'] = str(int(self.info['sid']) + 1)
                continue
            elif '二次' in reserve.text:
                print('name:{},set:{}  '.format(name, tab), reserve.text)
                break
            elif '成功' in reserve.text:
                # 预约完成
                print('name:{},set:{}  '.format(name, tab), reserve.text)
                print('name:{},set:{}  '.format(name, tab),
                      'reserve successfully! Your seat id is {0}'.format(self.info['sid']))
                ok = True
                break
            else:
                print('name:{},set:{}  '.format(name, tab), reserve.text)
                print('name:{},set:{}  '.format(name, tab), 'error ', '未知原因，未预约成功，请检查日志及数据设置！！！')
    except BaseException as e:
        print('name:{},set:{}  '.format(name, tab), 'error ', e)


res = [Reserve(**info) for info in INFOs]
th_num = len(INFOs)
pool = ThreadPool(th_num)


def main():
    pool.map(reserve, res)
    pool.close()
    pool.join()


if __name__ == '__main__':
    print("waiting", end='')
    while True:
        dt = datetime.datetime.now()
        if dt.hour == FROM_TIME[0] and dt.minute == FROM_TIME[1] and dt.second >= FROM_TIME[2]:
            break
        time.sleep(0.1)
        print("\b\b\b\b\b\b\bwaiting", end='')
        continue
    print('开始！')
    main()
