#!/usr/bin/env python
# -*- coding: utf-8 -*-

from telegram.ext import Updater
from telegram.ext.dispatcher import run_async
from telegram import ParseMode
from time import sleep
import logging
import datetime
import time
import random
import sqlite3

logger = logging.getLogger('simple_example')
logger.setLevel(logging.DEBUG)
#logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh = logging.FileHandler('debug.log')
fh.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.ERROR)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
fh.setFormatter(formatter)
logger.addHandler(fh)

class GoldRO(object):
	def __init__(self):
		self.first_run = {}
		self.token = '123'
		self.bot_db = "quests.db"
		self.quest_between = "-2 hours"
		self.hint_timeout = 15
		self.db_conn = None
		self.db_cur = None
		self.current_question = {}
		self.current_hint = {}
		self.current_answer = {}
		self.last_message = {}
		self.action = {}
		self.hint_len = 2
		self.timeout_message = 3 #minutes
		self.running = {}
		self.user_points = {}
		self.answer_weight = {}
		self.answer_time = {}
		self.username = {}
		self.session = {}
		self.session_target = 25
		self.user_id = {}
		self.last_stop_id = {}
		self.last_start_id = {}

	def db_connect(self):
		logging.debug("def db_connect")
		if not self.db_conn and not self.db_cur:
			logger.debug("Connect to database...")
			self.db_conn = sqlite3.connect(self.bot_db, check_same_thread=False)
			logger.debug("Get cursor")
			self.db_cur = self.db_conn.cursor()
		else:
			logger.error("Database connect already exits...")

	def db_disconnect(self):
		logger.debug("def db_disconnect")
		if self.db_conn and self.db_cur:
			logger.debug("Commit to database...")
			self.db_conn.commit()
			logger.debug("Close connection...")
			self.db_conn.close()
			self.db_cur = None
			self.db_conn = None
		else:
			logger.error("No database connect...")

	def new_question(self, chat_id):
		logger.debug("def new_question")
		self.db_connect()
		new_quest = self.db_cur.execute("""SELECT question, answer 
						FROM questions 
						WHERE last_show < strftime('%s','now','{0}') 
						ORDER BY RANDOM() LIMIT 1""".format(self.quest_between)).fetchone()
		if new_quest:
			self.current_question[chat_id] = new_quest[0]
			self.current_answer[chat_id] = new_quest[1]
			answer_len = int(len(self.current_answer[chat_id]))
			hint = u'{}{}'.format(self.current_answer[chat_id][:-(answer_len - self.hint_len)],'*'*(answer_len - self.hint_len))
			self.current_hint[chat_id] = hint
			self.db_cur.execute(u"""UPDATE questions 
						SET last_show = strftime('%s','now') 
						WHERE question = '{0}' 
						AND answer = '{1}'""".format(new_quest[0], new_quest[1]))
			logger.debug(self.current_question[chat_id])
			logger.debug(self.current_answer[chat_id])
		else:
			logger.debug('new_question: STOP')
			self.stop
		self.db_disconnect()
		self.answer_time[chat_id] = datetime.datetime.now()

	def parse_answer(self, message, chat_id, user_id, first_name, last_name):
		logger.debug("parse_answer")
		if ((self.first_run[chat_id] == False) and (self.action[chat_id] == "hint" or self.action[chat_id] == "hint2")):
			if message.lower() == self.current_answer[chat_id].lower():
				del(self.current_question[chat_id])
				del(self.current_hint[chat_id])
				logger.info('correct')
				username = (first_name + ' ' + last_name)
				uname = username.encode('utf-8')
				self.db_connect()
				self.session[(chat_id, user_id)] = self.session.get((chat_id, user_id), 0) + self.answer_weight[chat_id]
				logger.debug(self.session[(chat_id, user_id)])
				user_points = self.db_cur.execute("""SELECT points
								FROM leaders
								WHERE name = '{0}'
								AND username = '{1}'
								AND chat = '{2}'""".format(user_id, uname, chat_id)).fetchone()
				if user_points and user_points[0]:
					user_points = self.session[(chat_id,user_id)] #int(user_points[0]) + self.answer_weight[chat_id]
					logger.debug(user_points)
					logger.debug(self.answer_weight[chat_id])
					self.db_cur.execute("""UPDATE leaders
							SET points = '{0}'
							WHERE name = '{1}'
							AND username = '{2}'
							AND chat = '{3}'""".format(user_points, user_id, uname, chat_id))
				else:
					user_points = self.session[(chat_id,user_id)]
					self.db_cur.execute("""INSERT INTO leaders(name, points, chat, username)
								VALUES ('{0}', '{1}', '{2}', '{3}')""".format(user_id, user_points, chat_id, uname))
				self.db_disconnect()
				self.action[chat_id]="answer"
				self.username[chat_id] = username
				self.user_points[chat_id] = user_points
				self.user_id[chat_id] = user_id

	@run_async
	def start(self, bot, update, **kwargs):
		logger.debug('def start')
		chat_id = update.message.chat_id
		if self.running.get(chat_id):
			bot.sendMessage(chat_id, text='<b>Викторина уже запущена</b>', parse_mode=ParseMode.HTML)
		else:
		    #logger.debug(self.last_start_id.get(chat_id))
		    if (self.last_start_id.get(chat_id) != update.message.from_user.id) and (self.last_start_id.get(chat_id) != None):
			self.last_start_id[chat_id] = None
			bot.sendMessage(chat_id, text='<b>Викторина началась!</b>', parse_mode=ParseMode.HTML)
			t = {k: v for k, v in self.session.iteritems() if k[0] != chat_id}
			del(self.session)
			self.session = t
			self.db_connect()
			self.db_cur.execute("""DELETE FROM leaders""")
			self.db_disconnect()
			self.last_message[chat_id] = datetime.datetime.now()
			self.first_run[chat_id] = True
			self.running[chat_id] = True
			self.action[chat_id] = "new_question"
			self.answer_time[chat_id] = datetime.datetime.now()
			while self.running[chat_id]:
					if self.action[chat_id] == "answer":
						at = str(datetime.datetime.now() - self.answer_time[chat_id])
						if (self.session[(chat_id, self.user_id[chat_id])] >= 20):
							bot.sendMessage(chat_id, text=u"<b>{0}</b> отвечает на вопрос за <b>{1}</b> сек и получает <b>{2}</b> очков! Правильный ответ: <i>{3}</i>\n<b>Внимание!</b> {0} набирает <b>{4}</b> очков!"\
							.format(self.username[chat_id], int(at[5:-7]),self.answer_weight[chat_id], self.current_answer[chat_id], self.session[(chat_id, self.user_id[chat_id])]) ,parse_mode=ParseMode.HTML)
						else:
							bot.sendMessage(chat_id, text=u"<b>{0}</b> отвечает на вопрос за <b>{1}</b> сек и получает <b>{2}</b> очков! Правильный ответ: <i>{3}</i>"\
							.format(self.username[chat_id], int(at[5:-7]),self.answer_weight[chat_id], self.current_answer[chat_id]) ,parse_mode=ParseMode.HTML)
						if (self.session[(chat_id, self.user_id[chat_id])] >= self.session_target):
							bot.sendMessage(chat_id, text=u"<b>{0}</b> набирает <b>{1}</b> очков и побеждает в викторине!"\
							.format(self.username[chat_id], self.session[(chat_id, self.user_id[chat_id])]), parse_mode=ParseMode.HTML)
							bot.sendMessage(chat_id, text='<b>Викторина остановлена!</b>', parse_mode=ParseMode.HTML)
							self.db_connect()
							uname = self.username[chat_id]
							games = self.db_cur.execute("""SELECT points
												FROM top
												WHERE name = '{0}'
												AND username = '{1}'
												AND chat = '{2}'"""\
												.format(self.user_id[chat_id], uname.encode('utf-8'), chat_id)).fetchone()
							if games and len(games):
								for points in games:
									win_games = points
								win_games += 1
								self.db_cur.execute("""UPDATE top
											SET points = '{0}'
											WHERE name = '{1}'
											AND username = '{2}'
											AND chat = '{3}'"""\
											.format(win_games, self.user_id[chat_id], uname.encode('utf-8'), chat_id))
							else:
								win_games = 1
								self.db_cur.execute("""INSERT INTO top(name, points, chat, username)
											VALUES ('{0}', '{1}', '{2}', '{3}')"""\
											.format(self.user_id[chat_id], win_games, chat_id, uname.encode('utf-8')))
							logger.debug(win_games)
							self.db_disconnect()
							self.last_start_id[chat_id] = None
							self.last_stop_id[chat_id] = None
							self.running[chat_id] = False
						self.action[chat_id] = "new_question"
					elif self.action[chat_id] == "hint":
						ht = str(datetime.datetime.now() - self.answer_time[chat_id])
						if not (ht[5:-7] == ''):
							if (float(ht[5:-7])>=self.hint_timeout):
								self.answer_weight[chat_id] = 1
								answer_len = int(len(self.current_answer[chat_id]))
								if (answer_len == 2):
									hint = u'**'
								elif (answer_len == 1):
									hint = u'*'
								else:
									hint = u'{}{}'.format(self.current_answer[chat_id][:-(answer_len - self.hint_len)],'*'*(answer_len - self.hint_len))
								bot.sendMessage(chat_id, text=u"<b>Подсказка: </b><i>{0}</i>".format(hint), parse_mode=ParseMode.HTML)
								self.action[chat_id] = "hint2"
					elif self.action[chat_id] == "hint2":
						ht = str(datetime.datetime.now() - self.answer_time[chat_id])
						if not (ht[5:-7] == ''):
						    if (float(ht[5:-7]) >= self.hint_timeout*2):
							bot.sendMessage(chat_id, text=u"<b>Никто не ответил на вопрос.</b>", parse_mode=ParseMode.HTML)
							del(self.current_question[chat_id])
							del(self.current_hint[chat_id])
							self.action[chat_id] = "new_question"
					elif self.action[chat_id] == "new_question":
						lm = str(datetime.datetime.now() - self.last_message[chat_id])
						if (float(lm[3:-10]) >= self.timeout_message):
							self.running[chat_id] = False
							bot.sendMessage(chat_id, text='<b>Викторина остановлена!</b>', parse_mode=ParseMode.HTML)
						else:
							self.answer_weight[chat_id] = 2
							bot.sendMessage(chat_id, text=u"<b>Следующий вопрос через {0} секунд.</b>".format(self.hint_timeout), parse_mode=ParseMode.HTML)
							time.sleep(self.hint_timeout)
							self.action[chat_id] = "hint"
							if (self.running[chat_id]):
								self.first_run[chat_id] = False
								self.new_question(chat_id)
								bot.sendMessage(chat_id, text=u"<b>Внимание, вопрос: </b><i>{0}</i>"\
											.format(self.current_question[chat_id]), parse_mode=ParseMode.HTML)
					else:
						time.sleep(0.5)
		    else:
			self.last_start_id[chat_id] = update.message.from_user.id
			bot.sendMessage(chat_id, text='<b>Для запуска необходимо как минимум два игрока</b>', parse_mode=ParseMode.HTML)


	def roll(self, bot, update, **args):
		logger.debug('def roll')
		bot.sendMessage(update.message.chat_id, text=u'{}'.format(random.randrange(1, 100)))

	def stop(self, bot, update):
		logger.debug('def stop')
		chat_id = update.message.chat_id
		if self.running.get(chat_id):
			if (self.last_stop_id.get(chat_id) != update.message.from_user.id) and (self.last_stop_id.get(chat_id) != None):
				self.last_stop_id[chat_id] = None
				logger.info('self.running[' + str(chat_id) + '] = False')
				self.running[chat_id] = False
				self.last_start_id[chat_id] = None
				bot.sendMessage(chat_id, text='<b>Викторина остановлена!</b>', parse_mode=ParseMode.HTML)
			else:
				self.last_stop_id[chat_id] = update.message.from_user.id
				bot.sendMessage(chat_id, text='<b>Для остановки необходимы команды как минимум двух игроков</b>', parse_mode=ParseMode.HTML)
		else:
			bot.sendMessage(chat_id, text='<b>Викторина не запущена!</b>', parse_mode=ParseMode.HTML)
			self.last_start_id[chat_id] = None
			self.last_stop_id[chat_id] = None

	def help(self, bot, update):
		logger.debug('def help')
		bot.sendMessage(update.message.chat_id, text="""<b>Викторина.</b>
/start запуск викторины
/stop остановка викторины
/me очки в текущем раунде
/top таблица лидеров
/roll случайное число от 1 до 100
/help помощь""", parse_mode=ParseMode.HTML)

	def unknown_command(self, bot, update):
		logger.debug('def unknown_command')
		bot.sendMessage(update.message.chat_id, text=u"""<b>Неизвестная команда.</b>
/start запуск викторины
/stop остановка викторины
/me очки в текущем раунде
/top таблица лидеров
/roll случайное число от 1 до 100
/help помощь""", parse_mode=ParseMode.HTML)

	def me(self, bot, update):
		logger.debug('def me')
		chat_id = update.message.chat_id
		user_id = update.message.from_user.id
		self.db_connect()
		leaderboard = self.db_cur.execute("""SELECT points, username
							FROM leaders
							WHERE name = '{1}'
							AND chat = '{0}'"""\
							.format(chat_id, user_id)).fetchall()
		if len(leaderboard):
			for points, username in leaderboard:
				bot.sendMessage(chat_id, text=u"<b>{0}</b> в текущем раунде набрал <b>{1}</b> очков"\
							.format(username, points), parse_mode=ParseMode.HTML)
		else:
			bot.sendMessage(chat_id, text=u"<b>{0}</b> ещё не заработал очков"\
							.format(update.message.from_user.first_name + ' ' + update.message.from_user.last_name), parse_mode=ParseMode.HTML)
		self.db_disconnect()

	def show_top(self, bot, update):
		logger.debug('def show_top')
		chat_id = update.message.chat_id
