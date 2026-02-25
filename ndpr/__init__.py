import os
import toml
import requests
import sqlite3
import threading
from typing import Optional, Dict
from mcdreforged import *
from mcdreforged.api.rtext import *


config = None
config_path = None
data_dir = None
ban_db_path = None
download_task = None
version = 1.0


def on_load(server: PluginServerInterface, prev_module):
    try:
        global config, config_path, data_dir, ban_db_path
        config_path = os.path.join(server.get_data_folder(), 'config.toml')
        init_config(server)
        setup_logger(server)
        config_dir = os.path.dirname(config_path)
        data_dir = os.path.join(config_dir, 'data')
        ban_db_path = os.path.join(data_dir, 'ban_database.db')
        os.makedirs(data_dir, exist_ok=True)
        server.logger.info(f'UUID: {config.get("uuid", "未设置")}')
        if not config.get('uuid'):
            server.logger.info('正在获取UUID...')
            obtain_uuid(server)

        register_commands(server)
        onlinemode = config.get('onlinemode')
        server.register_help_message('!!ndpr', 'NDPR主命令')
        server.register_event_listener('MCDRPlayerJoinedEvent', on_player_joined)
        download_ban_database(server)
        check_plugin_update(server)
        server.logger.info('NDPR插件已加载')
    except Exception as e:
        # 配置错误已经在 init_config 中处理，不需要额外处理
        # 让异常正常抛出，MCDR 会显示 Traceback 但插件会保持禁用状态
        raise


def on_unload(server: PluginServerInterface):
    global download_task
    server.logger.info('NDPR插件已卸载')


def init_config(server: PluginServerInterface):
    global config

    if not os.path.exists(config_path):
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        # 生成带注释的 TOML 配置文件
        config_content = """
#=======================================
# NDPR 配置文件
# NDPR Config
#=======================================
#信息(INFO)
#    - 官网：https://ndpreforged.com
#    - Webside：https://ndpreforged.com
#    - QQ群：232760327
#    - QQGroup：232760327
#=======================================
# API 地址，通常不需要修改
#API URL,usually does not need to be modified
#=======================================
api_url = "https://api.ndpreforged.com"
#=======================================
# Token(必填)
# Token (required)
# 带上你的UUID前往 https://ndpreforged.com 官网绑定邮箱后自动发放
# Bring your UUID with you to go https://ndpreforged.com Automatically distribute after binding email on the official website
# 如果需要启用封禁功能，必须配置此项
# If the ban function needs to be enabled, this item must be configured
#=======================================
token = ""
#=======================================
# UUID
# 首次启动时会自动获取，无需手动填写
# It will automatically get when it is first started, no need to fill in manually
#=======================================
uuid = ""
#=======================================
# 服务器模式(必填)
# Server type (required)
# true = 正版服 (Online Server)
# false = 离线服 (Offline Server)
# 注意：必须填写此选项，否则插件不会正常加载
# Note: This option must be filled in, otherwise the plugin will not load normally
#=======================================
onlinemode = ""
#=======================================
# 日志文件路径
# Log file path
#=======================================
log_path = "server/logs/latest.log"
#=======================================
# 日志处理模式
# Logger mode
# default = 默认模式
# custom = 自定义日志处理
#=======================================
logger_mode = "default"
#=======================================
# 自定义日志格式（仅在 logger_mode = "custom" 时生效）
# Custom logger format (only effective when logger_mode = "custom")
# 占位符说明：
# %n% = 不检测该处内容(None)
# %s% = 空格(Space)
# %name% = 玩家名(Player ID)
# %message% = 消息内容(Massage)
# 默认格式示例：<[头衔]>玩家名 <信息内容>
# Default format example: <[Title]>Player ID <Massage>
#=======================================
logger_format = "<[%n%]%name%>%s%<%message%>"
#=======================================
# 封禁列表更新间隔（秒）
# Ban list update interval (seconds)
# 默认900秒(15分钟)
# Default 900 seconds = 15 minutes
#=======================================
download_interval = 900
#=======================================

"""
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(config_content)
        with open(config_path, 'r', encoding='utf-8') as f:
            config = toml.load(f)
        server.logger.info('正在尝试获取UUID...')
        obtain_uuid(server)
    else:
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = toml.load(f)
        except Exception as e:
            server.logger.error(f'读取配置文件失败: {e}')
            server.logger.error('请确保配置文件为有效的 TOML 格式')
            raise

        onlinemode = config.get('onlinemode')
        if onlinemode == '':
            server.logger.error('请在ndpr配置文件里填写服务器类型(正版或离线),否则插件不会加载')
            server.logger.error('请在ndpr配置文件里填写服务器类型(正版或离线),否则插件不会加载')
            server.logger.error('请在ndpr配置文件里填写服务器类型(正版或离线),否则插件不会加载')
            server.logger.error('请在ndpr配置文件里填写服务器类型(正版或离线),否则插件不会加载')
            server.logger.error('请在ndpr配置文件里填写服务器类型(正版或离线),否则插件不会加载')
            on_unload(server)
            raise Exception('插件卸载')

        if isinstance(onlinemode, str):
            onlinemode = onlinemode.lower() == 'true'
            config['onlinemode'] = onlinemode

        logger_mode = config.get('logger_mode', 'default')
        log_path = config.get('log_path', 'server/logs/latest.log')
        server.logger.info(f'服务器类型: {"正版" if onlinemode else "离线"}')
        check_config_completeness(server)
        validate_config(server)


