import random
import asyncio
from operator import itemgetter

import printer
from reqs.utils import UtilsReq


class UtilsTask:
    @staticmethod
    async def enter_room(user, room_id):
        if not room_id:
            return
        await user.req_s(UtilsReq.post_watching_history, user, room_id)
    
    @staticmethod
    async def is_normal_room(user, roomid):
        if not roomid:
            return True
        json_response = await user.req_s(UtilsReq.init_room, user, roomid)
        if not json_response['code']:
            data = json_response['data']
            param1 = data['is_hidden']
            param2 = data['is_locked']
            param3 = data['encrypted']
            if any((param1, param2, param3)):
                printer.infos([f'抽奖脚本检测到房间{roomid:^9}为异常房间'])
                return False
            else:
                printer.infos([f'抽奖脚本检测到房间{roomid:^9}为正常房间'])
                return True
    
    @staticmethod
    async def get_room_by_area(user, area_id, room_id=None):
        # None/0 都不行
        if room_id is not None and room_id:
            if await UtilsTask.is_ok_as_monitor(user, room_id, area_id):
                return room_id
        if area_id == 1:
            room_id = 23058
            if await UtilsTask.is_ok_as_monitor(user, room_id, area_id):
                return room_id
                
        while True:
            json_rsp = await user.req_s(UtilsReq.get_rooms_by_area, user, area_id)
            data = json_rsp['data']
            room_id = random.choice(data)['roomid']
            if await UtilsTask.is_ok_as_monitor(user, room_id, area_id):
                return room_id
                
    @staticmethod
    async def is_ok_as_monitor(user, room_id, area_id):
        json_response = await user.req_s(UtilsReq.init_room, user, room_id)
        data = json_response['data']
        is_hidden = data['is_hidden']
        is_locked = data['is_locked']
        is_encrypted = data['encrypted']
        is_normal = not any((is_hidden, is_locked, is_encrypted))
                
        json_response = await user.req_s(UtilsReq.get_room_info, user, room_id)
        data = json_response['data']
        is_open = True if data['live_status'] == 1 else False
        current_area_id = data['parent_area_id']
        # print(is_hidden, is_locked, is_encrypted, is_open, current_area_id)
        is_ok = (area_id == current_area_id) and is_normal and is_open
        return is_ok
        
    @staticmethod
    async def send_gift(user, room_id, num_sent, bag_id, gift_id):
        if not num_sent or not room_id:
            return
        json_rsp = await user.req_s(UtilsReq.init_room, user, room_id)
        # TODO FIX
        try:
            ruid = json_rsp['data']['uid']
        except ValueError:
            user.warn(f'send_gift {json_rsp}')
        biz_id = json_rsp['data']['room_id']
        # 200027 不足数目
        json_rsp = await user.req_s(UtilsReq.send_gift, user, gift_id, num_sent, bag_id, ruid, biz_id)
        # print(json_rsp)
        if not json_rsp['code']:
            data = json_rsp['data']
            print(f'# 送给房间{room_id:^9}礼物: {data["gift_name"]}X{data["gift_num"]}')
        else:
            print("# 错误", json_rsp['msg'])
            
    @staticmethod
    async def buy_gift(user, room_id, num_sent, coin_type, gift_id):
        if not num_sent or not room_id:
            return
        json_rsp = await user.req_s(UtilsReq.init_room, user, room_id)
        ruid = json_rsp['data']['uid']
        biz_id = json_rsp['data']['room_id']
        # 200027 不足数目
        json_rsp = await user.req_s(UtilsReq.buy_gift, user, gift_id, num_sent, ruid, biz_id, coin_type)
        if not json_rsp['code']:
            data = json_rsp['data']
            print(f'# 送给房间{room_id:^9}礼物: {data["gift_name"]}X{data["gift_num"]}')
        else:
            print("# 错误", json_rsp['msg'])
            
    @staticmethod
    async def fetch_giftbags(user):
        json_rsp = await user.req_s(UtilsReq.fetch_giftbags, user)
        gift_bags = []
        cur_time = json_rsp['data']['time']
        for gift in json_rsp['data']['list']:
            bag_id = gift['bag_id']
            gift_id = gift['gift_id']
            gift_num = gift['gift_num']
            gift_name = gift['gift_name']
            expire_at = gift['expire_at']
            left_time = expire_at - cur_time
            if not expire_at:
                left_days = '+∞'.center(6)
                left_time = None
            else:
                left_days = round(left_time / 86400, 1)
            gift_bags.append((bag_id, gift_id, gift_num, gift_name, left_days, left_time))
        return gift_bags

    # medals_wanted [roomid0, roomid1 …]
    @staticmethod
    async def fetch_medals(user, medals_wanted=None):
        json_rsp = await user.req_s(UtilsReq.fetch_medals, user)
        # print(json_rsp)
        medals = []
        if not json_rsp['code']:
            for medal in json_rsp['data']['fansMedalList']:
                # 有的房间封禁了
                if 'roomid' in medal:
                    room_id = medal['roomid']
                    remain_intimacy = int(medal['dayLimit']) - int(medal['todayFeed'])
                    medal_name = medal['medal_name']
                    level = medal['level']
                    medals.append((room_id, remain_intimacy, medal_name, level))

            if medals_wanted is not None:
                results = []
                for room_id in medals_wanted:
                    for medal in medals:
                        if medal[0] == room_id:
                            results.append(medal[:3])
                            break
            else:
                results = [medal[:3] for medal in sorted(medals, key=itemgetter(3), reverse=True)]
            return results
    
    @staticmethod
    async def open_capsule(user, num_opened):
        if num_opened not in (1, 10, 100):
            print('只能输入1或10或100')
            return
        json_rsp = await user.req_s(UtilsReq.open_capsule, user, num_opened)
        if not json_rsp['code']:
            for i in json_rsp['data']['text']:
                print(i)
                
    @staticmethod
    async def get_real_roomid(user, room_id):
        json_rsp = await user.req_s(UtilsReq.init_room, user, room_id)
        if not json_rsp['code']:
            print('查询结果:')
            data = json_rsp['data']
            if not data['short_id']:
                print('# 此房间无短房号')
            else:
                print(f'# 短号为:{data["short_id"]}')
            print(f'# 真实房间号为:{data["room_id"]}')
            return data['room_id']
        # 房间不存在
        elif json_rsp['code'] == 60004:
            print(json_rsp['msg'])
            
    @staticmethod
    async def check_uid_by_roomid(user, room_id):
        json_rsp = await user.req_s(UtilsReq.init_room, user, room_id)
        if not json_rsp['code']:
            uid = json_rsp['data']['uid']
            print(f'房间号{room_id}对应的UID为{uid}')
            return int(uid)
        return None
            
    @staticmethod
    async def send_danmu(user, msg, room_id):
        json_rsp = await user.req_s(UtilsReq.send_danmu, user, msg, room_id)
        print(json_rsp)

    @staticmethod
    async def uid2name(user, uid):
        json_rsp = await user.req_s(UtilsReq.uid2name, user, uid)
        print('fetch uname', json_rsp)
        assert not json_rsp['code']
        return json_rsp['data'].get('uname')

    @staticmethod
    async def follow_user(user, uid):
        json_rsp = await user.req_s(UtilsReq.follow_user, user, uid)
        print('follow', json_rsp)
        if not json_rsp['code']:
            user.infos([f'用户关注{uid}成功'])
            return True
        user.warn(f'用户关注{uid}失败,{json_rsp}')
        return False

    @staticmethod
    async def unfollow(user, uid):
        while True:
            await user.req_s(UtilsReq.unfollow_user, user, uid)
            await asyncio.sleep(1)
            is_following, _ = await UtilsTask.check_follow(user, uid)
            if not is_following:
                user.infos([f'用户取关{uid}成功'])
                return True
            await asyncio.sleep(0.5)

    @staticmethod
    async def check_follow(user, uid):
        json_rsp = await user.req_s(UtilsReq.check_follow, user, uid)
        assert not json_rsp['code']
        # 0/uid
        is_following = int(json_rsp['data']['mid']) == int(uid)
        # tag none/[list] 不包含默认分组
        tag = json_rsp['data']['tag']
        if tag is None:
            group_ids = []
        else:
            group_ids = tag
        return is_following, group_ids

    @staticmethod
    async def fetch_group_id(user, group_name, read_only=False):
        json_rsp = await user.req_s(UtilsReq.fetch_follow_groupids, user)
        print('查询分组情况', json_rsp)
        assert not json_rsp['code']
        for group in json_rsp['data']:
            if group['name'] == group_name:
                return int(group['tagid'])
        if read_only:
            return None
        print(f'没有名为{group_name}分组, 正在创建新群组')
        json_rsp = await user.req_s(UtilsReq.create_follow_group, user, group_name)
        print('new group', json_rsp)
        return int(json_rsp['data']['tagid'])

    @staticmethod
    async def move2follow_group(user, uid, group_id):
        json_rsp = await user.req_s(UtilsReq.move2follow_group, user, uid, group_id)
        print('move2group', json_rsp)
        return
