# -*- coding:utf-8 -*-

import datetime
import os
import re
import threading
import time

import paramiko


def mkdir():
    # 在文件所处位置建立文件夹保存输入和输出
    write_file_path = (
            "./"
            + datetime.datetime.now().strftime("%Y年")
            + "/"
            + datetime.datetime.now().strftime("%m月%d日")
            + "/"
    )
    # 去除首位空格
    path = write_file_path.strip()
    # 去除尾部 \ 符号
    path = path.rstrip("\\")
    # 判断路径是否存在
    # 存在     True
    # 不存在   False
    is_exists = os.path.exists(path)
    # 判断结果
    if not is_exists:
        # 如果不存在则创建目录
        # 创建目录操作函数
        os.makedirs(path)
        print(path + " 创建成功")
        return True
    else:
        # 如果目录存在则不创建，并提示目录已存在
        print(path + " 目录已存在")
        return False


def create_file(name, msg):
    # 将输出内容写入文件
    o_file_path = (
            "./"
            + datetime.datetime.now().strftime("%Y年")
            + "/"
            + datetime.datetime.now().strftime("%m月%d日")
            + "/"
    )
    o_full_path = (
            o_file_path + name + "-" + datetime.datetime.now().strftime("%Y-%m-%d") + ".txt"
    )
    o_file = open(o_full_path, "w")
    # 以覆盖方式写入
    o_file.write(msg)
    o_file.close()


def login_error(name, msg):
    o_file_path = (
            "./"
            + datetime.datetime.now().strftime("%Y年")
            + "/"
            + datetime.datetime.now().strftime("%m月%d日")
            + "/"
    )
    o_full_path = (
            o_file_path + name + "-" + datetime.datetime.now().strftime("%Y-%m-%d") + ".txt"
    )
    o_file = open(o_full_path, "a")
    # 以附加方式写入
    o_file.write(msg)
    o_file.close()


def show_more(device_info):
    # 回显如果有more，则输入空格直到显示完全
    all_result = b''
    tmp = b''
    if device_info.enable_passwd != '':
        # 如果有enable密码则需要进入使能模式
        device_info.command.send(device_info.enable_command + device_info.config_txt[0])
        for i in range(0, 10):
            if device_info.command.recv_ready():
                tmp = device_info.command.recv(1024)
            time.sleep(1)
            if re.search(rb'[pP][Aa][sS]{2}', tmp) is not None:
                break
            if i % 5 == 0:
                device_info.command.send(device_info.config_txt[0])
        device_info.command.send(device_info.enable_passwd + device_info.config_txt[0])
        time.sleep(1)
        if device_info.command.recv_ready():
            device_info.command.recv(1024)
    for num in range(0, len(device_info.config_txt)):
        device_info.command.send(
            device_info.config_txt[num] + device_info.config_txt[0])
        time.sleep(1)
        # 遇到more输入空格，到结尾停止，将所有输出内容导入all_result
        enter_space_times = 0
        same_times = 0
        prev_ssh_result = b' '
        while True:
            ssh_result = device_info.command.recv(10240)
            if ssh_result == b'':
                time.sleep(0.2)
                pass
            else:
                all_result = all_result + ssh_result
            if enter_space_times < 3:
                ssh_result = b''
            enter_space_times = enter_space_times + 1
            time.sleep(0.2)
            device_info.command.send(' ')
            if prev_ssh_result == ssh_result:
                device_info.command.send(device_info.config_txt[0])
                time.sleep(0.1)
                same_times = same_times + 1
            prev_ssh_result = ssh_result
            if same_times > 4:
                break
            # 确认输出结束后终止循环
    # print(all_result)
    all_result = clear_error_str(all_result, device_info)
    # 执行脚本清除more和异常字符
    return all_result