def validate_config(server: PluginServerInterface):
    global config
    errors = []

    api_url = config.get('api_url')
    if not api_url or not isinstance(api_url, str):
        errors.append('api_url 格式错误')
    elif not api_url.startswith('http://') and not api_url.startswith('https://'):
        errors.append('api_url请求头格式错误')
    token = config.get('token')
    if token is None:
        errors.append('token 格式错误')
    elif not isinstance(token, str):
        errors.append('token 格式错')

    # 验证 uuid（可以为空，但不能是 None）
    uuid = config.get('uuid')
    if uuid is None:
        errors.append('uuid 格式错误')
    elif not isinstance(uuid, str):
        errors.append('uuid 格式错误')
    elif uuid and len(uuid) != 36:
        errors.append('uuid 格式错误')

    # 验证 onlinemode（必须是布尔值）
    onlinemode = config.get('onlinemode')
    if not isinstance(onlinemode, bool):
        errors.append('onlinemode 必须是true 或 false')

    # 验证 log_path
    log_path = config.get('log_path')
    if not log_path or not isinstance(log_path, str):
        errors.append('log_path 格式错误')

    # 验证 logger_mode
    logger_mode = config.get('logger_mode')
    if logger_mode not in ['default', 'custom']:
        errors.append('logger_mode 必须是 "default" 或 "custom"')

    # 验证 logger_format
    logger_format = config.get('logger_format')
    if not logger_format or not isinstance(logger_format, str):
        errors.append('logger_format 格式错误')

    # 验证 download_interval（必须是正整数）
    download_interval = config.get('download_interval')
    if not isinstance(download_interval, int) or download_interval <= 0:
        errors.append('download_interval 格式错误')

    # 如果有错误，输出并抛出异常
    if errors:
        server.logger.error('配置文件参数格式错误:')
        for error in errors:
            server.logger.error(f'  - {error}')
        server.logger.error('请检查 config.toml 配置文件')
        on_unload(server)
        raise Exception('配置文件格式错误')

def setup_logger(server: PluginServerInterface):
    global config

    logger_mode = config.get('logger_mode', 'default')

    if logger_mode == 'custom':
        custom_format = config.get('logger_format', '<[%ip%]%name%>]%s%>%s%<%message%>')
        server.logger.info(f'使用自定义日志格式: {custom_format}')


