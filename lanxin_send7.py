
import os
import sys
import time
import yaml
import shutil
import logging
import pyautogui
import pyperclip


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
    i1 = os.path.join(os.getcwd(), button['image'])
    print(i1)
    match_part = pyautogui.locateOnScreen(
        i1, confidence=0.9, grayscale=True
    )
    print(match_part)
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

def sendAndbak_file(channel_button, DOCS_DIR,fileName,BAK_DIR):
    """发送文件和消息到指定频道, 文件路径需为绝对路径"""
    #  判断文件存在
    file_path = os.path.join(DOCS_DIR)
    print('file_path----------'+str(file_path))
    if os.path.isfile(file_path) or os.path.isabs(file_path):
        file_bytes = os.path.getsize(file_path)
        file_dir, file_name = os.path.split(file_path)
    else:
        return False

    search_click(channel_button, do_click=True) # 找到频道
    time.sleep(1)
    search_click(CONF['LANXIN']['BUTTON_FILE'], do_click=True)    # 找到文件上传按钮
    time.sleep(2)

    # 这时弹出文件选择对话框
    pyautogui.press('f4')   # 切地址栏
    time.sleep(2)
    # 输入文件路径
    pyautogui.hotkey('ctrlleft', 'a')
    time.sleep(1)
    pyautogui.hotkey('delete')
    pyautogui.typewrite(file_path)
    time.sleep(2)
    pyautogui.hotkey('enter')
    time.sleep(2)
    # 输入文件名
    pyautogui.hotkey('altleft', 'n')
    time.sleep(3)
    pyperclip.copy(fileName)
    pyautogui.hotkey('ctrlleft', 'v')
    time.sleep(1)
    pyautogui.hotkey('enter')

    # 发送文件消息(pyguiauto不支持中文, 故采用粘贴方式)
    #pyperclip.copy(send_msg)
    #pyautogui.hotkey('ctrlleft', 'v')

    # 点击或回车发送
    time.sleep(2)
    pyautogui.hotkey('enter')
    logging.info('已发送文件' + fileName)
    # search_click(BUTTON_SEND, do_click=True)
    print('fileName:', fileName)
    src = os.path.join(DOCS_DIR, str(fileName))
    dst = os.path.join(BAK_DIR, str(fileName))
    print('src:', src)
    print('dst:', dst)
    shutil.move(src,dst)
    logging.info('已备份文件'+fileName)
    return True

def do_police(DOCS_DIR,BAK_DIR,CHANNEL_TARGET):
    """轮询SFTP服务器, 下载所有文件到本地后删除, 本地依次发送到蓝信快传助手"""
    # 查询最新文件清单下载到本地路径 \police\
    logger.info('遍历' + DOCS_DIR)
    files = os.listdir(DOCS_DIR)
    if len(files) > 0:
        for f in files:
            print(f)
                # 原文件名 -> xx_YYYYMMDD_NN.txt

             # 文件发送蓝信快传助手频道, f_path为绝对路径
            sendAndbak_file(CHANNEL_TARGET,DOCS_DIR,f,BAK_DIR)
            #sendAndbak_file(CONF['LANXIN']['CHANNEL_TARGET'], fullPathFileName)

            time.sleep(1)  # 避免连续发送失败


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
        print(CONF['LANXIN']['LOGO'])
        find_lanxin = search_click(CONF['LANXIN']['LOGO'], do_click=True)
        if find_lanxin is None:
            logger.debug('未找到蓝信主窗口(等待{}秒).'.format(CONF['APP']['CYCLE']))
            time.sleep(3)
            continue

        # 查询接口机(SFTP), 若有文件则下载
        do_police(CONF['APP']['DOCS_DIR1'],CONF['APP']['BAK_DIR1'],CONF['LANXIN']['CHANNEL_TARGET1'])
        do_police(CONF['APP']['DOCS_DIR2'],CONF['APP']['BAK_DIR2'],CONF['LANXIN']['CHANNEL_TARGET2'])

        logger.debug('轮询结束, 等待{}秒'.format(CONF['APP']['CYCLE']))
        time.sleep(CONF['APP']['CYCLE'])

if __name__ == '__main__':
    main()
    sys.exit(0)