def clear_error_str(all_result, device_info):
    # 有时输出会异常，过滤掉输出异常的部分
    ansi_escape = re.compile(rb'''
        \x1B  # ESC
        (?:   # 7-bit C1 Fe (except CSI)
            [@-Z\\-_]
        |     # or [ for CSI, followed by a control sequence
            \[
            [0-?]*  # Parameter bytes
            [ -/]*  # Intermediate bytes
            [@-~]   # Final byte
        )
    ''', re.VERBOSE)
    ansi_escape2 = re.compile(rb'''
        [\s]?\x08
        |\r\x1b>
        |\x1b=\r
        |\n.*?\W\W[mM][oO][rR][eE]\W.*?\[16D
        |\x07
    ''', re.VERBOSE)
    replace_more = re.compile(rb'''
    (
        \n:\r
        |\n.*?\W\W[mM][oO][rR][eE]\W.*?\n
    )''', re.VERBOSE)
    rep_for_hw = re.compile(rb'''
    (
        \x1b\[16D.*?\[16D
    )''', re.VERBOSE)

    rep_for_rj = re.compile(rb'''
    (
        \x08\x08*\s*\x08*\x08
    )''', re.VERBOSE)

    delete_enter_rn = re.compile(rb'''
    (
        \r\s\s*\r
    )''', re.VERBOSE)

    # --------------------正则---------------------------------------
    if device_info.device_type == "huawei":
        all_result = rep_for_hw.sub(b'\n', all_result)
    # 匹配特定类型设备
    elif device_info.device_type == "ruijie":
        all_result = rep_for_rj.sub(b'\n', all_result)

    all_result = delete_enter_rn.sub(b'\n', all_result)
    # 去掉通用常见的异常\r
    all_result = re.sub(rb'\r\r*\s*\n', b'\n', all_result)
    # 去掉\r\n
    i = 0
    while i < 4:
        all_result = replace_more.sub(b'\n', all_result)
        i = i + 1
    all_result = ansi_escape2.sub(b'', all_result)
    all_result = ansi_escape.sub(b'', all_result)
    # 替换more和异常字符
    if device_info.device_type == "qimingxingcheng":
        all_result = all_result.decode("gb2312", "ignore")
    else:
        all_result = all_result.decode("utf-8", "ignore")
    # 将bytes转为str
    return all_result


class DeviceInfo:
    # 设置SSH连接信息
    ip = ""
    port = ""
    user = ""
    passwd = ""
    device_type = ""
    device_name = ""
    command = ''
    ssh_client = ''
    enable_passwd = ''
    enable_command = ''

    def __init__(self, ip, user, passwd):
        self.ip = ip
        self.port = 22
        self.passwd = passwd
        self.user = user
        self.ssh_client = ''
        self.command = ''
        self.config_txt = []
        self.enable_passwd = ''
        self.enable_command = ''

    def ssh_connect(self):
        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh_client.connect(
            hostname=self.ip, username=self.user, password=self.passwd, port=self.port)
        self.command = self.ssh_client.invoke_shell()
        try:
            self.config_txt = Config.device_type_list[self.device_type]
        except:
            self.device_type = 'none'
            self.config_txt = Config.device_type_list[self.device_type]
        try:
            self.enable_command = Config.device_enable_command[self.device_type]
        except:
            self.enable_command = 'enable'


class Config:
    # 设置命令
    Juniper = (
        "\n",
        "show system alarms",
        "show chassis alarms",
        "show chassis hardware",
        "show version",
        "show chassis environment",
        "show system uptime",
        "show chassis routing-engine",
        "show chassis fpc",
        "show virtual-chassis",
        "show virtual-chassis vc-port",
        "show interfaces descriptions",
        "show interfaces diagnostics optics | match \"phy|Receiver.*power[ ]{1,50}:\"",
        "show configuration | display set",
        " ",
    )
    # device_info.config_txt = brocade_config
    Brocade = (
        "\n",
        "show vcs",
        "show system monitor rb all",
        "show system rbridge-id all",
        "show run",
        " ",
    )
    # device_info.config_txt = ruijie_config
    Ruijie = (
        "\n",
        "show switch virtual",
        "show version",
        "show power",
        "show fan",
        "show run",
        " ",
    )
    # device_info.config_txt = firewall_config
    Hillstone = ("\n", "show configuration", " ")
    # device_info.config_txt = firewall_config
    Qiming = ("\n", "enable", "show run", " ")
    Huawei = (
        "\n",
        "display version",
        "display power",
        "display fan",
        "display device",
        "display cpu-usage",
        "display temperature all",
        "display current-configuration",
        " ",
    )
    H3c = (
        "\n",
        "display version",
        "display power",
        "display fan",
        "display device",
        "display cpu-usage",
        "display interface link-info | exclude \"down|-\"",
        "display cur",
        " ",
    )
    Centec = (
        "\r\n",
        "show cpu utilization",
        "show memory summary total",
        "show interface status",
        "show running-config",
        " ",
    )
    Aruba = (
        "\r\n",
        "encrypt disable",
        "show license",
        "show ap database long",
        "show memory",
        "show storage",
        "show vrrp",
        "show master-redundancy",
        "show switches",
        "show switches debug",
        "show database synchronize",
        "show ha ap table",
        "show running-config",
        "encrypt enable",
        " ",
    )
    # noinspection PyBroadException
    try:
        Test: list = ['\n'] + open("config.txt", "r", encoding='utf-8').readlines() + [" "]
    except:
        Test = ('\n', ' ')
    device_enable_command = {"huawei": "sys"}
    device_type_list = {"juniper": Juniper, "aruba": Aruba, "brocade": Brocade, "ruijie": Ruijie,
                        "hillstone": Hillstone, "qimingxingcheng": Qiming, "huawei": Huawei, "h3c": H3c,
                        "centec": Centec,
                        "none": Test}


