import string
import re
import random
import logging
import intent_extract
import api
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

from rasa_nlu.training_data import load_data
from rasa_nlu.config import RasaNLUModelConfig
from rasa_nlu.model import Trainer,Interpreter,Metadata
from rasa_nlu import config
interpreter=Interpreter.load('D:\chatbot\default\model_20210127-000608')
print('ok')
INIT=0
AUTHED=1
CHECK=2
HP=3
OP=4
PP=5
checked=0

params, suggestions, excluded = {}, [], []
stockname=''
item=''
date=''

reply=[]
state = INIT
pending = None
policy_rules = {
    (INIT, "login"): (INIT, "please enter your password?", AUTHED),

    (INIT, "number"): (AUTHED, "perfect, welcome back!", None),

    (AUTHED, "login"): (CHECK, "What kind of stock do you want to check?", None),
    (AUTHED, "location"): (CHECK, "What kind of stock do you want to check?", None),

    (CHECK, "logout"): (INIT, "thank you for using, have a nice day!", None),
    (CHECK, "hprice"): (CHECK, "In which kind of format do you prefer the result to be shown? text?", HP),
    (CHECK, "form"): (HP, "Order received.I'm working on your request. It might cost a few second.", None),
    (HP, "hprice"): (CHECK, None, None),

    (CHECK, "trend"): (CHECK, "Please choose a specific thing so that I can help you to check it out.", PP),
    (CHECK, "high"): (PP, "Order received.I'm working on your request. It might cost a few second.", None),
    (CHECK, "low"): (PP, "Order received.I'm working on your request. It might cost a few second.", None),
    (PP, "trend"): (CHECK, None, None),

    (CHECK, "close"): (CHECK, "Please enter the date that you want to check.", OP),
    (CHECK, "volume"): (CHECK, "Please enter the date that you want to check.", OP),
    (CHECK, "open"): (CHECK, "Please enter the date that you want to check.", OP),
    (CHECK, "number"): (OP, "Order received.I'm working on your request. It might cost a few second.", None),
    (OP, "open"): (CHECK, None, None),
    (OP, "close"): (CHECK, None, None),
    (OP, "volume"): (CHECK, None, None)
}
rules = {'I wanna (.*)': ['What would it mean if you got {0}',
                         'Why do you want {0}',
                         "What's stopping you from getting {0}"],
         'do you remember (.*)': ['Did you think I would forget {0}',
                                  "Why haven't you been able to forget {0}",
                                 ],
         'do you think (.*)': ['if {0}? Absolutely.'],
         'if (.*)': ["Do you really think it's likely that {0}",
                     'Do you wish that {0}',
                     'What do you think about {0}',
                     'Really--if {0}'],
         'Im (.*)': ["hello {0}"
                     ],
         'my name is (.*)': ["hello {0}"
                 ]
         }
def reply_to_user(response):
    global reply
    #print("BOT : {}".format(response))
    reply.append(response)


def chitchat_response(message, interpreter):
    # Call match_rule()
    global params, suggestions, excluded
    response, phrase = match_rule(rules, message)

    if response == "default":
        response = intent_extract.keyrespond(message, interpreter)
        return response
    if '{0}' in response:
        # Replace the pronouns of phrase
        phrase = replace_pronouns(phrase)
        # Calculate the response
        response = response.format(phrase)
        return response
    response, params, suggestions, excluded = intent_extract.intent_response(message, params, suggestions, excluded, interpreter)
    return response
def match_rule(rules, message):
    for pattern, responses in rules.items():
        match = re.search(pattern, message)
        if match is not None:
            response = random.choice(responses)
            var = match.group(1) if '{0}' in response else None
            return response, var
    return "default", None
def replace_pronouns(message) -> object:
    message = message.lower()
    if ' me ' in message:
        return re.sub('me', 'you', message)
    elif ' i ' in message:
        return re.sub('i', 'you', message)
    elif ' my ' in message:
        return re.sub('my', 'your', message)
    elif ' your ' in message:
        return re.sub('your', 'my', message)
    elif ' you ' in message:
        return re.sub('you', 'me', message)
    return message
