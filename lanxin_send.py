
import os
import sys
import time
import yaml
import re
import shutil
import logging
import paramiko
import pyautogui
import pyperclip
from ftplib import FTP


# 读取yaml配置
f = open(os.path.join(os.getcwd(), 'config.yaml'), encoding='utf-8')
CONF = yaml.load(f, Loader=yaml.FullLoader)

# 设置日志
logging.getLogger().setLevel(logging.DEBUG)
logger = logging.getLogger()
fh = logging.FileHandler(CONF['APP']['LOG_FILE'], mode='a')
fh.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
fh_formatter = logging.Formatter("%(asctime)s - %(filename)s[%(lineno)d] - %(levelname)s: %(message)s")
ch_formatter = logging.Formatter("%(asctime)s: %(message)s")
fh.setFormatter(fh_formatter)
ch.setFormatter(ch_formatter)
logger.addHandler(fh)
logger.addHandler(ch)

def search_click(button, do_move=True, do_click=False):
    """
    按特定图片搜索位置, 若存在, 则将鼠标移动到搜索结果位置, 或进行点击
    button: 被搜索点击区域 {'img':'', 'offset': (x, y)}
        image: 被搜索的图片, offset: 搜索中心与要点击的位置的偏移
    do_move: 是否移动鼠标
    do_click: 是否鼠标单击

    若成功找到则返回被选中位置坐标, 若失败则返回None
    """
    match_part = pyautogui.locateOnScreen(
        os.path.join(os.getcwd(), button['image']), confidence=0.9, grayscale=True
    )
    if match_part:
        center = pyautogui.center(match_part)
        click_x = center.x + eval(button['offset'])[0]
        click_y = center.y + eval(button['offset'])[1]
        time.sleep(1)
        if do_click or do_move:
            pyautogui.moveTo(click_x, click_y)
        if do_click:
            pyautogui.click(click_x, click_y, 1)
        return (click_x, click_y)
    else:
        return

def get_ssh_file(host, port, username, password, remote_dir, local_dir, do_remove=False):
    """获取SFTP服务器上执行目录所有文件, 下载到本地后删除, 返回文件列表"""
    try:
        transport = paramiko.Transport((host, port))
        transport.banner_timeout = 10
        transport.connect(None, username=username, password=password)
        sftp = paramiko.SFTPClient.from_transport(transport)

        files = sftp.listdir(remote_dir)
        print(files)
        for f in files:
            sftp.get(os.path.join(remote_dir, f), os.path.join(local_dir, f))
            if do_remove:
                sftp.remove(os.path.join(remote_dir, f))

        transport.close()
    except Exception as e:
        print('下载文件异常:', str(e))
        return []
    else:
        return files

def send_file(channel_button, file_path, send_msg):
    """发送文件和消息到指定频道, 文件路径需为绝对路径"""
    #  判断文件存在
    if os.path.isfile(file_path) and os.path.isabs(file_path):
        file_bytes = os.path.getsize(file_path)
        file_dir, file_name = os.path.split(file_path)
    else:
        return False

    search_click(channel_button, do_click=True) # 找到频道
    time.sleep(1)
    search_click(CONF['LANXIN']['BUTTON_FILE'], do_click=True)    # 找到文件上传按钮
    time.sleep(5)
    
    # 这时弹出文件选择对话框
    pyautogui.press('f4')   # 切地址栏
    time.sleep(3)
    # 输入文件路径
    pyautogui.hotkey('ctrlleft', 'a')
    time.sleep(1)
    pyautogui.hotkey('delete')
    pyautogui.typewrite(file_dir)
    time.sleep(2)
    pyautogui.hotkey('enter')
    time.sleep(2)
    # 输入文件名
    pyautogui.hotkey('altleft', 'n')
    time.sleep(1)
    pyperclip.copy(file_name)
    pyautogui.hotkey('ctrlleft', 'v')
    time.sleep(1)
    pyautogui.hotkey('enter')

    # 发送文件消息(pyguiauto不支持中文, 故采用粘贴方式)
    pyperclip.copy(send_msg)
    pyautogui.hotkey('ctrlleft', 'v')

    # 点击或回车发送
    time.sleep(2)
    pyautogui.hotkey('enter')
    # search_click(BUTTON_SEND, do_click=True)
    return True

def do_police():
    """轮询SFTP服务器, 下载所有文件到本地后删除, 本地依次发送到蓝信快传助手"""
    # 查询最新文件清单下载到本地路径 \police\
    logger.info('查询公安数据')
    files = get_ssh_file(
        CONF['SOURCE']['HOST'], CONF['SOURCE']['PORT'],
        CONF['SOURCE']['USERNAME'], CONF['SOURCE']['PASSWORD'],
        CONF['SOURCE']['PATH'], CONF['SOURCE']['SAVE_DIR'], True
    )
    if len(files) > 0:
        for f in files:
            if re.match(r'^xxxxxx<数据库导出文件命名>xxxxx$', f):
                # 原文件名 -> xx_YYYYMMDD_NN.txt
                new_name = 'xx_{}_{}.txt'.format(f[-14:-6], f[-6:-4])
                os.rename(
                    os.path.join(CONF['SOURCE']['SAVE_DIR'], f),
                    os.path.join(CONF['SOURCE']['SAVE_DIR'], new_name)
                )
                # 文件发送蓝信快传助手频道, f_path为绝对路径
                send_file(CONF['LANXIN']['CHANNEL_TARGET'], os.path.join(CONF['SOURCE']['SAVE_DIR'], new_name), '')
                
                time.sleep(60)  # 避免连续发送失败
            else:   # 文件名称不符合情况
                logger.error('待发送公安数据文件名称不符合:{}'.foramt(f))

def main():
    """主线程"""
    size = pyautogui.size()
    # 因pyautogui库适配高分屏及缩放情况不好, 请确认屏幕分辨率和截图一致
    logger.debug('----------------------------------------------')
    logger.debug('屏幕分辨率: %d x %d' % (size.width, size.height))
    logger.debug('请确认以上屏幕分辨率正确!')
    
    err_flag = False
    while not err_flag:
        logger.debug('轮询开始')
        
        # 确认蓝信窗口存在, 未被阻挡
        find_lanxin = search_click(CONF['LANXIN']['LOGO'], do_click=True)
        if find_lanxin is None:
            logger.debug('未找到蓝信主窗口(等待{}秒).'.format(CONF['APP']['CYCLE']))
            time.sleep(CONF['APP']['CYCLE'])
            continue
        
        # 查询接口机(SFTP), 若有文件则下载
        do_police()

        logger.debug('轮询结束, 等待{}秒'.format(CONF['APP']['CYCLE']))
        time.sleep(CONF['APP']['CYCLE'])

if __name__ == '__main__':
    main()
    sys.exit(0)