#		self.db_connect()
#		self.db_cur.execute("""CREATE TABLE top (
#							name integer PRIMARY KEY AUTOINCREMENT,
#							username text NOT NULL,
#							points integer NOT NULL,
#							chat text NOT NULL)""")
#		self.db_disconnect()
		self.db_connect()
		leaderboard = self.db_cur.execute("""SELECT name, points, username
							FROM top
							WHERE chat = '{0}'
							ORDER BY points DESC""".format(chat_id)).fetchall()
		if len(leaderboard):
			i = 1
			top = u"<b>Топ игроков:\nИмя - количество выигранных игр</b>\n"
			for id, points, username in leaderboard:
				top = u"{0}{1} - {2}\n".format(top, username, points)
				i+=1
			i = None
			bot.sendMessage(chat_id, text=u"{0}".format(top), parse_mode=ParseMode.HTML)
		else:
			bot.sendMessage(chat_id, text=u"<b>Лидеров еще нет</b>", parse_mode=ParseMode.HTML)
		self.db_disconnect()

	def message(self, bot, update):
		logger.debug('def message')
		chat_id = update.message.chat_id
		if (self.running.get(chat_id)):
			self.last_message[chat_id] = datetime.datetime.now()
			self.parse_answer(update.message.text, chat_id, update.message.from_user.id, update.message.from_user.first_name,\
				update.message.from_user.last_name)

	def main(self):
		logger.debug('def main')
		self.updater = Updater(self.token, workers=10)
		self.dp = self.updater.dispatcher
		self.dp.addTelegramCommandHandler("start", self.start)
		self.dp.addTelegramCommandHandler("stop", self.stop)
		self.dp.addTelegramCommandHandler("help", self.help)
		self.dp.addTelegramCommandHandler("me", self.me)
		self.dp.addTelegramCommandHandler("top", self.show_top)
		self.dp.addTelegramCommandHandler("roll", self.roll)
		self.dp.addUnknownTelegramCommandHandler(self.unknown_command)
		self.dp.addTelegramMessageHandler(self.message)
		self.updater.start_polling()
		self.updater.idle()

if __name__ == '__main__':
	bot = GoldRO()
	bot.main()