def policy_response(state, pending, message,interpreter):
    global checked
    global params, suggestions, excluded
    global stockname
    global CHECK
    try:
        new_state, response, pending_state = policy_rules[(state, intent_extract.match_intent(message, interpreter))]
    except KeyError:
        if(state==INIT):
            reply_to_user("Permission denied! please login first.")
        else:
            reply_to_user("input error!")
        return state,pending
    else:
        if(response is not None):
            reply_to_user(response)
        if pending is not None:
            new_state, response, pending_state = policy_rules[pending]
            if(response is not None):
                reply_to_user(response)
        if pending_state is not None:
            pending = (pending_state, intent_extract.match_intent(message, interpreter))
        if(new_state==CHECK) :
            checked=1
        return new_state, pending


def send_message(state, pending, message, interpreter):
    global checked
    global params, suggestions, excluded
    global stockname
    global CHECK, date, item
    global sheet_flag, pic_flag

    intent = intent_extract.match_intent(message, interpreter)  # 提取现阶段操作的意图

    response = chitchat_response(message, interpreter)  # 首先判断是否为闲聊消息
    if response is not None:
        reply_to_user(response)
        return state, None
    # 若不是闲聊型，则要先登录
    if (checked == 0):
        new_state, pending = policy_response(state, pending, message, interpreter)  # 登录的状态转换多轮查询
        return new_state, pending
    # 完成登录后
    else:
        if ("logout" in intent):
            stockname = ''
            item = ''
            date = ''
            sheet_flag = 0
            pic_flag = 0
            checked = 0
            new_state, pending = policy_response(state, pending, message, interpreter)
            return new_state, pending

        elif ('search' in intent) or ('location' in intent) or ('affirm' in intent) or (
                'deny' in intent):
            response, params, suggestions, excluded = intent_extract.intent_response(message, params, suggestions,
                                                                                     excluded, interpreter)
            reply_to_user(response)
            return state, None

        elif ('hprice' in intent) or ("form" in intent):
            if (stock_choosed() == 0):
                return state, None
            else:
                new_state, pending = policy_response(state, pending, message, interpreter)
                if (intent == 'hprice'):
                    return new_state, pending
                else:
                    if ("text" in message):
                        response = str(api.get_historical_prices(stockname))
                        reply_to_user(response)
                    return new_state, pending

        elif ('trend' in intent) or ('high' in intent) or ('low' in intent):
            if (stock_choosed() == 0):
                return state, None
            else:
                new_state, pending = policy_response(state, pending, message, interpreter)
                if ('trend' in intent):
                    return new_state, pending

        elif (intent == 'open') or (intent == 'close') or (intent == 'volume') or (
                intent == 'number'):
            if (stock_choosed() == 0):
                return state, None
            else:
                new_state, pending = policy_response(state, pending, message, interpreter)
                if (intent != 'number'):
                    item = intent
                return new_state, pending

        elif ('sp_stock' in intent):
            stockname = intent.ent_ex(message, interpreter)
            response = "I see, you'd like to check this one. And?"
            reply_to_user(response)
            return state, None

        else:  # 输入了意料之外的信息会报错
            response = "input error!"
            reply_to_user(response)
            return state, None
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)
def start(update, context):
    update.message.reply_text('Hi!')

def help(update, context):
    update.message.reply_text('Help!')
def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)
def stock_choosed():
    global stockname
    if (stockname == ''):
        response = "you have to choose a stock first."
        reply_to_user(response)
        return 0
    return 1

def main():
    updater = Updater('1567773781:AAH6uEgkHsHBW4svyGuBXzbZbjJf-FyBXFQ')
    dp = updater.dispatcher
    #简单的控制台指令
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))
    # 记录错误
    dp.add_error_handler(error)

    # 启动机器人
    updater.start_polling()

    #阻塞进程直至keyboard interrupt
    updater.idle()

if __name__ == '__main__':
    main()