def check_config_completeness(server: PluginServerInterface):
    global config, config_path

    required_keys = ['api_url', 'token', 'uuid', 'onlinemode', 'log_path', 'logger_mode', 'logger_format', 'download_interval']
    missing_keys = []

    for key in required_keys:
        if key not in config:
            missing_keys.append(key)

    if missing_keys:
        defaults = {
            'log_path': 'server/logs/latest.log',
            'download_interval': 900
        }
        for key in missing_keys:
            if key in defaults:
                config[key] = defaults[key]

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                content = f.read()

            import re
            for key in missing_keys:
                if key in defaults:
                    if re.search(rf'{key}\s*=\s*["\'].*["\']', content):
                        content = re.sub(
                            rf'({key}\s*=\s*)["\'][^"\']*["\']',
                            rf'\1"{defaults[key]}"',
                            content
                        )
                    else:
                        content += f'\n{key} = "{defaults[key]}"\n'

            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            server.logger.error(f'保存配置文件失败: {e}')



def obtain_uuid(server: PluginServerInterface):
    global config

    if not config.get('api_url'):
        server.logger.error('API URL未配置,无法获取UUID')
        return

    server.logger.info(f'正在获取UUID...')

    try:
        url = f"{config['api_url']}/uuid/getuuid"
        response = requests.post(url, timeout=10)
        server.logger.info(f'API响应状态: HTTP {response.status_code}')
        if response.status_code == 200:
            data = response.json()
            server.logger.info(f'API响应: {data}')
            if 'uuid' in data:
                uuid = data.get('uuid')
                config['uuid'] = uuid

                with open(config_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                import re
                content = re.sub(r'(uuid\s*=\s*)"[^"]*"', rf'\1"{uuid}"', content)
                with open(config_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                server.logger.info(f'获取到UUID: {uuid}')
            else:
                server.logger.error(f'获取UUID失败')
        else:
            server.logger.error(f'获取UUID请求失败: HTTP {response.status_code}')
            server.logger.error(f'响应内容: {response.text}')
    except Exception as e:
        server.logger.error(f'获取UUID失败: {e}')


def download_ban_database(server: PluginServerInterface, src=None):
    global config

    if not config.get('token'):
        server.logger.warning('Token未配置请去官网获取https://ndpreforged.com')
        server.logger.warning('Token未配置请去官网获取https://ndpreforged.com')
        server.logger.warning('Token未配置请去官网获取https://ndpreforged.com')
        server.logger.warning('Token未配置请去官网获取https://ndpreforged.com')
        server.logger.warning('Token未配置请去官网获取https://ndpreforged.com')
        msg = 'Token未配置请去官网获取https://ndpreforged.com'
        server.logger.warning(msg)
        if src:
            src.reply(f'§c{msg}')
        return

    if not config.get('api_url'):
        msg = 'API未配置,无法下载数据库'
        server.logger.error(msg)
        if src:
            src.reply(f'§c{msg}')
        return

    try:
        params = {'token': config['token']}
        response = requests.get(f"{config['api_url']}/bans/download", params=params, timeout=30)

        if response.status_code != 200:
            error_msg = f'API响应错误 HTTP{response.status_code} 响应内容: {response.text}'
            server.logger.error(error_msg)
            if src:
                src.reply(f'§c{error_msg}')
            return

        data = response.json()
        download_url = data.get('url')

        if not download_url:
            error_msg = 'API响应错误'
            server.logger.error(error_msg)
            if src:
                src.reply(f'§c{error_msg}')
            return

        download_response = requests.get(download_url, timeout=60)

        if download_response.status_code != 200:
            error_msg = f'API响应错误 HTTP{download_response.status_code} Download Error'
            server.logger.error(error_msg)
            if src:
                src.reply(f'§c{error_msg}')
            return

        with open(ban_db_path, 'wb') as f:
            f.write(download_response.content)

        conn = sqlite3.connect(ban_db_path)
        cursor = conn.cursor()

        is_online = config.get('onlinemode', False)
        if is_online:
            cursor.execute("SELECT COUNT(*) FROM online")
        else:
            cursor.execute("SELECT COUNT(*) FROM offline")

        count = cursor.fetchone()[0]
        conn.close()
        try:
            done_response = requests.post(
                f"{config['api_url']}/bans/download/done",
                json={'token': config['token']},
                timeout=10
            )
            if done_response.status_code == 200:
                server.logger.info(f'数据库已更新')
        except Exception as e:
            server.logger.warning(f'API相应错误 HTTP{done_response.status_code} {e}')

    except Exception as e:
        server.logger.error(f'数据库更新失败{e}')


def register_commands(server: PluginServerInterface):
    from mcdreforged.api.command import Literal, QuotableText, SimpleCommandBuilder, Text, GreedyText

    builder = SimpleCommandBuilder()

    # !!ndpr / !!NDPR help
    builder.command('!!ndpr help', help_callback)
    builder.command('!!NDPR help', help_callback)
    builder.command('!!ndpr', help_callback)
    builder.command('!!NDPR', help_callback)

    # !!ndpr / !!NDPR d / download
    builder.command('!!ndpr d', download_callback)
    builder.command('!!ndpr download', download_callback)
    builder.command('!!NDPR d', download_callback)
    builder.command('!!NDPR download', download_callback)

    # !!ndpr / !!NDPR ban <player>
    builder.command('!!ndpr ban <player>', ban_callback)
    builder.command('!!NDPR ban <player>', ban_callback)

    # !!ndpr / !!NDPR check 
    builder.command('!!ndpr check <target>', check_callback)
    builder.command('!!NDPR check <target>', check_callback)

    # !!ndpr / !!NDPR reload
    builder.command('!!ndpr reload', reload_callback)
    builder.command('!!NDPR reload', reload_callback)

    # !!ndpr / !!NDPR cu / checkupdate
    builder.command('!!ndpr cu', check_update_callback)
    builder.command('!!ndpr checkupdate', check_update_callback)
    builder.command('!!NDPR cu', check_update_callback)
    builder.command('!!NDPR checkupdate', check_update_callback)

    builder.arg('player', QuotableText)
    builder.arg('target', QuotableText)
    builder.register(server)


def help_callback(src, ctx):
    src.reply('§6========== §bNDPR 封禁系统 §6==========')
    src.reply(f'§e版本:{version}.0')
    src.reply(f'§e作者:EXE_autumnwind NDPReforged Team')
    src.reply('官方交流Q群:232760327')
    src.reply('')
    src.reply('§b命令列表:')
    src.reply('§f!!ndpr help §7- 显示此帮助信息')
    src.reply('§f!!ndpr d / download §7- 下载封禁数据库')
    src.reply('§f!!ndpr ban <ID> §7- 提交封禁审核(如有上传权限)')
    src.reply('§f!!ndpr check <ID/IP/UUID> §7- 检查封禁状态')
    src.reply('§f!!ndpr reload §7- 重载插件')
    src.reply('§f!!ndpr cu / checkupdate §7- 检查插件更新')
    src.reply('')
    src.reply('© 2026 NDPR Team')

def reload_callback(src, ctx):
    reload_plugin(src, src.get_server())

def download_callback(src, ctx):
    download_ban_database(src.get_server(), src)


def ban_callback(src, ctx):
    player = ctx.get('player')
    if player:
        add_ban_player(src, player)

def check_callback(src, ctx):
    target = ctx.get('target')
    if target:
        if target.count('.') >= 3 and ':' in target:  # IPv4
            check_ban_by_identifier(src, 'ip', target)
        elif target.count(':') > 1:  # IPv6
            check_ban_by_identifier(src, 'ipv6', target)
        elif len(target) == 36 and target.count('-') == 4:  # UUID
            check_ban_by_identifier(src, 'uuid', target)
        else:  # ID
            check_ban_status(src, target)


def check_ban_by_identifier(src, identifier_type: str, value: str):
    global ban_db_path, config

    if not os.path.exists(ban_db_path):
        src.reply('§c无数据')
        return

    try:
        conn = sqlite3.connect(ban_db_path)
        cursor = conn.cursor()
        tables_to_check = ['online', 'offline']
        found = False

        for table in tables_to_check:
            if identifier_type == 'ip':
                cursor.execute(f"SELECT player, ban_reason, ban_time FROM {table} WHERE ip = ?", (value,))
            elif identifier_type == 'ipv6':
                cursor.execute(f"SELECT player, ban_reason, ban_time FROM {table} WHERE ipv6 = ?", (value,))
            elif identifier_type == 'uuid':
                cursor.execute(f"SELECT player, ban_reason, ban_time FROM {table} WHERE mcuuid = ?", (value,))

            result = cursor.fetchone()
            if result:
                found = True
                src.reply(f'§7玩家: {result[0]}')
                src.reply(f'§7原因: {result[1]}')
                src.reply(f'§7封禁时间: {result[2]}')
                break

        if not found:
            src.reply(f'§a未找到封禁记录 ({identifier_type}: {value})')

        conn.close()
    except Exception as e:
        src.reply(f'§c查询失败: {e}')


def check_update_callback(src, ctx):
    check_plugin_update(src.get_server(), src)


@new_thread('NDPR')
def reload_plugin(src, server: PluginServerInterface):
    global config
    try:
        init_config(server)
        download_ban_database(server, src)
        src.reply('§aNDPR插件已重载')
    except Exception as e:
        src.reply(f'§c重载失败: {e}')


@new_thread('NDPR')
def add_ban_player(src, player: str):
    global config

    if not config.get('token'):
        src.reply('§cToken未配置')
        return

    player_ip = get_player_ip(player)
    player_uuid = get_player_uuid(player)
    player_ipv6 = get_player_ipv6(player)

    info_list = []
    if player_ip:
        info_list.append(f'IP: {player_ip}')
    if player_ipv6:
        info_list.append(f'IPv6: {player_ipv6}')
    if player_uuid:
        info_list.append(f'UUID: {player_uuid}')

    if info_list:
        src.reply(f'§e已获取信息: {", ".join(info_list)}')

    try:
        url = f"{config['api_url']}/check/uploader"
        headers = {
            'Content-Type': 'application/json'
        }
        data = {
            'token': config['token'],
            'player_id': player,
            'ip': player_ip,
            'ipv6': player_ipv6,
            'uuid': player_uuid,
            'onlinemode': config.get('onlinemode', False)
        }

        src.reply(f'§e正在提交封禁审核...')

        response = requests.post(url, headers=headers, json=data, timeout=10)

        if response.status_code == 200:
            result = response.json()
            if result.get('result') == 'success':
                check_id = result.get('check_id')
                src.reply(f'§a成功提交')
                src.reply(f'§7审核编号: {check_id}')
                src.reply(f'§7等待管理员审核')
            else:
                src.reply(f'§c提交失败: {result.get("message", "未知错误")}')
        elif response.status_code == 403:
            src.reply('§c无上传权限,请到官网获取')
        else:
            src.reply(f'§c提交失败 HTTP {response.status_code}')
    except Exception as e:
        src.reply(f'§c提交失败 {e}')


@new_thread('NDPR')
def check_ban_status(src, player: str):
    global ban_db_path, config

    if not os.path.exists(ban_db_path):
        src.reply('§c无数据')
        return

    is_online = config.get('onlinemode', False)
    table_name = 'online' if is_online else 'offline'

    try:
        conn = sqlite3.connect(ban_db_path)
        cursor = conn.cursor()
        if is_online:
            cursor.execute("SELECT ip, ban_reason, ban_time FROM online WHERE player = ?", (player,))
        else:
            cursor.execute("SELECT ip, ban_reason, ban_time FROM offline WHERE player = ?", (player,))

        result = cursor.fetchone()
        conn.close()

        if result:
            src.reply(f'§c玩家 {player} 已被封禁')
            src.reply(f'§7IP: {result[0]}')
            src.reply(f'§7原因: {result[1]}')
            src.reply(f'§7封禁时间: {result[2]}')
        else:
            src.reply(f'§a玩家 {player} 未被封禁')
    except Exception as e:
        src.reply(f'§c查询失败: {e}')

def get_player_info_from_log(player: str) -> Dict[str, Optional[str]]:
    import re
    from datetime import datetime, timedelta

    log_path = config.get('log_path', 'server/logs/latest.log')

    if not os.path.isabs(log_path):
        plugin_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        mcdr_root = os.path.dirname(plugin_dir)
        log_path = os.path.join(mcdr_root, log_path)

    if not os.path.exists(log_path):
        print(f'日志文件不存在: {log_path}')
        return {}

    try:
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        two_minutes_ago = datetime.now() - timedelta(minutes=2)

        result = {
            'ip': None,
            'uuid': None,
            'ipv6': None
        }
        for line in reversed(lines):
            time_match = re.search(r'\[(\d{2}:\d{2}:\d{2})\]', line)
            if not time_match:
                continue

            time_str = time_match.group(1)
            try:
                log_time = datetime.strptime(time_str, '%H:%M:%S')
                log_time = log_time.replace(year=datetime.now().year,
                                           month=datetime.now().month,
                                           day=datetime.now().day)

                if log_time < two_minutes_ago:
                    continue
            except ValueError:
                continue
            if player in line and 'UUID of player' in line:
                uuid_match = re.search(r'UUID of player (\w+) is ([a-fA-F0-9-]{36})', line)
                if uuid_match and uuid_match.group(1) == player:
                    result['uuid'] = uuid_match.group(2)
            if player in line and ('logged in' in line or 'joined the game' in line):
                ip_match = re.search(rf'{re.escape(player)}\[/([0-9.:]+):', line)
                if ip_match:
                    ip = ip_match.group(1)
                    if ':' in ip and ip.count(':') > 1:
                        result['ipv6'] = ip
                    else:
                        result['ip'] = ip
        return result
    except Exception as e:
        print(f'读取日志时出错: {e}')
        return {}


def get_player_ip(player: str) -> Optional[str]:
    info = get_player_info_from_log(player)
    return info.get('ip')


def get_player_uuid(player: str) -> Optional[str]:
    info = get_player_info_from_log(player)
    return info.get('uuid')


def get_player_ipv6(player: str) -> Optional[str]:
    info = get_player_info_from_log(player)
    return info.get('ipv6')


def check_plugin_update(server: PluginServerInterface, src=None):
    current_version = {version}
    api_url = 'https://api.github.com/repos/NDPReforged/NDPR-MCDR/releases/latest'

    try:
        if src:
            src.reply('§e正在检查插件更新...')
        else:
            server.logger.info('正在检查插件更新...')

        response = requests.get(api_url, timeout=10)
        if response.status_code != 200:
            if src:
                src.reply('§c检查更新失败: 无法连接到GitHub')
            else:
                server.logger.warning('检查更新失败: 无法连接到GitHub')
            return

        data = response.json()
        latest_version = data.get('tag_name', '').lstrip('v')
        release_url = data.get('html_url', '')
        release_notes = data.get('body', '无更新说明')

        if src:
            if latest_version > current_version:
                src.reply(f'§a发现新版本: §e{latest_version} §7(当前: {current_version})')
                src.reply(f'§7下载地址: §f{release_url}')
                install_button = RText("§b[§d点击复制安装命令§b]")
                install_button.set_hover_text(RText("§7点击复制安装命令到聊天栏"))
                install_button.set_click_event(RAction.suggest_command, f'!!MCDR plg install ndpr=={latest_version}')
                src.reply(install_button)
                if release_notes:
                    src.reply('§7更新内容:')
                    notes_preview = release_notes[:200] + '...' if len(release_notes) > 200 else release_notes
                    for line in notes_preview.split('\n')[:5]:
                        if line.strip():
                            src.reply(f'§8  {line}')
            else:
                src.reply(f'§a当前已是最新版本 §e{current_version}')
        else:
            if latest_version > current_version:
                server.logger.warning(f'发现新版本: {latest_version} (当前: {current_version})')
                server.logger.info(f'下载地址: {release_url}')
            else:
                server.logger.info(f'当前已是最新版本 {current_version}')

    except Exception as e:
        error_msg = f'检查更新失败: {e}'
        if src:
            src.reply(f'§c{error_msg}')
        else:
            server.logger.warning(error_msg)

def on_player_joined(server: PluginServerInterface, player: str, info):
    global ban_db_path, config
    if not os.path.exists(ban_db_path):
        return
    player_uuid = get_player_uuid(player)
    player_ip = get_player_ip(player)
    player_ipv6 = get_player_ipv6(player)

    server.logger.info(f'玩家 {player} - IP: {player_ip}, UUID: {player_uuid}, IPv6: {player_ipv6}')

    is_online = config.get('onlinemode', False)
    table_name = 'online' if is_online else 'offline'

    try:
        conn = sqlite3.connect(ban_db_path)
        cursor = conn.cursor()

        tables_to_check = ['online', 'offline']

        for table in tables_to_check:
            if table == 'online' and player_uuid:
                cursor.execute(f"SELECT 1 FROM {table} WHERE mcuuid = ?", (player_uuid,))
                result = cursor.fetchone()
                if result:
                    conn.close()
                    server.logger.info(f'检测到被封禁玩家 {player} (UUID: {player_uuid} 匹配) 在 {table} 表, 正在踢出')
                    server.execute(f'kick {player} §c您已被NDPR封禁系统封禁')
                    return

            cursor.execute(f"SELECT 1 FROM {table} WHERE player = ?", (player,))
            result = cursor.fetchone()
            if result:
                conn.close()
                server.logger.info(f'检测到被封禁玩家 {player} (玩家名匹配) 在 {table} 表, 正在踢出')
                server.execute(f'kick {player} §c您已被NDPR封禁系统封禁')
                return

            if player_ip:
                cursor.execute(f"SELECT 1 FROM {table} WHERE ip = ?", (player_ip,))
                result = cursor.fetchone()
                if result:
                    conn.close()
                    server.logger.info(f'检测到被封禁玩家 {player} (IP: {player_ip} 匹配) 在 {table} 表, 正在踢出')
                    server.execute(f'kick {player} §c您已被NDPR封禁系统封禁')
                    return

            if player_ipv6:
                cursor.execute(f"SELECT 1 FROM {table} WHERE ipv6 = ?", (player_ipv6,))
                result = cursor.fetchone()
                if result:
                    conn.close()
                    server.logger.info(f'检测到被封禁玩家 {player} (IPv6: {player_ipv6} 匹配) 在 {table} 表, 正在踢出')
                    server.execute(f'kick {player} §c您已被NDPR封禁系统封禁')
                    return

        conn.close()
    except Exception as e:
        server.logger.error(f'检测玩家 {player} 时出错: {e}')

def start_download_task(server: PluginServerInterface):
    global download_task, config
    download_interval = config.get('download_interval', 1800)
    download_minutes = download_interval // 60
    download_task = threading.Thread(
        target=run_download_loop,
        args=(server, download_interval),
        daemon=True,
        name='ndpr_download'
    )
    download_task.start()
@new_thread('NDPR_DownloadLoop')
def run_download_loop(server: PluginServerInterface, interval: int):
    import time
    while True:
        try:
            time.sleep(interval)
            download_ban_database(server)
        except Exception:
            pass


