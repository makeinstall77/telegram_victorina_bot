#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sqlite3
import os
import io

questions_file = "questions_ru.txt"
questions_list = []

if os.path.exists(questions_file):
    try:
        with io.open(questions_file, 'rt', encoding='utf-8') as f:
            for line in f.readlines():
                quest = line.replace("\n","")\
                            .replace("\r","").split("|")
                if len(quest) > 1:
                    questions_list.append((quest[0],
                                           quest[1]))
            print "Read file ok"
    # неполучилось открыть файл
    except IOError:
        print "Error open file %s" % questions_file
    else:
        conn = sqlite3.connect("QuizBot.db")
        c = conn.cursor()
        query = """INSERT INTO questions(question, answer, last_show)
                   VALUES (?, ?, 0)"""
        c.executemany(query, questions_list)
        count = c.execute("SELECT COUNT(*) FROM questions").fetchone()
        print "Insert ok, new count questions: %s" % count
        conn.commit()
        conn.close()
else:
    print "File %s not exists!" % questions_file