def device_backup(get_line):
    with sem:
        data = get_line.split()
        # 初始化data并将每行数据以空格隔开，导入到data
        # noinspection PyBroadException
        try:
            this_device_info = DeviceInfo(data[0], data[1], data[2])
        except:
            return
        if len(data) > 3:
            this_device_info.device_type = data[3]
        if len(data) > 4 and data[4] != "'":
            this_device_info.device_name = data[4]
        else:
            this_device_info.device_name = this_device_info.ip
        if len(data) > 5 and data[5] != "'":
            this_device_info.port = data[5]
        if len(data) > 6 and data[6] != "'":
            this_device_info.enable_passwd = data[6]
        # 拆分line，为ssh_connect类赋值
        # noinspection PyBroadException
        try:
            this_device_info.ssh_connect()
        except:
            process_lock.acquire()
            try:
                print("无法登录 ", this_device_info.ip + ' ' +
                      this_device_info.device_name + '\n')
                login_error("无法登录的设备", this_device_info.ip + '\t' +
                            this_device_info.device_name + '\n')
            finally:
                process_lock.release()
            return
        # 尝试连接SSH，如果无法登录则锁定进程，在文件写入无法登录。最后解锁进程并返回
        enter_times: int = 0
        while 1:
            if this_device_info.command.recv_ready():
                ssh_result = this_device_info.command.recv(10240)
            time.sleep(0.5)
            this_device_info.command.send(this_device_info.config_txt[0])
            enter_times = enter_times + 1
            if enter_times > 2 and ssh_result != b'':
                break
            # 确认设备可以输入
            elif enter_times > 10:
                process_lock.acquire()
                try:
                    print("无法登录 ", this_device_info.ip + ' ' +
                          this_device_info.device_name + '\n')
                    login_error("无法登录的设备", this_device_info.ip + '\t' +
                                this_device_info.device_name + '\n')
                finally:
                    process_lock.release()
                    this_device_info.ssh_client.close()
                    return
        # 如果超过5秒还没有正常匹配等待字符dev_ready，跳过此设备
        process_lock.acquire()
        try:
            print("成功登录 " + this_device_info.ip + ' ' +
                  this_device_info.device_name + '\n')
        finally:
            process_lock.release()
        # 登录成功输出
        create_file(this_device_info.device_name + "-" +
                    this_device_info.device_type, show_more(this_device_info))
        # 执行输入命令行操作
        time.sleep(1)
        # 写入完成后，等待一秒后关闭连接
        this_device_info.ssh_client.close()


# ---------------------------------主函数--------------------------------------------------
mkdir()
# 创建写入文件夹
create_file("无法登录的设备", "")
device_info_file = open("iplist.txt", "r", encoding='utf-8')
# 读取需要访问的设备信息，打开文件
process_lock = threading.Lock()
sem = threading.Semaphore(20)  # 限制线程的最大数量为4个
threads = []
for line in device_info_file.readlines():
    if re.search(r'^#.*', line):
        continue
    # 从第一行开始逐行读取文件
    t = threading.Thread(target=device_backup, args=(line,))
    threads.append(t)
    t.start()
device_info_file.close()

for t in threads:
    t.join()
# 等待所有程序运行完成
print("全部工作已完成！\n")
