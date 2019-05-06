import asyncio
from .utils import UtilsTask
from reqs.live_daily_job import (
    HeartBeatReq,
    RecvHeartGiftReq,
    OpenSilverBoxReq,
    RecvDailyBagReq,
    SignReq,
    WatchTvReq,
    SignFansGroupsReq,
    SendGiftReq,
    ExchangeSilverCoinReq,
)
from .task_func_decorator import unique
from .base_class import SchedTask


class HeartBeatTask(SchedTask):
    @staticmethod
    async def check(_):
        return (-2, (0, 30)),
        
    @staticmethod
    @unique
    async def work(user):
        while True:
            json_rsp = await user.req_s(HeartBeatReq.pc_heartbeat, user)
            # print(json_rsp)
            user.infos(['心跳包(5分钟左右间隔)'])
            json_rsp = await user.req_s(HeartBeatReq.app_heartbeat, user)
            print(json_rsp)
            await asyncio.sleep(300)

                
class RecvHeartGiftTask(SchedTask):
    @staticmethod
    async def check(_):
        return (-2, (0, 30)),
        
    @staticmethod
    @unique
    async def work(user):
        while True:
            json_rsp = await user.req_s(RecvHeartGiftReq.recv_heartgift, user)
            if json_rsp['code'] == 400:
                user.fall_in_jail()
                return
            await asyncio.sleep(300)
 
               
class OpenSilverBoxTask(SchedTask):
    @staticmethod
    async def check(_):
        return (-2, (0, 30)),
                
    @staticmethod
    @unique
    async def work(user):
        while True:
            user.infos(["检查宝箱状态"])
            temp = await user.req_s(OpenSilverBoxReq.check_time, user)
            # print (temp['code'])    #宝箱领完返回的code为-10017
            if temp['code'] == -10017:
                user.infos(["今日宝箱领取完毕"])
                json_rsp = None
            else:
                time_start = temp['data']['time_start']
                time_end = temp['data']['time_end']
                json_rsp = await user.req_s(OpenSilverBoxReq.open_silver_box, user, time_start, time_end)
            if json_rsp is None or json_rsp['code'] == -10017 or json_rsp['code'] == -800:
                return
            elif not json_rsp['code']:
                user.infos(["打开了宝箱"])
            elif json_rsp['code'] == 400:
                user.infos(["宝箱开启中返回了小黑屋提示"])
                user.fall_in_jail()
                # 马上继续调用，由下一次的user去supend这个task
                return
            else:
                user.infos(["继续等待宝箱冷却..."])
                sleeptime = (json_rsp['data'].get('surplus', 3)) * 60 + 5
                await asyncio.sleep(sleeptime)
                
                
class RecvDailyBagTask(SchedTask):
    @staticmethod
    async def check(_):
        return (-2, (0, 30)),
        
    @staticmethod
    @unique
    async def work(user):
        json_rsp = await user.req_s(RecvDailyBagReq.recv_dailybag, user)
        try:
            json_rsp['data']['bag_list']
        except TypeError:
            user.warn(f'recv_dailybag {json_rsp}')
        for i in json_rsp['data']['bag_list']:
            user.infos([f'获得-{i["bag_name"]}-成功'])

                
class SignTask(SchedTask):
    @staticmethod
    async def check(_):
        return (-2, (0, 30)),
        
    @staticmethod
    @unique
    async def work(user):
        while True:
            json_rsp = await user.req_s(SignReq.sign, user)
            user.infos([f'签到状态: {json_rsp["msg"]}'])
            if json_rsp['code'] == -500 and '已' in json_rsp['msg']:
                return
            sleeptime = 350
            await asyncio.sleep(sleeptime)
        
        
class WatchTvTask(SchedTask):
    @staticmethod
    async def check(_):
        return (-2, (0, 30)),
   
    @staticmethod
    @unique
    async def work(user):
        while True:
            # -400 done/not yet
            json_rsp = await user.req_s(WatchTvReq.watch_tv, user)
            user.infos([f'双端观看直播:  {json_rsp["msg"]}'])
            if json_rsp['code'] == -400 and '已' in json_rsp['msg']:
                return
            sleeptime = 350
            await asyncio.sleep(sleeptime)
        
        
class SignFansGroupsTask(SchedTask):
    @staticmethod
    async def check(_):
        return (-2, (0, 30)),
   
    @staticmethod
    @unique
    async def work(user):
        json_rsp = await user.req_s(SignFansGroupsReq.fetch_groups, user)
        for group in json_rsp['data']['list']:
            group_id = group['group_id']
            owner_uid = group['owner_uid']
            json_rsp = await user.req_s(SignFansGroupsReq.sign_group, user, group_id, owner_uid)
            if not json_rsp['code']:
                data = json_rsp['data']
                if data['status']:
                    user.infos([f'应援团 {group_id} 已应援过'])
                else:
                    user.infos([f'应援团 {group_id} 应援成功,获得 {data["add_num"]} 点亲密度'])
            else:
                user.infos([f'应援团 {group_id} 应援失败'])
            
            
class SendGiftTask(SchedTask):
    @staticmethod
    async def check(_):
        return (-2, (0, 30)),
        
    @staticmethod
    async def fetch_giftbags(user):
        gift_bags = await UtilsTask.fetch_giftbags(user)
        results = []
        for bag_id, gift_id, gift_num, _, _, left_time in gift_bags:
            results.append([gift_id, gift_num, bag_id, left_time])
        return results
        
    @staticmethod
    async def fetch_wearing_medal(user):
        json_rsp = await user.req_s(SendGiftReq.fetch_wearing_medal, user)
        if not json_rsp['code']:
            data = json_rsp['data']
            if data:
                room_id = data['roominfo']['room_id']
                remain_intimacy = int(data['day_limit']) - int(data['today_feed'])
                medal_name = data['medal_name']
                return [(room_id, remain_intimacy, medal_name), ]
            else:
                # print('暂无佩戴任何勋章')
                return []
    
    @staticmethod
    async def send_expiring_gift(user):
        if not user.task_ctrl['clean-expiring-gift']:
            return
        gift_bags = await SendGiftTask.fetch_giftbags(user)
        room_id = user.task_ctrl['clean-expiring-gift2room']
        time_set = user.task_ctrl['set-expiring-time']
        # filter 用过期来过滤
        expiring_giftbags = []
        for gift in gift_bags:
            left_time = gift[3]
            if left_time is not None and 0 < int(left_time) < time_set:
                expiring_giftbags.append(gift[:3])
        if expiring_giftbags:
            print('发现即将过期的礼物')
            if user.task_ctrl['clean_expiring_gift2all_medal']:
                print('正在清理过期礼物到用户勋章')
                medals = await UtilsTask.fetch_medals(user)
                expiring_giftbags = await SendGiftTask.fill_intimacy(user, expiring_giftbags, medals)
                
            print('正在清理过期礼物到指定房间')
            for gift_id, gift_num, bag_id in expiring_giftbags:
                await UtilsTask.send_gift(user, room_id, gift_num, bag_id, gift_id)
        else:
            print('未发现即将过期的礼物')
    
    @staticmethod
    async def send_medal_gift(user):
        medals = []
        if user.task_ctrl['send2wearing-medal']:
            medals = await SendGiftTask.fetch_wearing_medal(user)
            if not medals:
                print('暂未佩戴任何勋章')
        if user.task_ctrl['send2medal']:
            medals += await UtilsTask.fetch_medals(user, user.task_ctrl['send2medal'])
        # print('目前的勋章', medals)
        
        print('正在投递勋章')
        gift_bags = await SendGiftTask.fetch_giftbags(user)
        # print(temp)
        send_giftbags = []
        for gift in gift_bags:
            gift_id = int(gift[0])
            left_time = gift[3]
            # 过滤某些特定礼物以及永久礼物
            if (gift_id not in [4, 3, 9, 10]) and left_time is not None:
                send_giftbags.append(gift[:3])
        await SendGiftTask.fill_intimacy(user, send_giftbags, medals)
        
    @staticmethod
    async def fill_intimacy(user, gift_bags, medals):
        json_rsp = await user.req_s(SendGiftReq.fetch_gift_config, user)
        gift_price = {gift['id']: (gift['price'] / 100) for gift in json_rsp['data']}
        for room_id, remain_intimacy, medal_name in medals:
            filled_intimacy = 0
            for gift in gift_bags:
                gift_id, gift_num, bag_id = gift
                if gift_num * gift_price[gift_id] <= remain_intimacy:
                    num_sent = gift_num
                elif remain_intimacy >= gift_price[gift_id]:
                    num_sent = int(remain_intimacy / gift_price[gift_id])
                else:
                    continue
                gift[1] -= num_sent
                score = gift_price[gift_id] * num_sent
                await UtilsTask.send_gift(user, room_id, num_sent, bag_id, gift_id)
                filled_intimacy += score
                remain_intimacy -= score
            user.infos([f'对 {medal_name} 共送出亲密度为{filled_intimacy}的礼物'])
        # 过滤掉送光了的礼物包
        return [gift for gift in gift_bags if gift[1]]
        
    @staticmethod
    @unique
    async def work(user):
        await SendGiftTask.send_medal_gift(user)
        await SendGiftTask.send_expiring_gift(user)

                
class ExchangeSilverCoinTask(SchedTask):
    @staticmethod
    async def check(_):
        return (-2, (0, 30)),
     
    @staticmethod
    @unique
    async def work(user):
        while True:
            if not user.task_ctrl['silver2coin']:
                return
            json_rsp = await user.req_s(ExchangeSilverCoinReq.silver2coin_web, user)
            user.infos([f'{json_rsp["msg"]}'])
            if json_rsp['code'] == 403 and '最多' in json_rsp['msg']:
                finish_web = True
            else:
                finish_web = False
            if finish_web:
                return
            sleeptime = 350
            await asyncio.sleep(sleeptime)
